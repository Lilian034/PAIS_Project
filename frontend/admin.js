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
});

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
    initDocumentSort()
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

function handleDocumentUpload(files) {
    Array.from(files).forEach(file => {
        const fileItem = createDocumentItem(file);
        const documentsList = document.querySelector('.documents-list');
        documentsList.appendChild(fileItem);
        
        const empty = documentsList.querySelector('.empty-state');
        if (empty) empty.classList.add('hidden');
    });
    
    showNotification('文檔已加入清單！', 'success');
}

function viewFile(btn) {
    const url = btn.getAttribute('data-url');
    if (url) {
        window.open(url, '_blank');
    } else {
        showNotification('暫無可預覽的檔案網址', 'warning');
    }
}

function deleteDocument(btn) {
    const item = btn.closest('.document-item');
    if (item) item.remove();
    
    const list = document.querySelector('.documents-list');
    const empty = list?.querySelector('.empty-state');
    if (list && !list.querySelector('.document-item') && empty) {
        empty.classList.remove('hidden');
    }
    showNotification('已刪除', 'success');
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
function initProofreading() {
    const sendBtn = document.getElementById('pr-sendBtn');
    const messageInput = document.getElementById('pr-messageInput');
    
    if (!sendBtn || !messageInput) return;
    
    sendBtn.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message) {
            addUserMessage(message);
            messageInput.value = '';
            simulateAIResponse(message);
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

function simulateAIResponse(userMessage) {
    setTimeout(() => {
        const messagesContainer = document.getElementById('pr-chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'pr-message pr-ai';
        messageDiv.innerHTML = `
            <div class="pr-avatar pr-ai-avatar">
                <img src="./proofreading.png" alt="校稿助理" onerror="this.style.display='none';this.closest('.pr-ai-avatar').classList.add('fallback');">
                <span class="fallback-text">校</span>
            </div>
            <div class="pr-bubble">已收到您的文稿,正在校對中...</div>
        `;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 500);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 文宣生成 ====================
function initContentGeneration() {
    // 由 HTML onclick 觸發
}

function generateContent() {
    const contentType = document.getElementById('contentType')?.value;
    const prompt = document.getElementById('genPrompt')?.value;
    
    if (!prompt?.trim()) {
        showNotification('請輸入生成指令', 'warning');
        return;
    }
    
    const outputDiv = document.getElementById('generatedContent');
    if (outputDiv) {
        outputDiv.innerHTML = '<div class="placeholder-text"><p>生成中...</p></div>';
        
        setTimeout(() => {
            outputDiv.innerHTML = `<p>這是根據您的指令生成的${contentType}內容...</p>`;
        }, 1000);
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
    alert(message);
}