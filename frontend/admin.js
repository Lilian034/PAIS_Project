/**
 * 幕僚系統主入口文件
 * 負責導入和初始化所有功能模組
 */

// ==================== 導入模組 ====================

import * as TabManager from './modules/tab-manager.js';
import * as DocumentManager from './modules/document-manager.js';
import * as Proofreading from './modules/proofreading.js';
import * as ContentGenerator from './modules/content-generator.js';
import * as VoiceGenerator from './modules/voice-generator.js';
import * as VideoGenerator from './modules/video-generator.js';
import * as DataMonitor from './modules/data-monitor.js';
import APIClient from './api/api-client.js';
import { showNotification } from './utils/notification.js';

// ==================== 全局變量 ====================

let uploadedPhotoPaths = []; // 保存已上傳的照片路徑（供視頻生成使用）
let uploadedAudioPath = null; // 保存已上傳的音頻路徑（供視頻生成使用）

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    // 初始化所有功能模組
    TabManager.init();
    DocumentManager.init();
    initMediaUpload();
    Proofreading.init();
    ContentGenerator.init();
    VoiceGenerator.init();
    VideoGenerator.init();
    DataMonitor.init();
    initLogout();

    // 測試 API 連接
    checkAPIConnection();

    console.log('✅ 幕僚系統已啟動');
});

/**
 * 檢查 API 連接
 */
async function checkAPIConnection() {
    try {
        const [publicHealth, staffHealth] = await Promise.all([
            APIClient.system.healthCheck(),
            APIClient.system.staffHealthCheck()
        ]);

        const allHealthy = publicHealth?.status === 'healthy' && staffHealth?.status === 'healthy';

        if (allHealthy) {
            console.log('✅ API 服務運行正常');
        } else {
            console.warn('⚠️ 部分 API 服務可能未啟動');
        }
    } catch (error) {
        console.error('❌ API 連接測試失敗:', error);
    }
}

// ==================== 媒體上傳 ====================

/**
 * 初始化媒體上傳功能
 */
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

    console.log('✅ 媒體上傳已初始化');
}

/**
 * 處理照片上傳
 */
async function handlePhotoUpload(files) {
    const photoGrid = document.querySelector('.photo-grid');
    const addPhotoBtn = photoGrid?.querySelector('.add-photo');
    if (!photoGrid || !addPhotoBtn) return;

    showNotification('正在上傳照片...', 'info');

    for (const file of Array.from(files)) {
        if (photoGrid.children.length >= 6) {
            showNotification('最多只能上傳5張照片', 'warning');
            break;
        }

        try {
            // 上傳照片到服務器（使用 images 資料夾）
            const uploadResult = await APIClient.documents.upload(file, 'images');

            if (!uploadResult.success) {
                showNotification(`上傳 ${file.name} 失敗: ${uploadResult.error}`, 'error');
                continue;
            }

            // 保存上傳的照片路徑
            const photoPath = uploadResult.file_path || `documents/images/${file.name}`;
            uploadedPhotoPaths.push(photoPath);

            // 通知 VideoGenerator 模組
            VideoGenerator.setUploadedPhotoPaths(uploadedPhotoPaths);

            // 在前端顯示照片
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';
            photoItem.dataset.path = photoPath;

            const img = document.createElement('img');
            img.src = `/${photoPath}`;
            img.alt = file.name;
            img.style.cssText = `
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: 8px;
            `;
            photoItem.appendChild(img);

            // 添加刪除按鈕
            const deleteBtn = document.createElement('button');
            deleteBtn.textContent = '×';
            deleteBtn.style.cssText = `
                position: absolute;
                top: 4px;
                right: 4px;
                background: rgba(0, 0, 0, 0.6);
                color: white;
                border: none;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
            `;
            deleteBtn.onclick = () => {
                photoItem.remove();
                uploadedPhotoPaths = uploadedPhotoPaths.filter(p => p !== photoPath);
                VideoGenerator.setUploadedPhotoPaths(uploadedPhotoPaths);
            };

            photoItem.style.position = 'relative';
            photoItem.appendChild(deleteBtn);

            photoGrid.insertBefore(photoItem, addPhotoBtn);

        } catch (error) {
            console.error('❌ 上傳照片錯誤:', error);
            showNotification(`上傳 ${file.name} 失敗`, 'error');
        }
    }

    showNotification('照片上傳完成！', 'success');
}

/**
 * 處理音頻上傳
 */
async function handleAudioUpload(files) {
    const audioBox = document.querySelector('#media .audio-single');
    if (!audioBox || !files || !files.length) return;

    const addBtn = audioBox.querySelector('.add-audio');
    const file = files[0];

    try {
        showNotification('正在上傳音頻...', 'info');

        // 上傳音頻到服務器（使用 audio 資料夾）
        const uploadResult = await APIClient.documents.upload(file, 'audio');

        if (!uploadResult.success) {
            showNotification(`上傳音頻失敗: ${uploadResult.error}`, 'error');
            return;
        }

        // 保存上傳的音頻路徑
        const audioPath = uploadResult.file_path || `documents/audio/${file.name}`;
        uploadedAudioPath = audioPath;

        // 通知 VideoGenerator 模組
        VideoGenerator.setUploadedAudioPath(audioPath);

        showNotification('音頻上傳成功！', 'success');

        // 前端顯示預覽
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

    } catch (error) {
        console.error('❌ 上傳音頻錯誤:', error);
        showNotification('上傳音頻失敗', 'error');
    }
}

// ==================== 登出功能 ====================

/**
 * 初始化登出功能
 */
function initLogout() {
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('確定要登出嗎？')) {
                showNotification('已登出', 'success');
                // 可以在這裡添加實際的登出邏輯
                // 例如：清除 localStorage, 重定向到登入頁等
            }
        });
    }

    console.log('✅ 登出功能已初始化');
}

// ==================== 模組間通信 ====================

/**
 * 當內容生成完成時，通知其他模組
 */
window.addEventListener('content-generated', (event) => {
    const { taskId } = event.detail;
    if (taskId) {
        VideoGenerator.setCurrentTaskId(taskId, 'content');
    }
});

/**
 * 當語音生成完成時，通知其他模組
 */
window.addEventListener('voice-generated', (event) => {
    const { taskId } = event.detail;
    if (taskId) {
        VideoGenerator.setCurrentTaskId(taskId, 'voice');
    }
});
