document.addEventListener('DOMContentLoaded', function() {
    // 標籤切換功能
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            
            // 移除所有活動狀態
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // 設定新的活動狀態
            item.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // 文檔上傳功能
    const documentUpload = document.getElementById('documentUpload');
    if (documentUpload) {
        documentUpload.addEventListener('change', function(e) {
            const files = e.target.files;
            if (files.length > 0) {
                handleDocumentUpload(files);
            }
        });
    }

    // 照片上傳功能
    const photoUpload = document.getElementById('photoUpload');
    if (photoUpload) {
        photoUpload.addEventListener('change', function(e) {
            const files = e.target.files;
            if (files.length > 0) {
                handlePhotoUpload(files);
            }
        });
    }

    // 語音上傳功能
    const audioUpload = document.getElementById('audioUpload');
    if (audioUpload) {
        audioUpload.addEventListener('change', function(e) {
            const files = e.target.files;
            if (files.length > 0) {
                handleAudioUpload(files);
            }
        });
    }

    // 語音選項選擇
    const voiceOptions = document.querySelectorAll('.voice-option');
    voiceOptions.forEach(option => {
        option.addEventListener('click', () => {
            voiceOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
        });
    });

    // 語音測試按鈕
    const voiceTestBtns = document.querySelectorAll('.voice-test');
    voiceTestBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            playVoiceTest(btn);
        });
    });

    // 音頻播放按鈕
    const playBtns = document.querySelectorAll('.play-btn');
    playBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            playAudioSample(btn);
        });
    });

    // 滑桿設定更新
    const sliders = document.querySelectorAll('.slider');
    sliders.forEach(slider => {
        slider.addEventListener('input', function() {
            updateSliderValue(this);
        });
        
        // 初始化顯示值
        updateSliderValue(slider);
    });

    // 設定保存
    const saveSettingsBtn = document.querySelector('.save-settings');
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', saveVoiceSettings);
    }

    // 卡通形象重新生成
    const generateBtn = document.querySelector('.media-btn.generate');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateAvatar);
    }

    // 登出功能
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    // 初始化數據刷新
    refreshAnalytics();
    
    // 每30秒更新一次數據
    setInterval(refreshAnalytics, 30000);
});

// 文檔上傳處理
function handleDocumentUpload(files) {
    Array.from(files).forEach(file => {
        const fileItem = createDocumentItem(file);
        const documentsList = document.querySelector('.documents-list');
        documentsList.appendChild(fileItem);
        
        // 模擬上傳過程
        simulateUploadProcess(fileItem);
    });
    
    showNotification('文檔上傳中...', 'info');
}

// 創建文檔列表項目
function createDocumentItem(file) {
    const item = document.createElement('div');
    item.className = 'document-item';
    
    const now = new Date();
    const timeString = now.toLocaleDateString('zh-TW') + ' ' + 
                      now.toLocaleTimeString('zh-TW', {hour: '2-digit', minute:'2-digit'});
    
    item.innerHTML = `
        <span>${file.name}</span>
        <span class="file-type">${getFileType(file.type)}</span>
        <span>${timeString}</span>
        <span class="status processing">處理中</span>
        <div class="actions">
            <button class="btn-small" onclick="editDocument(this)">編輯</button>
            <button class="btn-small danger" onclick="deleteDocument(this)">刪除</button>
        </div>
    `;
    
    return item;
}

// 獲取文件類型
function getFileType(mimeType) {
    if (mimeType.includes('pdf')) return '政策文件';
    if (mimeType.includes('word') || mimeType.includes('document')) return '規劃文件';
    if (mimeType.includes('excel') || mimeType.includes('sheet')) return '數據文件';
    return '其他文件';
}

// 模擬上傳過程
function simulateUploadProcess(fileItem) {
    setTimeout(() => {
        const statusElement = fileItem.querySelector('.status');
        statusElement.textContent = '已處理';
        statusElement.className = 'status processed';
        showNotification('文檔處理完成！', 'success');
    }, 3000 + Math.random() * 2000);
}

