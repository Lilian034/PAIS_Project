document.addEventListener('DOMContentLoaded', () => {
    initTabSwitching();
    initDocumentManagement();
    initMediaUpload();
    initProofreading();
    initContentGeneration();
    initVoiceGeneration();
    initVideoGeneration();
    initDataMonitoring();
    initLogout();

    // 測試API連接
    checkAPIConnection();
});

async function checkAPIConnection() {
    try {
        const [publicHealth, staffHealth] = await Promise.all([healthCheck(), staffHealthCheck()]);
        const allHealthy = publicHealth?.status === 'healthy' && staffHealth?.status === 'healthy';
        if (!allHealthy) console.warn('部分API服務可能未啟動');
    } catch (error) {
        console.error('API連接測試失敗:', error);
    }
}

// ==================== 標籤切換 ====================
function initTabSwitching() {
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            item.classList.add('active');
            document.getElementById(tabId)?.classList.add('active');
        });
    });
}

// ==================== 政務文檔管理 ====================

// 全局排序模式
let documentSortMode = 'newest'; // 'newest', 'oldest'

function initDocumentManagement() {
    const uploadInput = document.getElementById('documentUpload');
    if (uploadInput) {
        uploadInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleDocumentUpload(e.target.files);
            }
        });
    }

    initDocumentSearch();
    initDocumentSort();

    // 載入文檔列表和資料夾列表
    loadDocumentsList();
    loadFoldersList();
}

async function loadDocumentsList() {
    const documentsList = document.querySelector('.documents-list');
    let emptyState = documentsList.querySelector('.empty-state');

    if (!emptyState) {
        emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        documentsList.appendChild(emptyState);
    }

    emptyState.innerHTML = '<div class="empty-illustration">⏳</div><p>正在載入文檔列表...</p>';
    emptyState.classList.remove('hidden');

    try {
        const result = await listDocuments();
        if (!result.success) throw new Error(result.error || '未知錯誤');

        const oldItems = documentsList.querySelectorAll('.document-item:not(.list-header), .folder-header');
        oldItems.forEach(item => item.remove());

        if (result.documents && result.documents.length > 0) {
            emptyState.classList.add('hidden');
            const grouped = groupDocumentsByFolder(result.documents);

            Object.keys(grouped).sort().forEach(folder => {
                let docs = sortDocumentsByMode(grouped[folder], documentSortMode);

                if (folder && folder !== '.') {
                    documentsList.appendChild(createFolderHeader(folder));
                }

                docs.forEach(doc => {
                    documentsList.appendChild(createDocumentItemFromAPI(doc));
                });
            });
        } else {
            emptyState.classList.remove('hidden');
            emptyState.innerHTML = `
                <div class="empty-illustration">📂</div>
                <p>尚未有任何上傳的文檔</p>
                <small>從左側「上傳文檔」選取檔案</small>
            `;
        }
    } catch (error) {
        console.error('載入文檔列表失敗:', error);
        emptyState.classList.remove('hidden');
        emptyState.innerHTML = `
            <div class="empty-illustration">❌</div>
            <p>載入文檔列表失敗</p>
            <small>${error.message}</small>
            <br><br>
            <button class="btn btn-primary btn-sm" onclick="loadDocumentsList()" style="margin-top: 10px;">重試</button>
        `;
        showNotification(`載入失敗: ${error.message}`, 'error');
    }
}

/**
 * 按文件夾分組文檔
 */
