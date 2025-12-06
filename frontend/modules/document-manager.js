/**
 * 文檔管理模組
 * 負責知識庫文檔的上傳、列表、刪除、搜尋、排序等功能
 */

import { $, $$, addClass, removeClass, show, hide, createElement, escapeHtml, formatFileSize, getFileIcon, formatDateTime, pad } from '../utils/dom-helper.js';
import { showNotification, confirm } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// ==================== 模組狀態 ====================

let documentSortMode = 'newest'; // 'newest', 'oldest'
let allDocuments = []; // 緩存所有文檔
let filteredDocuments = []; // 過濾後的文檔

// ==================== 公開函數 ====================

/**
 * 初始化文檔管理功能
 * @export
 */
export function init() {
    initUpload();
    initSearch();
    initSort();
    loadDocuments();
    loadFolders();

    console.log('✅ 文檔管理已初始化');
}

/**
 * 刷新文檔列表
 * @export
 */
export async function refreshList() {
    await loadDocuments();
}

// ==================== 初始化子功能 ====================

/**
 * 初始化上傳功能
 */
function initUpload() {
    const uploadInput = $('#documentUpload');
    if (uploadInput) {
        uploadInput.addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                await handleUpload(e.target.files);
                e.target.value = ''; // 重置 input
            }
        });
    }
}

/**
 * 初始化搜尋功能
 */
function initSearch() {
    const searchInput = $('#documentSearch');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const keyword = e.target.value.trim().toLowerCase();

        if (keyword === '') {
            // 顯示所有文檔
            filteredDocuments = [...allDocuments];
        } else {
            // 過濾文檔
            filteredDocuments = allDocuments.filter(doc =>
                doc.filename.toLowerCase().includes(keyword) ||
                doc.path.toLowerCase().includes(keyword)
            );
        }

        renderDocumentsList(filteredDocuments);
    });
}

/**
 * 初始化排序功能
 */
function initSort() {
    const sortSelect = $('#documentSort');
    if (!sortSelect) return;

    sortSelect.addEventListener('change', (e) => {
        documentSortMode = e.target.value;
        renderDocumentsList(filteredDocuments);
    });
}

// ==================== 文檔載入 ====================

/**
 * 載入文檔列表
 */
async function loadDocuments() {
    const documentsList = $('.documents-list');
    if (!documentsList) return;

    let emptyState = documentsList.querySelector('.empty-state');

    if (!emptyState) {
        emptyState = createElement('div', { className: 'empty-state' });
        documentsList.appendChild(emptyState);
    }

    // 顯示加載狀態
    emptyState.innerHTML = '<div class="empty-illustration">⏳</div><p>正在載入文檔列表...</p>';
    removeClass(emptyState, 'hidden');

    try {
        const result = await APIClient.documents.list();

        if (!result.success) {
            throw new Error(result.error || '未知錯誤');
        }

        // 緩存文檔
        allDocuments = result.documents || [];
        filteredDocuments = [...allDocuments];

        // 渲染列表
        renderDocumentsList(filteredDocuments);

        // 處理空狀態
        if (allDocuments.length === 0) {
            removeClass(emptyState, 'hidden');
            emptyState.innerHTML = `
                <div class="empty-illustration">📂</div>
                <p>尚未有任何上傳的文檔</p>
                <small>從左側「上傳文檔」選取檔案</small>
            `;
        } else {
            addClass(emptyState, 'hidden');
        }

    } catch (error) {
        console.error('❌ 載入文檔列表失敗:', error);
        removeClass(emptyState, 'hidden');
        emptyState.innerHTML = `
            <div class="empty-illustration">❌</div>
            <p>載入文檔列表失敗</p>
            <small>${escapeHtml(error.message)}</small>
        `;
        showNotification(`載入失敗: ${error.message}`, 'error');
    }
}

/**
 * 渲染文檔列表
 * @param {Array} documents - 要顯示的文檔列表
 */
