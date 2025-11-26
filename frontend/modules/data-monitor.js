/**
 * 數據監控模組
 * 負責訪客統計、URL監測和系統分析功能
 */

import { escapeHtml } from '../utils/dom-helper.js';
import { showNotification } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// ==================== 常量定義 ====================

const LS_KEY = 'exposureUrls';
const SESSION_KEY = 'admin_visitor_counted';

// ==================== 公開函數 ====================

/**
 * 初始化數據監控功能
 * @export
 */
export function init() {
    initVisitorTracking();
    initUrlMonitoring();
    initAnalytics();

    console.log('✅ 數據監控已初始化');
}

/**
 * 刷新所有統計數據
 * @export
 */
export async function refresh() {
    await loadVisitorStats();
    refreshAnalytics();
}

/**
 * 載入訪客統計數據
 * @export
 */
export async function loadStats() {
    await loadVisitorStats();
}

// ==================== 私有函數 - 訪客追蹤 ====================

/**
 * 初始化訪客追蹤
 */
function initVisitorTracking() {
    // 記錄訪客計數（使用 sessionStorage 防止同一會話重複計數）
    if (!sessionStorage.getItem(SESSION_KEY)) {
        APIClient.visitor.increment().then(result => {
            if (result.success) {
                sessionStorage.setItem(SESSION_KEY, 'true');
                console.log('✅ 訪客計數已記錄:', result);
                // 記錄後立即載入最新統計數據
                loadVisitorStats();
            }
        });
    } else {
        // 如果已經計數過，只載入統計數據
        loadVisitorStats();
    }
}

/**
 * 載入訪客統計數據
 */
async function loadVisitorStats() {
    // 載入總瀏覽數
    try {
        const totalResult = await APIClient.visitor.getTotal();
        const totalEl = document.getElementById('totalVisitorCount');
        if (totalEl) {
            if (totalResult.success) {
                totalEl.textContent = totalResult.total.toLocaleString('zh-TW');
                console.log('✅ 總瀏覽數已更新:', totalResult.total);
            } else {
                totalEl.textContent = '--';
                console.warn('⚠️ 載入總瀏覽數失敗:', totalResult.error);
            }
        }
    } catch (error) {
        console.error('❌ 載入總瀏覽數時發生錯誤:', error);
        const totalEl = document.getElementById('totalVisitorCount');
        if (totalEl) totalEl.textContent = '--';
    }

    // 載入本月瀏覽數
    try {
        const monthlyResult = await APIClient.visitor.getStats();
        const monthlyEl = document.getElementById('monthlyVisitorCount');
        if (monthlyEl) {
            if (monthlyResult.success) {
                monthlyEl.textContent = monthlyResult.count.toLocaleString('zh-TW');
                console.log('✅ 本月瀏覽數已更新:', monthlyResult.count);
            } else {
                monthlyEl.textContent = '--';
                console.warn('⚠️ 載入本月瀏覽數失敗:', monthlyResult.error);
            }
        }
    } catch (error) {
        console.error('❌ 載入本月瀏覽數時發生錯誤:', error);
        const monthlyEl = document.getElementById('monthlyVisitorCount');
        if (monthlyEl) monthlyEl.textContent = '--';
    }
}

// ==================== 私有函數 - URL 監測 ====================

/**
 * 初始化 URL 監測功能
 */