function groupDocumentsByFolder(documents) {
    const grouped = {};

    documents.forEach(doc => {
        // 獲取文件夾路徑
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
 * 創建文件夾標題
 */
function createFolderHeader(folderPath) {
    const item = document.createElement('div');
    item.className = 'folder-header';
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
        <span>${folderPath}</span>
    `;
    return item;
}

/**
 * 從 API 資料創建文檔項目
 */
function createDocumentItemFromAPI(doc) {
    const item = document.createElement('div');
    item.className = 'document-item document-item--3';
    item.dataset.filePath = doc.path;
    item.dataset.filename = doc.filename;

    // 格式化時間
    const uploadDate = new Date(doc.uploaded_at);
    const timeString = `${uploadDate.getFullYear()}-${pad(uploadDate.getMonth() + 1)}-${pad(uploadDate.getDate())} ${pad(uploadDate.getHours())}:${pad(uploadDate.getMinutes())}`;

    // 格式化文件大小
    const sizeStr = formatFileSize(doc.size);

    // 獲取文件圖標
    const fileIcon = getFileIcon(doc.extension);

    item.innerHTML = `
        <span class="file-name" title="${doc.path}">
            ${fileIcon} ${doc.filename}
            <small style="color: #6b7280; font-size: 0.75rem; margin-left: 0.5rem;">${sizeStr}</small>
        </span>
        <span title="${doc.uploaded_at}">${timeString}</span>
        <div class="actions">
            <button class="btn-small" onclick="downloadDocumentFile(this)" title="下載">📥 下載</button>
            <button class="btn-small danger" onclick="deleteDocumentFromBackend(this)" title="刪除">🗑️ 刪除</button>
        </div>
    `;
    return item;
}

/**
 * 獲取文件圖標
 */
function getFileIcon(extension) {
    const iconMap = {
        '.pdf': '📕',
        '.doc': '📘',
        '.docx': '📘',
        '.txt': '📄',
        '.xls': '📊',
        '.xlsx': '📊',
        '.ppt': '📙',
        '.pptx': '📙',
        '.jpg': '🖼️',
        '.jpeg': '🖼️',
        '.png': '🖼️',
        '.gif': '🖼️',
        '.zip': '📦',
        '.rar': '📦',
        '.md': '📝'
    };
    return iconMap[extension] || '📄';
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function initDocumentSearch() {
    const root = document.querySelector('#documents');
    if (!root) return;
    
    const input = root.querySelector('.search-input');
    const list = root.querySelector('.documents-list');
    if (!input || !list) return;
    
    input.addEventListener('input', () => {
        const query = input.value.trim().toLowerCase();
        list.querySelectorAll('.document-item').forEach(item => {
            const fileName = getFileName(item);
            item.style.display = (!query || fileName.includes(query)) ? '' : 'none';
        });
    });
}

function initDocumentSort() {
    const section = document.querySelector('#documents');
    if (!section) return;

    const applyBtn = section.querySelector('.docs-actions .btn');
    const selectEl = section.querySelector('.docs-actions .select');
    if (!applyBtn || !selectEl) return;

    applyBtn.addEventListener('click', async () => {
        const mode = selectEl.value || 'newest';
        documentSortMode = mode;

        // 重新載入文檔列表以應用排序
        await loadDocumentsList();
        showNotification('已套用排序', 'success');
    });
}

/**
 * 根據排序模式排序文檔
 */
function sortDocumentsByMode(docs, mode) {
    if (!docs || docs.length === 0) return docs;

    const sorted = [...docs];

    switch (mode) {
        case 'oldest':
            sorted.sort((a, b) => {
                const timeA = new Date(a.uploaded_at).getTime();
                const timeB = new Date(b.uploaded_at).getTime();
                return timeA - timeB;
            });
            break;
        case 'newest':
        default:
            sorted.sort((a, b) => {
                const timeA = new Date(a.uploaded_at).getTime();
                const timeB = new Date(b.uploaded_at).getTime();
                return timeB - timeA;
            });
            break;
    }

    return sorted;
}

function getFileName(item) {
    const el = item.querySelector('.file-name');
    if (!el) return '';
    return (el.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

async function handleDocumentUpload(files) {
    let uploadCount = 0;
    let successCount = 0;
    let failedFiles = [];

    // 獲取選擇的資料夾
    const folderSelect = document.getElementById('uploadFolder');
    const selectedFolder = folderSelect ? folderSelect.value : '';

    const folderDisplay = selectedFolder ? `/${selectedFolder}` : '根目錄';

    // 顯示開始上傳的通知
    showNotification(`正在上傳 ${files.length} 個文件到 ${folderDisplay}...`, 'info');

    for (const file of Array.from(files)) {
        try {
            uploadCount++;

            // 調用 API 上傳文件，傳入資料夾參數
            const result = await uploadFile(file, selectedFolder);

            if (result.success) {
                successCount++;
            } else {
                failedFiles.push({ name: file.name, error: result.error });
            }
        } catch (error) {
            console.error('上傳錯誤:', error);
            failedFiles.push({ name: file.name, error: error.message });
        }
    }

    // 上傳完成後重新載入文檔列表和資料夾列表
    if (uploadCount > 0) {
        await loadDocumentsList();
        await loadFoldersList();

        // 顯示最終結果
        if (successCount === uploadCount) {
            showNotification(`✅ 上傳成功！已上傳 ${successCount} 個文件`, 'success');
        } else if (successCount > 0) {
            showNotification(`⚠️ 部分上傳成功：成功 ${successCount} 個，失敗 ${failedFiles.length} 個`, 'warning');
            // 在 console 中顯示失敗詳情
            console.error('上傳失敗的文件:', failedFiles);
        } else {
            showNotification(`❌ 上傳失敗：所有文件都無法上傳`, 'error');
            console.error('上傳失敗的文件:', failedFiles);
        }
    }
}

function viewFile(btn) {
    const url = btn.getAttribute('data-url');
    if (url) {
        window.open(url, '_blank');
    } else {
        showNotification('暫無可預覽的檔案網址', 'warning');
    }
}

/**
 * 下載文檔文件
 */
async function downloadDocumentFile(btn) {
    const item = btn.closest('.document-item');
    if (!item) return;

    const filePath = item.dataset.filePath;
    const fileName = item.dataset.filename || '文件';

    if (!filePath) {
        showNotification('無法獲取文件路徑', 'error');
        return;
    }

    try {
        showNotification(`正在準備下載 ${fileName}...`, 'info');

        // 構建下載 URL
        const downloadUrl = `/api/documents/${encodeURIComponent(filePath)}/download`;

        // 創建隱藏的 a 標籤進行下載
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = fileName;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        showNotification(`✅ 開始下載 ${fileName}`, 'success');
    } catch (error) {
        console.error('下載錯誤:', error);
        showNotification(`❌ 下載失敗: ${error.message}`, 'error');
    }
}

/**
 * 從後端刪除文檔
 */
async function deleteDocumentFromBackend(btn) {
    const item = btn.closest('.document-item');
    if (!item) return;

    const filePath = item.dataset.filePath;
    const fileName = item.dataset.filename || '文件';

    if (!filePath) {
        showNotification('無法獲取文件路徑', 'error');
        return;
    }

    // 確認刪除
    if (!confirm(`確定要刪除「${fileName}」嗎？此操作無法恢復。`)) {
        return;
    }

    try {
        showNotification(`正在刪除 ${fileName}...`, 'info');

        // 調用 API 刪除文件
        const result = await deleteDocument(filePath);

        if (result.success) {
            showNotification(`✅ ${fileName} 已刪除`, 'success');
            // 重新載入文檔列表和資料夾列表
            await loadDocumentsList();
            await loadFoldersList();
        } else {
            showNotification(`❌ 刪除失敗: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('刪除錯誤:', error);
        showNotification(`❌ 刪除失敗: ${error.message}`, 'error');
    }
}

function pad(n) {
    return String(n).padStart(2, '0');
}

// ==================== 媒體上傳 ====================
function initMediaUpload() {
    const photoUpload = document.getElementById('photoUpload');
    if (photoUpload) {
        photoUpload.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handlePhotoUpload(e.target.files);
            }
        });
    }
    
    const audioUpload = document.getElementById('audioUpload');
    if (audioUpload) {
        audioUpload.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleAudioUpload(e.target.files);
            }
        });
    }
}