function renderDocumentsList(documents) {
    const documentsList = $('.documents-list');
    if (!documentsList) return;

    // 移除舊的文檔項目（保留空狀態）
    const oldItems = documentsList.querySelectorAll('.document-item:not(.list-header), .folder-header');
    oldItems.forEach(item => item.remove());

    if (documents.length === 0) {
        const emptyState = documentsList.querySelector('.empty-state');
        if (emptyState) {
            removeClass(emptyState, 'hidden');
            emptyState.innerHTML = `
                <div class="empty-illustration">🔍</div>
                <p>沒有找到符合條件的文檔</p>
            `;
        }
        return;
    }

    // 按文件夾分組
    const grouped = groupByFolder(documents);

    // 排序並渲染
    Object.keys(grouped).sort().forEach(folder => {
        const sortedDocs = sortDocuments(grouped[folder], documentSortMode);

        // 添加文件夾標題
        if (folder && folder !== '.') {
            documentsList.appendChild(createFolderHeader(folder));
        }

        // 添加文檔項目
        sortedDocs.forEach(doc => {
            documentsList.appendChild(createDocumentItem(doc));
        });
    });
}

// ==================== 文檔操作 ====================

/**
 * 處理文檔上傳
 * @param {FileList} files - 要上傳的文件列表
 */
async function handleUpload(files) {
    const totalFiles = files.length;

    if (totalFiles === 0) return;

    showNotification(`開始上傳 ${totalFiles} 個文件...`, 'info');

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];

        try {
            const result = await APIClient.documents.uploadDocument(file);

            if (result.success) {
                successCount++;
                console.log(`✅ 上傳成功: ${file.name}`);
            } else {
                failCount++;
                console.error(`❌ 上傳失敗: ${file.name}`, result.error);
            }
        } catch (error) {
            failCount++;
            console.error(`❌ 上傳失敗: ${file.name}`, error);
        }
    }

    // 顯示結果
    if (successCount > 0) {
        showNotification(`✅ 成功上傳 ${successCount} 個文件`, 'success');
        await loadDocuments(); // 刷新列表
    }

    if (failCount > 0) {
        showNotification(`❌ ${failCount} 個文件上傳失敗`, 'error');
    }
}

/**
 * 刪除文檔
 * @param {string} filePath - 文件路徑
 * @param {string} filename - 文件名稱
 */
async function deleteDocument(filePath, filename) {
    if (!confirm(`確定要刪除文檔「${filename}」嗎？\n此操作無法復原。`)) {
        return;
    }

    try {
        const result = await APIClient.documents.delete(filePath);

        if (result.success) {
            showNotification(`✅ 已刪除: ${filename}`, 'success');
            await loadDocuments(); // 刷新列表
        } else {
            throw new Error(result.error || '刪除失敗');
        }
    } catch (error) {
        console.error('❌ 刪除文檔失敗:', error);
        showNotification(`刪除失敗: ${error.message}`, 'error');
    }
}

/**
 * 下載文檔
 * @param {string} filePath - 文件路徑
 * @param {string} filename - 文件名稱
 */
function downloadDocument(filePath, filename) {
    const downloadUrl = `/api/documents/${encodeURIComponent(filePath)}/download`;

    const link = createElement('a', {
        href: downloadUrl,
        download: filename,
        style: { display: 'none' }
    });

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showNotification(`📥 開始下載: ${filename}`, 'info');
}

/**
 * 查看文檔
 * @param {string} filePath - 文件路徑
 * @param {string} filename - 文件名稱
 */
function viewDocument(filePath, filename) {
    const viewUrl = `/api/documents/${encodeURIComponent(filePath)}/download`;
    window.open(viewUrl, '_blank');
}

// ==================== 輔助函數 ====================

/**
 * 按文件夾分組
 * @param {Array} documents - 文檔列表
 * @returns {Object}
 */
function groupByFolder(documents) {
    const grouped = {};

    documents.forEach(doc => {
        const pathParts = doc.path.split('/');
        const folder = pathParts.length > 1 ? pathParts.slice(0, -1).join('/') : '.';

        if (!grouped[folder]) {
            grouped[folder] = [];
        }
        grouped[folder].push(doc);
    });

    return grouped;
}

/**
 * 排序文檔
 * @param {Array} documents - 文檔列表
 * @param {string} mode - 排序模式 ('newest', 'oldest')
 * @returns {Array}
 */
function sortDocuments(documents, mode) {
    return documents.sort((a, b) => {
        const dateA = new Date(a.uploaded_at);
        const dateB = new Date(b.uploaded_at);
        return mode === 'newest' ? dateB - dateA : dateA - dateB;
    });
}

/**
 * 創建文件夾標題元素
 * @param {string} folderPath - 文件夾路徑
 * @returns {HTMLElement}
 */