// 照片上傳處理
function handlePhotoUpload(files) {
    const photoGrid = document.querySelector('.photo-grid');
    const addPhotoBtn = photoGrid.querySelector('.add-photo');
    
    Array.from(files).forEach((file, index) => {
        if (photoGrid.children.length < 6) { // 最多6張照片
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            
            const img = document.createElement('img');
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'cover';
            
            // 創建預覽
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

// 語音上傳處理
function handleAudioUpload(files) {
    const audioList = document.querySelector('.audio-list');
    
    Array.from(files).forEach(file => {
        const audioItem = document.createElement('div');
        audioItem.className = 'audio-item';
        audioItem.innerHTML = `
            <span>${file.name}</span>
            <button class="play-btn" onclick="playAudioSample(this)">▶️</button>
        `;
        audioList.appendChild(audioItem);
    });
    
    showNotification('語音樣本上傳成功！', 'success');
}

// 播放語音測試
function playVoiceTest(btn) {
    btn.textContent = '播放中...';
    btn.disabled = true;
    
    // 模擬播放過程
    setTimeout(() => {
        btn.textContent = '試聽';
        btn.disabled = false;
    }, 3000);
    
    showNotification('播放語音測試...', 'info');
}

// 播放音頻樣本
function playAudioSample(btn) {
    const wasPlaying = btn.textContent === '⏸️';
    
    // 重置所有播放按鈕
    document.querySelectorAll('.play-btn').forEach(b => {
        b.textContent = '▶️';
    });
    
    if (!wasPlaying) {
        btn.textContent = '⏸️';
        setTimeout(() => {
            btn.textContent = '▶️';
        }, 3000);
    }
}

// 更新滑桿顯示值
function updateSliderValue(slider) {
    const valueSpan = slider.parentElement.querySelector('.value');
    let value = slider.value;
    
    // 根據滑桿類型格式化顯示值
    if (slider.min == '0.5' && slider.max == '2') {
        valueSpan.textContent = value + 'x';
    } else if (slider.min == '0' && slider.max == '100') {
        valueSpan.textContent = value + '%';
    } else {
        valueSpan.textContent = value;
    }
}

// 保存語音設定
function saveVoiceSettings() {
    const settings = {
        voiceType: document.querySelector('.voice-option.active')?.querySelector('h4')?.textContent,
        speed: document.querySelector('input[min="0.5"]').value,
        pitch: document.querySelector('input[min="-10"]').value,
        volume: document.querySelector('input[max="100"]').value
    };
    
    // 模擬保存過程
    const btn = document.querySelector('.save-settings');
    const originalText = btn.textContent;
    btn.textContent = '保存中...';
    btn.disabled = true;
    
    setTimeout(() => {
        btn.textContent = originalText;
        btn.disabled = false;
        showNotification('語音設定已保存！', 'success');
    }, 1500);
}

// 生成卡通形象
function generateAvatar() {
    const btn = document.querySelector('.media-btn.generate');
    const originalText = btn.textContent;
    btn.textContent = '生成中...';
    btn.disabled = true;
    
    const avatarPlaceholder = document.querySelector('.avatar-placeholder');
    avatarPlaceholder.textContent = '⏳';
    
    setTimeout(() => {
        avatarPlaceholder.textContent = '🤖';
        btn.textContent = originalText;
        btn.disabled = false;
        showNotification('卡通形象已更新！', 'success');
    }, 5000);
}

// 編輯文檔
function editDocument(btn) {
    const row = btn.closest('.document-item');
    const fileName = row.querySelector('span').textContent;
    showNotification(`編輯文檔：${fileName}`, 'info');
}

// 刪除文檔
function deleteDocument(btn) {
    if (confirm('確定要刪除此文檔嗎？')) {
        const row = btn.closest('.document-item');
        const fileName = row.querySelector('span').textContent;
        row.remove();
        showNotification(`已刪除文檔：${fileName}`, 'success');
    }
}

// 刷新分析數據
function refreshAnalytics() {
    // 模擬數據更新
    const stats = [
        { selector: '.stat-card:nth-child(1) h3', value: Math.floor(1200 + Math.random() * 100) },
        { selector: '.stat-card:nth-child(2) h3', value: Math.floor(800 + Math.random() * 100) },
        { selector: '.stat-card:nth-child(3) h3', value: (2.0 + Math.random() * 0.8).toFixed(1) + '秒' },
        { selector: '.stat-card:nth-child(4) h3', value: (4.0 + Math.random() * 0.5).toFixed(1) + '/5' }
    ];
    
    stats.forEach(stat => {
        const element = document.querySelector(stat.selector);
        if (element) {
            element.textContent = stat.value;
        }
    });
    
    // 更新圖表柱狀圖高度
    const bars = document.querySelectorAll('.bar');
    bars.forEach(bar => {
        const height = Math.floor(30 + Math.random() * 70) + '%';
        bar.style.height = height;
    });
    
    // 更新活動列表時間
    updateActivityTimes();
}

// 更新活動時間
function updateActivityTimes() {
    const now = new Date();
    const times = document.querySelectorAll('.activity-time');
    
    times.forEach((time, index) => {
        const minutes = now.getMinutes() - (index * 5);
        const hours = now.getHours();
        const displayTime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
        time.textContent = displayTime;
    });
}

// 登出處理
function handleLogout() {
    if (confirm('確定要登出嗎？')) {
        showNotification('正在登出...', 'info');
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1500);
    }
}

// 通知系統
function showNotification(message, type = 'info') {
    // 移除現有通知
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // 添加樣式
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        borderRadius: '8px',
        color: 'white',
        fontWeight: '500',
        zIndex: '9999',
        transform: 'translateX(400px)',
        transition: 'transform 0.3s ease'
    });
    
    // 設定顏色
    const colors = {
        success: '#27ae60',
        error: '#e74c3c',
        info: '#3498db',
        warning: '#f39c12'
    };
    notification.style.background = colors[type] || colors.info;
    
    document.body.appendChild(notification);
    
    // 滑入動畫
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // 自動移除
    setTimeout(() => {
        notification.style.transform = 'translateX(400px)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}