function initUrlMonitoring() {
    const section = document.querySelector('#exposure');
    if (!section) return;

    let listEl = section.querySelector('.url-list');
    if (!listEl) {
        listEl = document.createElement('div');
        listEl.className = 'url-list';
        section.appendChild(listEl);
    }

    // 載入和保存函數
    function loadUrls() {
        try {
            return JSON.parse(localStorage.getItem(LS_KEY) || '[]');
        } catch {
            return [];
        }
    }

    function saveUrls(data) {
        localStorage.setItem(LS_KEY, JSON.stringify(data));
        updateActiveUrlCount(data.length);
    }

    function updateActiveUrlCount(count) {
        const activeUrlEl = document.getElementById('activeUrlCount');
        if (activeUrlEl) {
            activeUrlEl.textContent = count.toString();
        }
    }

    function normalizeUrl(url) {
        url = (url || '').trim();
        if (!url) return '';
        if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
        return url;
    }

    function renderUrlList() {
        const data = loadUrls();

        // 更新活躍網址數
        updateActiveUrlCount(data.length);

        if (!data.length) {
            listEl.innerHTML = '<div class="empty-tip">目前沒有網址，請按右上角「新增網址」。</div>';
            return;
        }

        listEl.innerHTML = data.map(it => `
            <div class="url-item" data-id="${it.id}">
                <div class="url-info">
                    <span class="url-icon">🌐</span>
                    <div class="url-details">
                        <h4>${escapeHtml(it.name)}</h4>
                        <a class="url-link" href="${it.url}" target="_blank" rel="noopener">${escapeHtml(it.url)}</a>
                    </div>
                </div>
                <div class="url-actions">
                    <button class="btn-icon" data-action="open" title="開啟">🔗</button>
                    <button class="btn-icon danger" data-action="del" title="刪除">🗑️</button>
                </div>
            </div>
        `).join('');
    }

    // 綁定 URL 項目操作事件
    listEl.addEventListener('click', (e) => {
        const btn = e.target.closest('button.btn-icon');
        if (!btn) return;

        const row = btn.closest('.url-item');
        const id = row?.dataset.id;
        if (!id) return;

        const data = loadUrls();
        const item = data.find(x => String(x.id) === String(id));
        if (!item) return;

        if (btn.dataset.action === 'open') {
            window.open(item.url, '_blank', 'noopener');
        } else if (btn.dataset.action === 'del') {
            if (confirm(`確定要刪除「${item.name}」嗎？`)) {
                saveUrls(data.filter(x => String(x.id) !== String(id)));
                renderUrlList();
            }
        }
    });

    // 關閉新增 URL 彈窗
    function closeUrlAddModal() {
        const modal = document.getElementById('urlAddModal');
        if (modal) modal.remove();
        document.body.classList.remove('no-scroll');
    }

    // 顯示新增 URL 彈窗
    window.showAddUrlModal = function() {
        const mask = document.createElement('div');
        mask.className = 'audio-modal';
        mask.id = 'urlAddModal';

        const card = document.createElement('div');
        card.className = 'audio-modal__card';
        card.innerHTML = `
            <div class="audio-modal__head">
                <h3>新增網址</h3>
                <button class="btn-ghost" data-close aria-label="關閉">✕</button>
            </div>
            <div class="form-row">
                <label for="ua-name">網站簡稱:</label>
                <input id="ua-name" type="text" placeholder="請輸入網頁簡稱...">
            </div>
            <div class="form-row">
                <label for="ua-url">監測網址:</label>
                <input id="ua-url" type="text" placeholder="網址...">
            </div>
            <div class="audio-modal__actions">
                <button class="btn-dark" data-save>新增</button>
            </div>
        `;

        mask.appendChild(card);
        document.body.appendChild(mask);
        document.body.classList.add('no-scroll');

        mask.addEventListener('click', (e) => {
            if (e.target === mask || e.target.closest('[data-close]')) {
                closeUrlAddModal();
            }
        });

        mask.querySelector('[data-save]').addEventListener('click', () => {
            const name = (mask.querySelector('#ua-name')?.value || '').trim();
            const rawUrl = (mask.querySelector('#ua-url')?.value || '').trim();

            if (!name) {
                showNotification('請輸入「網站簡稱」', 'warning');
                return;
            }

            const url = normalizeUrl(rawUrl);
            try {
                new URL(url);
            } catch {
                showNotification('請輸入正確網址', 'warning');
                return;
            }

            const arr = loadUrls();
            arr.push({ id: Date.now(), name, url });
            saveUrls(arr);
            renderUrlList();
            closeUrlAddModal();
            showNotification('網址新增成功', 'success');
        });
    };

    // 綁定新增按鈕
    const addBtn = section.querySelector('.add-url-btn');
    if (addBtn) {
        addBtn.addEventListener('click', window.showAddUrlModal);
    }

    // 初次渲染
    renderUrlList();
}

// ==================== 私有函數 - 系統分析 ====================

/**
 * 初始化系統分析
 */
function initAnalytics() {
    refreshAnalytics();
    // 每 30 秒刷新一次
    setInterval(refreshAnalytics, 30000);
}

/**
 * 刷新分析數據
 */
function refreshAnalytics() {
    // 模擬數據刷新
    // 未來可以在這裡添加實際的系統狀態監控
}

// ==================== 全局導出（供 HTML 內聯事件使用） ====================

if (typeof window !== 'undefined') {
    window.dataMonitor = {
        refresh,
        loadStats
    };
}
