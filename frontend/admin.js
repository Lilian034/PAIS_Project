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

// ==================== API 連接測試 ====================
async function checkAPIConnection() {
    try {
        // 測試公眾API
        const publicHealth = await healthCheck();
        console.log('公眾API健康狀態:', publicHealth);

        // 測試幕僚API
        const staffHealth = await staffHealthCheck();
        console.log('幕僚API健康狀態:', staffHealth);

        if (publicHealth && publicHealth.status === 'healthy' && staffHealth && staffHealth.status === 'healthy') {
            console.log('✅ 所有API服務運行正常');
        } else {
            console.warn('⚠️ 部分API服務可能未啟動');
        }
    } catch (error) {
        console.error('❌ API連接測試失敗:', error);
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

    // 載入文檔列表
    loadDocumentsList();
}

/**
 * 從後端載入文檔列表
 */
async function loadDocumentsList() {
    console.log('📂 開始載入文檔列表...');

    const documentsList = document.querySelector('.documents-list');
    let emptyState = documentsList.querySelector('.empty-state');

    // 如果沒有空狀態元素，創建一個
    if (!emptyState) {
        emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        documentsList.appendChild(emptyState);
    }

    // 顯示加載中
    emptyState.innerHTML = `
        <div class="empty-illustration">⏳</div>
        <p>正在載入文檔列表...</p>
    `;
    emptyState.classList.remove('hidden');

    try {
        console.log('📡 調用 listDocuments API...');
        const result = await listDocuments();
        console.log('📡 API 返回結果:', result);

        if (!result.success) {
            throw new Error(result.error || '未知錯誤');
        }

        // 清除舊的文檔項目（保留 header）
        const oldItems = documentsList.querySelectorAll('.document-item:not(.list-header)');
        oldItems.forEach(item => item.remove());

        if (result.documents && result.documents.length > 0) {
            // 移除空狀態
            emptyState.classList.add('hidden');

            // 獲取 list-header
            const header = documentsList.querySelector('.list-header');

            // 按路徑分組（顯示文件夾結構）
            const grouped = groupDocumentsByFolder(result.documents);

            // 添加文檔
            Object.keys(grouped).sort().forEach(folder => {
                const docs = grouped[folder];

                // 如果是子文件夾，添加文件夾標題
                if (folder && folder !== '.') {
                    const folderItem = createFolderHeader(folder);
                    documentsList.appendChild(folderItem);
                }

                // 添加該文件夾下的文件
                docs.forEach(doc => {
                    const item = createDocumentItemFromAPI(doc);
                    documentsList.appendChild(item);
                });
            });

            console.log(`✅ 已載入 ${result.documents.length} 個文檔`);
            showNotification(`✅ 已載入 ${result.documents.length} 個文檔`, 'success');
        } else {
            // 顯示空狀態
            emptyState.classList.remove('hidden');
            emptyState.innerHTML = `
                <div class="empty-illustration">📂</div>
                <p>尚未有任何上傳的文檔</p>
                <small>從左側「上傳文檔」選取檔案</small>
            `;
            console.log('📂 知識庫中沒有文檔');
        }
    } catch (error) {
        console.error('❌ 載入文檔列表失敗:', error);
        emptyState.classList.remove('hidden');
        emptyState.innerHTML = `
            <div class="empty-illustration">❌</div>
            <p>載入文檔列表失敗</p>
            <small>${error.message}</small>
            <br><br>
            <button class="btn btn-primary btn-sm" onclick="loadDocumentsList()" style="margin-top: 10px;">重試</button>
        `;
        showNotification(`❌ 載入失敗: ${error.message}`, 'error');
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
    
    const listEl = section.querySelector('.documents-list');
    const applyBtn = section.querySelector('.docs-actions .btn');
    const selectEl = section.querySelector('.docs-actions .select');
    if (!listEl || !applyBtn || !selectEl) return;
    
    applyBtn.addEventListener('click', () => {
        const mode = selectEl.value || 'newest';
        
        // 只選擇 document-item 但排除 list-header
        const items = Array.from(listEl.querySelectorAll('.document-item:not(.list-header)'));
        
        if (items.length === 0) {
            showNotification('沒有可排序的項目', 'warning');
            return;
        }
        
        const keyed = items.map(el => ({
            el,
            ts: getTimeMs(el)
        }));
        
        switch (mode) {
            case 'oldest':
                keyed.sort((a, b) => (a.ts || 0) - (b.ts || 0));
                break;
            case 'newest':
            default:
                keyed.sort((a, b) => (b.ts || 0) - (a.ts || 0));
                break;
        }
        
        // 重新排列(表頭會自動保持在最前面)
        keyed.forEach(k => listEl.appendChild(k.el));
        
        showNotification('已套用排序', 'success');
    });
}

function getFileName(item) {
    const el = item.querySelector('.file-name');
    if (!el) return '';
    let txt = el.textContent || '';
    return txt.replace(/\s+/g, ' ').trim().toLowerCase();
}

function getTimeMs(item) {
    if (item.dataset.ts) return parseInt(item.dataset.ts, 10) || 0;
    
    const spans = item.querySelectorAll('span');
    const timeStr = spans[1]?.textContent?.trim() || '';
    const ms = parseTimeToMs(timeStr);
    if (ms) item.dataset.ts = String(ms);
    return ms;
}

function parseTimeToMs(s) {
    if (!s) return 0;
    s = s.trim().replace(/\s+/g, ' ').replace(/-/g, '/');
    
    const m = s.match(/(\d{4})\/(\d{1,2})\/(\d{1,2})\s+(\d{1,2}):(\d{2})/);
    if (m) {
        const [, y, mo, d, h, mi] = m;
        return new Date(+y, +mo - 1, +d, +h, +mi).getTime();
    }
    
    const t = Date.parse(s);
    return isNaN(t) ? 0 : t;
}

function createDocumentItem(file) {
    const item = document.createElement('div');
    item.className = 'document-item document-item--3';
    
    const now = new Date();
    const timeString = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
    const fileUrl = URL.createObjectURL(file);
    
    item.innerHTML = `
        <span class="file-name">${file.name}</span>
        <span>${timeString}</span>
        <div class="actions">
            <button class="btn-small danger" onclick="deleteDocument(this)">刪除</button>
            <button class="btn-small" data-url="${fileUrl}" onclick="viewFile(this)">查看檔案</button>
        </div>
    `;
    return item;
}

async function handleDocumentUpload(files) {
    let uploadCount = 0;
    let successCount = 0;

    for (const file of Array.from(files)) {
        try {
            uploadCount++;
            showNotification(`正在上傳 ${file.name}... (${uploadCount}/${files.length})`, 'info');

            // 調用 API 上傳文件
            const result = await uploadFile(file);

            if (result.success) {
                successCount++;
                showNotification(`✅ ${file.name} 上傳成功！已加入知識庫 (${result.chunks || 0} 個分塊)`, 'success');
            } else {
                showNotification(`❌ ${file.name} 上傳失敗: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('上傳錯誤:', error);
            showNotification(`❌ ${file.name} 上傳失敗: ${error.message}`, 'error');
        }
    }

    // 上傳完成後重新載入文檔列表
    if (successCount > 0) {
        showNotification(`✅ 上傳完成！成功 ${successCount} 個，共 ${uploadCount} 個`, 'success');
        await loadDocumentsList();
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
            // 重新載入文檔列表
            await loadDocumentsList();
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
        // 調用校稿 API
        const result = await proofreadContent(userMessage, proofreadSessionId);

        // 移除加載訊息
        messagesContainer.removeChild(loadingDiv);

        if (result.success) {
            // 更新會話ID
            proofreadSessionId = result.session_id;

            // 顯示 AI 回應
            const messageDiv = document.createElement('div');
            messageDiv.className = 'pr-message pr-ai';
            messageDiv.innerHTML = `
                <div class="pr-avatar pr-ai-avatar">
                    <img src="./proofreading.png" alt="校稿助理" onerror="this.style.display='none';this.closest('.pr-ai-avatar').classList.add('fallback');">
                    <span class="fallback-text">校</span>
                </div>
                <div class="pr-bubble">${escapeHtml(result.response)}</div>
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