function handlePhotoUpload(files) {
    const photoGrid = document.querySelector('.photo-grid');
    const addPhotoBtn = photoGrid?.querySelector('.add-photo');
    if (!photoGrid || !addPhotoBtn) return;
    
    Array.from(files).forEach(file => {
        if (photoGrid.children.length < 6) {
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            
            const img = document.createElement('img');
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'cover';
            
            const reader = new FileReader();
            reader.onload = (e) => {
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
            
            photoItem.appendChild(img);
            photoGrid.insertBefore(photoItem, addPhotoBtn);
        }
    });
    
    showNotification('照片上傳成功！', 'success');
}

function handleAudioUpload(files) {
    const audioBox = document.querySelector('#media .audio-single');
    if (!audioBox || !files || !files.length) return;
    
    const addBtn = audioBox.querySelector('.add-audio');
    const file = files[0];
    const url = URL.createObjectURL(file);
    
    if (addBtn) {
        addBtn.classList.add('has-preview');
        addBtn.innerHTML = '';
        
        const chip = document.createElement('div');
        chip.className = 'audio-chip';
        
        const playBtn = document.createElement('button');
        playBtn.className = 'play';
        playBtn.textContent = '▶︎ 播放';
        
        const name = document.createElement('span');
        name.className = 'name';
        name.textContent = file.name || '已選音檔';
        
        const audio = new Audio(url);
        let playing = false;
        
        playBtn.onclick = () => {
            if (!playing) {
                audio.play();
                playing = true;
                playBtn.textContent = '⏸ 暫停';
            } else {
                audio.pause();
                playing = false;
                playBtn.textContent = '▶︎ 播放';
            }
        };
        
        audio.onended = () => {
            playing = false;
            playBtn.textContent = '▶︎ 播放';
        };
        
        chip.appendChild(playBtn);
        chip.appendChild(name);
        addBtn.appendChild(chip);
    }
    
    showNotification('音檔已上傳', 'success');
}

// ==================== 資料校稿 ====================
let proofreadSessionId = null; // 保存會話ID

function initProofreading() {
    const sendBtn = document.getElementById('pr-sendBtn');
    const messageInput = document.getElementById('pr-messageInput');
    const clearBtn = document.getElementById('clearProofreadChat');

    if (!sendBtn || !messageInput) return;

    sendBtn.addEventListener('click', async () => {
        const message = messageInput.value.trim();
        if (message) {
            addUserMessage(message);
            messageInput.value = '';
            await sendProofreadRequest(message);
        }
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    // 清除對話按鈕
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            clearProofreadChat();
        });
    }
}

