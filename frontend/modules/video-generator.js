/**
 * 短影音生成模組
 * 負責影片生成、播放和下載功能
 */

import { showNotification } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// ==================== 模組狀態 ====================

let currentVideoTaskId = null; // 當前影片任務 ID
let generatedVideoUrl = null; // 生成的影片 URL

// 外部依賴變數
let uploadedPhotoPaths = null;
let uploadedAudioPath = null;
let currentTaskId = null;
let currentVoiceTaskId = null;

// ==================== 公開函數 ====================

export function init() {
    const generateBtn = document.getElementById('btnGenVideo');
    const saveBtn = document.getElementById('btnSaveVideo');

    if (generateBtn) {
        generateBtn.addEventListener('click', handleVideoGenerate);
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', saveVideoFile);
    }

    console.log('✅ 短影音生成已初始化');
}

export async function generate() {
    await handleVideoGenerate();
}

export function save() {
    saveVideoFile();
}

export function getCurrentTaskId() {
    return currentVideoTaskId;
}

export function getVideoUrl() {
    return generatedVideoUrl;
}

export function setUploadedPhotoPaths(paths) {
    uploadedPhotoPaths = paths;
}

export function setUploadedAudioPath(path) {
    uploadedAudioPath = path;
}

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
    if (!uploadedPhotoPaths || uploadedPhotoPaths.length === 0) {
        showNotification('請先上傳照片', 'warning');
        return;
    }

    let taskId = currentTaskId || currentVoiceTaskId;
    if (!uploadedAudioPath && !taskId) {
        showNotification('請先上傳音頻或生成語音！', 'warning');
        return;
    }

    try {
        showNotification('正在請求生成 Avatar Video...', 'info');

        const imagePath = uploadedPhotoPaths[0];
        
        let videoResult;

        // 發送請求 (現在後端會秒回 "處理中")
        if (uploadedAudioPath) {
            videoResult = await APIClient.staff.generateVideoWithUploadedAudio(uploadedAudioPath, imagePath);
        } else {
            videoResult = await APIClient.staff.generateVideo(taskId, imagePath);
        }

        if (!videoResult.success) {
            showNotification(`請求失敗: ${videoResult.error}`, 'error');
            return;
        }

        // 取得 Task ID，並開始輪詢
        currentVideoTaskId = videoResult.task_id;
        showNotification('請求已送出！正在後台生成影片，請稍候...', 'success');
        
        // 更新介面顯示 "處理中"
        const avatarPreview = document.querySelector('.generated-avatar');
        if (avatarPreview) {
            avatarPreview.innerHTML = `
                <div style="text-align:center; padding: 20px;">
                    <div class="loading-spinner" style="font-size:24px; margin-bottom:10px;">⏳</div>
                    <p style="color:#666; font-size:14px;">影片生成中...<br>請勿關閉視窗</p>
                </div>
            `;
        }

        // === 開始輪詢狀態 (Polling) ===
        pollVideoStatus(currentVideoTaskId);

    } catch (error) {
        console.error('❌ Avatar Video 生成錯誤:', error);
        showNotification(`生成請求錯誤: ${error.message}`, 'error');
    }
}

/**
 * 輪詢影片狀態
 */
async function pollVideoStatus(taskId) {
    let attempts = 0;
    const maxAttempts = 120; // 最多查 10 分鐘 (120 * 5s)

    const check = async () => {
        attempts++;
        if (attempts > maxAttempts) {
            showNotification('等待逾時，請稍後至列表查看', 'warning');
            return;
        }

        try {
            // 呼叫 API 查詢狀態
            const statusRes = await APIClient.staff.getMediaStatus(taskId);
            
            // 尋找類型為 avatar_video 的記錄
            const record = statusRes.media_records?.find(r => r.media_type === 'avatar_video' || r.media_type === 'video');

            if (record && record.status === 'completed' && record.file_path) {
                // 成功！顯示影片
                generatedVideoUrl = `/${record.file_path}`;
                displayVideoPlayer(generatedVideoUrl);
                showNotification('Avatar Video 生成完成！', 'success');
            } else if (record && record.status === 'failed') {
                // 失敗
                showNotification('影片生成失敗，請檢查後台日誌', 'error');
                const avatarPreview = document.querySelector('.generated-avatar');
                if (avatarPreview) avatarPreview.innerHTML = '<div class="avatar-placeholder" style="color:red">❌ 生成失敗</div>';
            } else {
                // 還在跑，5秒後再問一次
                console.log(`[Polling] 影片生成中... (${attempts}/${maxAttempts})`);
                setTimeout(check, 5000);
            }
        } catch (e) {
            console.warn('輪詢狀態失敗:', e);
            setTimeout(check, 5000); // 失敗也重試
        }
    };

    // 開始第一次檢查
    check();
}

/**
 * 顯示影片播放器
 */
function displayVideoPlayer(videoUrl) {
    const avatarPreview = document.querySelector('.generated-avatar');

    if (!avatarPreview) return;

    avatarPreview.innerHTML = '';

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
        if (existingInfo) existingInfo.remove();
        taskInfo.className = 'video-task-info';
        mediaCard.querySelector('.media-preview').appendChild(taskInfo);
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

if (typeof window !== 'undefined') {
    window.videoGenerator = {
        generate,
        save,
        setUploadedPhotoPaths,
        setUploadedAudioPath,
        setCurrentTaskId,
        getCurrentTaskId,
        getVideoUrl
    };
}