/**
 * 短影音生成模組
 * 負責影片生成、播放和下載功能
 */

import { showNotification } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// ==================== 模組狀態 ====================

let currentVideoTaskId = null; // 當前影片任務 ID
let generatedVideoUrl = null; // 生成的影片 URL

// 外部依賴變數（從其他模組傳入）
let uploadedPhotoPaths = null;
let uploadedAudioPath = null; // 上傳的音頻路徑
let currentTaskId = null;
let currentVoiceTaskId = null;

// ==================== 公開函數 ====================

/**
 * 初始化短影音生成功能
 * @export
 */
export function init() {
    const generateBtn = document.getElementById('btnGenVideo');
    const saveBtn = document.getElementById('btnSaveVideo');

    // 綁定生成按鈕
    if (generateBtn) {
        generateBtn.addEventListener('click', handleVideoGenerate);
    }

    // 綁定保存按鈕
    if (saveBtn) {
        saveBtn.addEventListener('click', saveVideoFile);
    }

    console.log('✅ 短影音生成已初始化');
}

/**
 * 生成影片
 * @export
 */
export async function generate() {
    await handleVideoGenerate();
}

/**
 * 保存影片文件
 * @export
 */
export function save() {
    saveVideoFile();
}

/**
 * 獲取當前影片任務 ID
 * @returns {string|null}
 * @export
 */
export function getCurrentTaskId() {
    return currentVideoTaskId;
}

/**
 * 獲取生成的影片 URL
 * @returns {string|null}
 * @export
 */
export function getVideoUrl() {
    return generatedVideoUrl;
}

/**
 * 設置上傳的照片路徑（供外部調用）
 * @param {Array<string>} paths - 照片路徑數組
 * @export
 */
export function setUploadedPhotoPaths(paths) {
    uploadedPhotoPaths = paths;
}

/**
 * 設置上傳的音頻路徑（供外部調用）
 * @param {string} path - 音頻路徑
 * @export
 */
export function setUploadedAudioPath(path) {
    uploadedAudioPath = path;
}

/**
 * 設置當前任務 ID（供其他模組調用）
 * @param {string} taskId - 任務 ID
 * @param {string} type - 任務類型 ('content' 或 'voice')
 * @export
 */
export function setCurrentTaskId(taskId, type = 'content') {
    if (type === 'content') {
        currentTaskId = taskId;
    } else if (type === 'voice') {
        currentVoiceTaskId = taskId;
    }
}

// ==================== 私有函數 ====================

/**
 * 處理影片生成（HeyGen Avatar Video）
 */
async function handleVideoGenerate() {
    // 檢查是否有上傳的照片
    if (!uploadedPhotoPaths || uploadedPhotoPaths.length === 0) {
        showNotification('請先上傳照片', 'warning');
        return;
    }

    // 檢查是否有音頻（上傳的或生成的）
    let taskId = currentTaskId || currentVoiceTaskId;
    if (!uploadedAudioPath && !taskId) {
        showNotification('請先上傳音頻或生成語音！', 'warning');
        return;
    }

    try {
        showNotification('正在生成 Avatar Video，預計需要 5-10 分鐘，請耐心等候...', 'info');

        // 使用第一張上傳的照片
        const imagePath = uploadedPhotoPaths[0];

        // 設置任務ID（如果有的話）
        currentVideoTaskId = taskId || `upload_${Date.now()}`;

        let videoResult;

        // 如果有上傳的音頻，直接使用上傳的音頻
        if (uploadedAudioPath) {
            console.log('🎵 使用上傳的音頻:', uploadedAudioPath);
            videoResult = await APIClient.staff.generateVideoWithUploadedAudio(uploadedAudioPath, imagePath);
        } else {
            // 否則使用任務ID（從語音生成取得音頻）
            console.log('🎵 使用任務語音:', taskId);
            videoResult = await APIClient.staff.generateVideo(taskId, imagePath);
        }

        if (!videoResult.success) {
            showNotification(`Avatar Video 生成失敗: ${videoResult.error}`, 'error');
            return;
        }

        // 成功生成影片
        const videoPath = videoResult.file_path;
        generatedVideoUrl = `/${videoPath}`;

        showNotification('Avatar Video 生成完成！', 'success');

        // 顯示影片預覽
        displayVideoPlayer(generatedVideoUrl);

    } catch (error) {
        console.error('❌ Avatar Video 生成錯誤:', error);
        showNotification(`生成過程中發生錯誤: ${error.message}`, 'error');
    }
}

/**
 * 顯示影片播放器
 * @param {string} videoUrl - 影片 URL
 */
function displayVideoPlayer(videoUrl) {
    const avatarPreview = document.querySelector('.generated-avatar');

    if (!avatarPreview) return;

    // 清空原有內容
    avatarPreview.innerHTML = '';

    // 創建影片元素
    const video = document.createElement('video');
    video.controls = true;
    video.autoplay = false;
    video.style.cssText = `
        width: 100%;
        height: 100%;
        object-fit: contain;
        background: #000;
    `;

    const source = document.createElement('source');
    source.src = videoUrl;
    source.type = 'video/mp4';

    video.appendChild(source);
    avatarPreview.appendChild(video);

    // 添加任務ID提示
    const taskInfo = document.createElement('p');
    taskInfo.style.cssText = `
        margin-top: 0.5rem;
        font-size: 0.875rem;
        color: #6b7280;
        text-align: center;
    `;
    taskInfo.textContent = `任務ID: ${currentVideoTaskId}`;

    const mediaCard = avatarPreview.closest('.media-card');
    if (mediaCard) {
        const existingInfo = mediaCard.querySelector('.video-task-info');
        if (existingInfo) {
            existingInfo.remove();
        }
        taskInfo.className = 'video-task-info';
        const previewDiv = mediaCard.querySelector('.media-preview');
        if (previewDiv) {
            previewDiv.appendChild(taskInfo);
        }
    }
}

/**
 * 保存影片文件
 */
function saveVideoFile() {
    if (!generatedVideoUrl) {
        showNotification('請先生成影片', 'warning');
        return;
    }

    try {
        // 創建下載鏈接
        const a = document.createElement('a');
        a.href = generatedVideoUrl;
        a.download = `video_${currentVideoTaskId || Date.now()}.mp4`;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        showNotification('影片下載已開始', 'success');
    } catch (error) {
        console.error('❌ 保存影片錯誤:', error);
        showNotification(`保存影片失敗: ${error.message}`, 'error');
    }
}

// ==================== 全局導出（供 HTML 內聯事件使用） ====================

if (typeof window !== 'undefined') {
    window.videoGenerator = {
        generate,
        save
    };
}