/**
 * 清除校稿對話記憶
 */
function clearProofreadChat() {
    if (!confirm('確定要清除對話記憶嗎？這將開始一個新的對話。')) {
        return;
    }

    // 重置 session ID
    proofreadSessionId = null;

    // 清除對話框內容（保留初始歡迎訊息）
    const messagesContainer = document.getElementById('pr-chatMessages');
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

    showNotification('✅ 對話已清除，已開始新的對話', 'success');
}

function addUserMessage(text) {
    const messagesContainer = document.getElementById('pr-chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'pr-message pr-user';
    messageDiv.innerHTML = `
        <div class="pr-avatar"></div>
        <div class="pr-bubble">${escapeHtml(text)}</div>
    `;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function sendProofreadRequest(userMessage) {
    const messagesContainer = document.getElementById('pr-chatMessages');

    // 顯示加載訊息
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

    try {
        // 判斷是否為首次對話（沒有 session_id）
        const isFirstMessage = !proofreadSessionId;
        console.log('📝 校稿請求 - 當前 session_id:', proofreadSessionId, '是否首次對話:', isFirstMessage);

        // 調用校稿 API
        const result = await proofreadContent(userMessage, proofreadSessionId, isFirstMessage);
        console.log('📡 API 返回:', result);

        // 移除加載訊息
        messagesContainer.removeChild(loadingDiv);

        if (result.success) {
            // 更新會話ID
            proofreadSessionId = result.session_id;
            console.log('✅ 會話 ID 已更新:', proofreadSessionId);

            // 建立來源顯示（如果有的話）
            let sourcesHtml = '';
            if (result.sources && result.sources.length > 0) {
                const sourcesList = result.sources.map(s => `<span style="display: inline-block; padding: 2px 8px; background: #e0f2fe; color: #0369a1; border-radius: 4px; font-size: 0.75rem; margin: 2px;">📄 ${escapeHtml(s)}</span>`).join('');
                sourcesHtml = `<div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #e5e7eb; font-size: 0.85rem; color: #6b7280;">
                    <span style="font-weight: 500;">📚 參考來源：</span>
                    <div style="margin-top: 0.25rem;">${sourcesList}</div>
                </div>`;
            }

            // 顯示 AI 回應
            const messageDiv = document.createElement('div');
            messageDiv.className = 'pr-message pr-ai';
            messageDiv.innerHTML = `
                <div class="pr-avatar pr-ai-avatar">
                    <img src="./proofreading.png" alt="校稿助理" onerror="this.style.display='none';this.closest('.pr-ai-avatar').classList.add('fallback');">
                    <span class="fallback-text">校</span>
                </div>
                <div class="pr-bubble">
                    ${escapeHtml(result.response)}
                    ${sourcesHtml}
                </div>
            `;
            messagesContainer.appendChild(messageDiv);
        } else {
            // 顯示錯誤訊息
            const errorDiv = document.createElement('div');
            errorDiv.className = 'pr-message pr-ai';
            errorDiv.innerHTML = `
                <div class="pr-avatar pr-ai-avatar">
                    <img src="./proofreading.png" alt="校稿助理" onerror="this.style.display='none';this.closest('.pr-ai-avatar').classList.add('fallback');">
                    <span class="fallback-text">校</span>
                </div>
                <div class="pr-bubble">抱歉，校對過程中發生錯誤：${escapeHtml(result.error)}</div>
            `;
            messagesContainer.appendChild(errorDiv);
        }
    } catch (error) {
        // 移除加載訊息
        messagesContainer.removeChild(loadingDiv);

        // 顯示錯誤
        const errorDiv = document.createElement('div');
        errorDiv.className = 'pr-message pr-ai';
        errorDiv.innerHTML = `
            <div class="pr-avatar pr-ai-avatar">
                <img src="./proofreading.png" alt="校稿助理" onerror="this.style.display='none';this.closest('.pr-ai-avatar').classList.add('fallback');">
                <span class="fallback-text">校</span>
            </div>
            <div class="pr-bubble">抱歉，校對過程中發生未預期錯誤</div>
        `;
        messagesContainer.appendChild(errorDiv);
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 文宣生成 ====================
let currentTaskId = null; // 保存當前任務ID

function initContentGeneration() {
    // 由 HTML onclick 觸發
}

async function generateContent() {
    const contentType = document.getElementById('contentType')?.value;
    const prompt = document.getElementById('genPrompt')?.value;

    if (!prompt?.trim()) {
        showNotification('請輸入生成指令', 'warning');
        return;
    }

    const outputDiv = document.getElementById('generatedContent');
    if (outputDiv) {
        outputDiv.innerHTML = '<div class="placeholder-text"><p>生成中，請稍候...</p></div>';

        try {
            // 將內容類型轉換為 style 參數
            let style = 'formal';
            switch (contentType) {
                case 'press':
                    style = 'formal';
                    break;
                case 'speech':
                    style = 'formal';
                    break;
                case 'facebook':
                    style = 'casual';
                    break;
                case 'instagram':
                    style = 'casual';
                    break;
                case 'poster':
                    style = 'concise';
                    break;
            }

            // 調用文案生成 API
            const result = await generateStaffContent(prompt, style, 'medium');

            if (result.success) {
                // 保存任務ID
                currentTaskId = result.task_id;

                // 顯示生成的內容
                outputDiv.innerHTML = `
                    <div style="white-space: pre-wrap; line-height: 1.8;">
                        ${escapeHtml(result.content)}
                    </div>
                    <div style="margin-top: 1rem; padding: 0.5rem; background: #f0f9ff; border-radius: 4px; font-size: 0.875rem; color: #0369a1;">
                        ✅ ${result.message || '文案生成完成'}
                        <br>任務ID: ${result.task_id}
                    </div>
                `;

                showNotification('✅ 文案生成成功！', 'success');
            } else {
                outputDiv.innerHTML = `
                    <div class="placeholder-text" style="color: #dc2626;">
                        <p>❌ 生成失敗: ${escapeHtml(result.error)}</p>
                    </div>
                `;
                showNotification(`生成失敗: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('生成錯誤:', error);
            outputDiv.innerHTML = `
                <div class="placeholder-text" style="color: #dc2626;">
                    <p>❌ 生成過程中發生未預期錯誤</p>
                </div>
            `;
            showNotification('生成過程中發生錯誤', 'error');
        }
    }
}

function copyDraft() {
    const content = document.getElementById('generatedContent')?.innerText;
    if (content) {
        navigator.clipboard.writeText(content).then(() => {
            showNotification('已複製到剪貼簿', 'success');
        });
    }
}

function saveDraftTxt() {
    const content = document.getElementById('generatedContent')?.innerText;
    if (content) {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '文宣內容.txt';
        a.click();
        URL.revokeObjectURL(url);
    }
}

// ==================== 語音生成 ====================
function initVoiceGeneration() {
    const saveBtn = document.getElementById('btnSaveAudio');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveAudioFile);
    }
    
    const voiceOptions = document.querySelectorAll('.voice-option');
    voiceOptions.forEach(option => {
        option.addEventListener('click', () => {
            voiceOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
        });
    });
    
    // 綁定「＋新增音檔」按鈕
    const btnVoiceUpload = document.getElementById('btnVoiceUpload');
    if (btnVoiceUpload) {
        btnVoiceUpload.addEventListener('click', openAudioAddModal);
    }
    
    // 初始化新增音檔彈窗
    initAudioAddModal();
}

function initAudioAddModal() {
    const addChooseBtn = document.getElementById('addChooseBtn');
    const addAudioInput = document.getElementById('addAudioInput');
    const addBtnClose = document.getElementById('addBtnClose');
    const addBtnCreate = document.getElementById('addBtnCreate');
    
    if (!addChooseBtn || !addAudioInput) return;
    
    // 點擊「選擇檔案」按鈕
    addChooseBtn.addEventListener('click', () => {
        addAudioInput.click();
    });
    
    // 選擇檔案後顯示檔名
    addAudioInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            addChooseBtn.innerHTML = `<span style="color: #2f3f52; font-weight: 600;">📁 ${escapeHtml(file.name)}</span>`;
        }
    });
    
    // 關閉彈窗
    if (addBtnClose) {
        addBtnClose.addEventListener('click', closeAudioAddModal);
    }
    
    // 新增音檔
    if (addBtnCreate) {
        addBtnCreate.addEventListener('click', () => {
            const file = addAudioInput.files[0];
            const emotion = document.getElementById('addEmotion')?.value.trim();
            const source = document.getElementById('addSource')?.value.trim();
            
            if (!file) {
                alert('請選擇音檔檔案');
                return;
            }
            
            if (!emotion) {
                alert('請輸入情緒');
                return;
            }
            
            // 這裡可以加入實際的新增邏輯
            showNotification(`已新增音檔: ${file.name}`, 'success');
            closeAudioAddModal();
        });
    }
}

function openAudioAddModal() {
    const modal = document.getElementById('audioAddModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
    }
    document.body.classList.add('no-scroll');
}

function closeAudioAddModal() {
    const modal = document.getElementById('audioAddModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
    }
    document.body.classList.remove('no-scroll');
    
    // 重置表單
    const addChooseBtn = document.getElementById('addChooseBtn');
    const addAudioInput = document.getElementById('addAudioInput');
    const addEmotion = document.getElementById('addEmotion');
    const addSource = document.getElementById('addSource');
    
    if (addChooseBtn) addChooseBtn.innerHTML = '＋ 選擇檔案';
    if (addAudioInput) addAudioInput.value = '';
    if (addEmotion) addEmotion.value = '';
    if (addSource) addSource.value = '';
}

function saveAudioFile() {
    showNotification('音檔已儲存', 'success');
}

// ==================== 短影音生成 ====================
function initVideoGeneration() {
    const saveBtn = document.getElementById('btnSaveVideo');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveVideoFile);
    }
}

function saveVideoFile() {
    showNotification('影片已儲存', 'success');
}

// ==================== 數據監控 ====================
function initDataMonitoring() {
    const LS_KEY = 'exposureUrls';
    const section = document.querySelector('#exposure');
    if (!section) return;

    // 記錄訪客計數（使用 sessionStorage 防止同一會話重複計數）
    const SESSION_KEY = 'admin_visitor_counted';
    if (!sessionStorage.getItem(SESSION_KEY)) {
        incrementVisitor().then(result => {
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

    let listEl = section.querySelector('.url-list');
    if (!listEl) {
        listEl = document.createElement('div');
        listEl.className = 'url-list';
        section.appendChild(listEl);
    }
    
    function load() {
        try {
            return JSON.parse(localStorage.getItem(LS_KEY) || '[]');
        } catch {
            return [];
        }
    }
    
    function save(data) {
        localStorage.setItem(LS_KEY, JSON.stringify(data));
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function normalizeUrl(url) {
        url = (url || '').trim();
        if (!url) return '';
        if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
        return url;
    }
    
    function render() {
        const data = load();
        if (!data.length) {
            listEl.innerHTML = '<div class="empty-tip">目前沒有網址,請按右上角「新增網址」。</div>';
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
    
    listEl.addEventListener('click', (e) => {
        const btn = e.target.closest('button.btn-icon');
        if (!btn) return;
        
        const row = btn.closest('.url-item');
        const id = row?.dataset.id;
        if (!id) return;
        
        const data = load();
        const item = data.find(x => String(x.id) === String(id));
        if (!item) return;
        
        if (btn.dataset.action === 'open') {
            window.open(item.url, '_blank', 'noopener');
        } else if (btn.dataset.action === 'del') {
            if (confirm(`確定要刪除「${item.name}」嗎？`)) {
                save(data.filter(x => String(x.id) !== String(id)));
                render();
            }
        }
    });
    
    function closeUrlAddModal() {
        const modal = document.getElementById('urlAddModal');
        if (modal) modal.remove();
        document.body.classList.remove('no-scroll');
    }
    
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
                alert('請輸入「網站簡稱」。');
                return;
            }
            
            const url = normalizeUrl(rawUrl);
            try {
                new URL(url);
            } catch {
                alert('請輸入正確網址');
                return;
            }
            
            const arr = load();
            arr.push({ id: Date.now(), name, url });
            save(arr);
            render();
            closeUrlAddModal();
        });
    };
    
    const addBtn = section.querySelector('.add-url-btn');
    if (addBtn) {
        addBtn.addEventListener('click', window.showAddUrlModal);
    }
    
    render();
    refreshAnalytics();
    setInterval(refreshAnalytics, 30000);
}

function refreshAnalytics() {
    // 模擬數據刷新
}

// ==================== 訪客統計 ====================
async function loadVisitorStats() {
    try {
        const result = await getVisitorStats();
        if (result.success) {
            const visitorCountEl = document.getElementById('visitorCount');
            const visitorMonthEl = document.getElementById('visitorMonth');
            const monthlyVisitorCountEl = document.getElementById('monthlyVisitorCount');

            if (visitorCountEl) {
                visitorCountEl.textContent = result.count.toLocaleString('zh-TW');
            }
            if (monthlyVisitorCountEl) {
                monthlyVisitorCountEl.textContent = result.count.toLocaleString('zh-TW');
            }
            if (visitorMonthEl) {
                visitorMonthEl.textContent = result.month;
            }
            console.log('✅ 訪客統計已更新:', result);
        } else {
            console.warn('⚠️ 載入訪客統計失敗:', result.error);
            const visitorCountEl = document.getElementById('visitorCount');
            const monthlyVisitorCountEl = document.getElementById('monthlyVisitorCount');
            if (visitorCountEl) visitorCountEl.textContent = '--';
            if (monthlyVisitorCountEl) monthlyVisitorCountEl.textContent = '--';
        }
    } catch (error) {
        console.error('❌ 載入訪客統計時發生錯誤:', error);
    }
}

// ==================== 登出 ====================
function initLogout() {
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('確定要登出嗎？')) {
                showNotification('已登出', 'success');
            }
        });
    }
}

// ==================== 通知系統 ====================
function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);

    // 創建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
        font-size: 14px;
        line-height: 1.5;
    `;

    // 根據類型設置顏色
    switch(type) {
        case 'success':
            notification.style.background = '#10b981';
            notification.style.color = 'white';
            break;
        case 'error':
            notification.style.background = '#ef4444';
            notification.style.color = 'white';
            break;
        case 'warning':
            notification.style.background = '#f59e0b';
            notification.style.color = 'white';
            break;
        default:
            notification.style.background = '#3b82f6';
            notification.style.color = 'white';
    }

    notification.textContent = message;
    document.body.appendChild(notification);

    // 3秒後自動移除
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// ==================== 資料夾管理功能 ====================

/**
 * 載入資料夾列表到下拉選單
 */
async function loadFoldersList() {
    try {
        console.log('📂 載入資料夾列表...');
        const result = await listDocuments();

        if (!result.success || !result.documents) {
            console.error('無法載入資料夾列表');
            return;
        }

        // 從文檔路徑中提取所有資料夾
        const folders = new Set();
        result.documents.forEach(doc => {
            const pathParts = doc.path.split('/');
            if (pathParts.length > 1) {
                // 提取所有層級的資料夾路徑
                for (let i = 1; i <= pathParts.length - 1; i++) {
                    const folderPath = pathParts.slice(0, i).join('/');
                    folders.add(folderPath);
                }
            }
        });

        // 將資料夾列表填入下拉選單
        const folderSelect = document.getElementById('uploadFolder');
        if (folderSelect) {
            // 保留根目錄選項
            folderSelect.innerHTML = '<option value="">根目錄 (documents/)</option>';

            // 添加所有資料夾
            const sortedFolders = Array.from(folders).sort();
            sortedFolders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder;
                option.textContent = `📁 ${folder}`;
                folderSelect.appendChild(option);
            });

            console.log(`✅ 已載入 ${sortedFolders.length} 個資料夾`);
        }
    } catch (error) {
        console.error('載入資料夾列表失敗:', error);
    }
}

/**
 * 顯示新增資料夾對話框
 */
function showNewFolderDialog() {
    const folderName = prompt('請輸入新資料夾名稱：', '');

    if (!folderName) {
        return; // 使用者取消
    }

    // 清理資料夾名稱
    const cleanFolderName = folderName.trim().replace(/[\/\\:*?"<>|]/g, '-');

    if (!cleanFolderName) {
        showNotification('❌ 資料夾名稱無效', 'error');
        return;
    }

    // 將新資料夾添加到下拉選單
    const folderSelect = document.getElementById('uploadFolder');
    if (folderSelect) {
        const option = document.createElement('option');
        option.value = cleanFolderName;
        option.textContent = `📁 ${cleanFolderName}`;
        folderSelect.appendChild(option);
        folderSelect.value = cleanFolderName; // 自動選擇新資料夾

        showNotification(`✅ 已建立資料夾「${cleanFolderName}」，可以開始上傳文件`, 'success');
    }
}

// 添加動畫樣式
if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}