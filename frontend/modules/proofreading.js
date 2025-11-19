/**
 * 校稿功能模組
 * 負責資料校稿對話功能
 */

import { $, escapeHtml } from '../utils/dom-helper.js';
import { showNotification, confirm } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// 模組狀態
let proofreadSessionId = null;

/**
 * 初始化校稿功能
 * @export
 */
export function init() {
    const sendBtn = $('#pr-sendBtn');
    const messageInput = $('#pr-messageInput');
    const clearBtn = $('#clearProofreadChat');

    if (!sendBtn || !messageInput) {
        console.warn('校稿功能：找不到必要的 DOM 元素');
        return;
    }

    // 綁定發送按鈕
    sendBtn.addEventListener('click', async () => {
        const message = messageInput.value.trim();
        if (message) {
            addUserMessage(message);
            messageInput.value = '';
            await sendProofreadRequest(message);
        }
    });

    // Enter 鍵發送
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    // 清除對話按鈕
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            clearChat();
        });
    }

    console.log('✅ 校稿功能已初始化');
}

/**
 * 清除校稿對話記憶
 */
function clearChat() {
    if (!confirm('確定要清除對話記憶嗎？這將開始一個新的對話。')) {
        return;
    }

    // 重置 session ID
    proofreadSessionId = null;

    // 清除對話框內容（保留初始歡迎訊息）
    const messagesContainer = $('#pr-chatMessages');
    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div class="pr-message pr-ai">
                <div class="pr-avatar pr-ai-avatar">
                    <img src="./proofreading.png" alt="校稿助理" onerror="this.style.display='none';this.closest('.pr-ai-avatar').classList.add('fallback');">
                    <span class="fallback-text">校</span>
                </div>
                <div class="pr-bubble">您好～我在這裡幫你校正文稿、逐字稿。請直接貼上文字。</div>
            </div>
        `;
    }

    showNotification('對話已清除，已開始新的對話', 'success');
}

/**
 * 添加用戶消息到對話框
 * @param {string} text - 用戶消息文字
 */
function addUserMessage(text) {
    const messagesContainer = $('#pr-chatMessages');
    if (!messagesContainer) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'pr-message pr-user';
    messageDiv.innerHTML = `
        <div class="pr-avatar"></div>
        <div class="pr-bubble">${escapeHtml(text)}</div>
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * 添加 AI 消息到對話框
 * @param {string} text - AI 回應文字
 * @param {Array<string>} sources - 參考來源（可選）
 */
function addAIMessage(text, sources = []) {
    const messagesContainer = $('#pr-chatMessages');
    if (!messagesContainer) return;

    // 建立來源顯示
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        const sourcesList = sources.map(s =>
            `<span style="display: inline-block; padding: 2px 8px; background: #e0f2fe; color: #0369a1; border-radius: 4px; font-size: 0.75rem; margin: 2px;">📄 ${escapeHtml(s)}</span>`
        ).join('');

        sourcesHtml = `
            <div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #e5e7eb; font-size: 0.85rem; color: #6b7280;">
                <span style="font-weight: 500;">📚 參考來源：</span>
                <div style="margin-top: 0.25rem;">${sourcesList}</div>
            </div>
        `;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = 'pr-message pr-ai';
    messageDiv.innerHTML = `
        <div class="pr-avatar pr-ai-avatar">
            <img src="./proofreading.png" alt="校稿助理" onerror="this.style.display='none';this.closest('.pr-ai-avatar').classList.add('fallback');">
            <span class="fallback-text">校</span>
        </div>
        <div class="pr-bubble">
            ${escapeHtml(text)}
            ${sourcesHtml}
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * 顯示加載消息
 * @returns {Element} 加載消息元素
 */
function showLoading() {
    const messagesContainer = $('#pr-chatMessages');
    if (!messagesContainer) return null;

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'pr-message pr-ai';
    loadingDiv.innerHTML = `
        <div class="pr-avatar pr-ai-avatar">
            <img src="./proofreading.png" alt="校稿助理" onerror="this.style.display='none';this.closest('.pr-ai-avatar').classList.add('fallback');">
            <span class="fallback-text">校</span>
        </div>
        <div class="pr-bubble">正在校對中...</div>
    `;

    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return loadingDiv;
}

/**
 * 移除加載消息
 * @param {Element} loadingElement - 加載消息元素
 */
function hideLoading(loadingElement) {
    if (loadingElement && loadingElement.parentNode) {
        loadingElement.parentNode.removeChild(loadingElement);
    }
}

/**
 * 發送校稿請求
 * @param {string} userMessage - 用戶消息
 */
async function sendProofreadRequest(userMessage) {
    const loadingDiv = showLoading();

    try {
        // 判斷是否為首次對話
        const isFirstMessage = !proofreadSessionId;
        console.log('📝 校稿請求 - session_id:', proofreadSessionId, '首次對話:', isFirstMessage);

        // 調用 API
        const result = await APIClient.staff.proofread(userMessage, proofreadSessionId, isFirstMessage);
        console.log('📡 API 返回:', result);

        // 移除加載訊息
        hideLoading(loadingDiv);

        if (result.success) {
            // 更新會話 ID
            proofreadSessionId = result.session_id;
            console.log('✅ 會話 ID 已更新:', proofreadSessionId);

            // 顯示 AI 回應
            addAIMessage(result.response, result.sources);
        } else {
            // 顯示錯誤訊息
            addAIMessage(`抱歉，校對過程中發生錯誤：${result.error}`);
        }
    } catch (error) {
        // 移除加載訊息
        hideLoading(loadingDiv);

        // 顯示錯誤
        console.error('❌ 校稿請求失敗:', error);
        addAIMessage('抱歉，校對過程中發生未預期錯誤');
        showNotification('校稿請求失敗', 'error');
    }
}

/**
 * 導出清除對話函數（供外部調用）
 * @export
 */
export function clearProofreadChat() {
    clearChat();
}

/**
 * 導出獲取當前 session ID（供外部調用）
 * @export
 */
export function getSessionId() {
    return proofreadSessionId;
}