function createFolderHeader(folderPath) {
    const item = createElement('div', { className: 'folder-header' });
    item.style.cssText = `
        padding: 0.75rem 1rem;
        background: #f3f4f6;
        border-left: 3px solid #3b82f6;
        margin: 0.5rem 0;
        font-weight: 600;
        color: #1f2937;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    `;
    item.innerHTML = `
        <span style="font-size: 1.2em;">📁</span>
        <span>${escapeHtml(folderPath)}</span>
    `;
    return item;
}

/**
 * 創建文檔項目元素
 * @param {Object} doc - 文檔對象
 * @returns {HTMLElement}
 */
function createDocumentItem(doc) {
    const item = createElement('div', {
        className: 'document-item document-item--3'
    });

    item.dataset.filePath = doc.path;
    item.dataset.filename = doc.filename;

    // 格式化時間
    const uploadDate = new Date(doc.uploaded_at);
    const timeString = formatDateTime(uploadDate);

    // 格式化文件大小
    const sizeStr = formatFileSize(doc.size);

    // 獲取文件圖標
    const fileIcon = getFileIcon(doc.extension);

    item.innerHTML = `
        <span class="file-name" title="${escapeHtml(doc.path)}">
            ${fileIcon} ${escapeHtml(doc.filename)}
            <small style="color: #6b7280; font-size: 0.75rem; margin-left: 0.5rem;">${sizeStr}</small>
        </span>
        <span title="${escapeHtml(doc.uploaded_at)}">${timeString}</span>
        <div class="actions">
            <button class="btn-icon" onclick="window.documentManager.view('${escapeHtml(doc.path)}', '${escapeHtml(doc.filename)}')" title="查看">
                👁️
            </button>
            <button class="btn-icon" onclick="window.documentManager.download('${escapeHtml(doc.path)}', '${escapeHtml(doc.filename)}')" title="下載">
                📥
            </button>
            <button class="btn-icon btn-danger" onclick="window.documentManager.delete('${escapeHtml(doc.path)}', '${escapeHtml(doc.filename)}')" title="刪除">
                🗑️
            </button>
        </div>
    `;

    return item;
}

// ==================== 資料夾管理 ====================

/**
 * 載入資料夾列表
 */
async function loadFolders() {
    try {
        const result = await APIClient.documents.list();

        if (!result.success) return;

        const documents = result.documents || [];
        const folders = new Set();

        documents.forEach(doc => {
            const pathParts = doc.path.split('/');
            if (pathParts.length > 1) {
                for (let i = 1; i <= pathParts.length - 1; i++) {
                    folders.add(pathParts.slice(0, i).join('/'));
                }
            }
        });

        const folderList = $('#folderList');
        if (folderList && folders.size > 0) {
            folderList.innerHTML = Array.from(folders).sort()
                .map(folder => `
                    <option value="${escapeHtml(folder)}">${escapeHtml(folder)}</option>
                `).join('');
        }
    } catch (error) {
        console.error('❌ 載入資料夾列表失敗:', error);
    }
}

/**
 * 顯示新增資料夾對話框
 */
function showNewFolderDialog() {
    const folderName = window.prompt('請輸入新資料夾名稱：', '');

    if (!folderName) {
        return; // 使用者取消
    }

    // 清理資料夾名稱
    const cleanFolderName = folderName.trim().replace(/[\/\\:*?"<>|]/g, '-');

    if (!cleanFolderName) {
        showNotification('資料夾名稱無效', 'error');
        return;
    }

    // 將新資料夾添加到下拉選單
    const folderSelect = $('#uploadFolder');
    if (folderSelect) {
        const option = createElement('option', {
            value: cleanFolderName
        }, `📁 ${cleanFolderName}`);

        folderSelect.appendChild(option);
        folderSelect.value = cleanFolderName; // 自動選擇新資料夾

        showNotification(`已建立資料夾「${cleanFolderName}」，可以開始上傳文件`, 'success');
    }
}

// ==================== 全局導出（供 HTML 內聯事件使用） ====================

if (typeof window !== 'undefined') {
    window.documentManager = {
        view: viewDocument,
        download: downloadDocument,
        delete: deleteDocument,
        refresh: refreshList
    };

    // 導出資料夾對話框函數
    window.showNewFolderDialog = showNewFolderDialog;
}
