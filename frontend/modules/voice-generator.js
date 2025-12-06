/**
 * 語音生成模組
 * 負責語音生成、播放和下載功能
 */

import { $, escapeHtml } from '../utils/dom-helper.js';
import { showNotification } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// ==================== 模組狀態 ====================

let currentVoiceTaskId = null; // 當前語音任務 ID
let generatedAudioUrl = null; // 生成的音頻 URL

// ==================== 公開函數 ====================

/**
 * 初始化語音生成功能
 * @export
 */
export function init() {
    const generateBtn = $('#btnGoGenerate');
    const saveBtn = $('#btnSaveAudio');
    const btnVoiceUpload = $('#btnVoiceUpload');

    // 綁定生成按鈕
    if (generateBtn) {
        generateBtn.addEventListener('click', handleVoiceGenerate);
    }

    // 綁定保存按鈕
    if (saveBtn) {
        saveBtn.addEventListener('click', saveAudioFile);
    }

    // 綁定語音選項
    const voiceOptions = document.querySelectorAll('.voice-option');
    voiceOptions.forEach(option => {
        option.addEventListener('click', () => {
            voiceOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
        });
    });

    // 綁定「＋新增音檔」按鈕
    if (btnVoiceUpload) {
        btnVoiceUpload.addEventListener('click', openAudioAddModal);
    }

    // 初始化新增音檔彈窗
    initAudioAddModal();

    console.log('✅ 語音生成已初始化');
}

/**
 * 生成語音
 * @export
 */
export async function generate() {
    await handleVoiceGenerate();
}

/**
 * 保存音頻文件
 * @export
 */
export function save() {
    saveAudioFile();
}

/**
 * 獲取當前語音任務 ID
 * @returns {string|null}
 * @export
 */
export function getCurrentTaskId() {
    return currentVoiceTaskId;
}

/**
 * 獲取生成的音頻 URL
 * @returns {string|null}
 * @export
 */
export function getAudioUrl() {
    return generatedAudioUrl;
}

// ==================== 私有函數 ====================

/**
 * 處理語音生成
 */
async function handleVoiceGenerate() {
    const voicePrompt = $('#voicePrompt');
    const text = voicePrompt?.value?.trim();

    if (!text) {
        showNotification('請輸入要生成語音的內容', 'warning');
        return;
    }

    try {
        showNotification('正在生成語音，請稍候...', 'info');

        // 步驟 1: 先創建文案任務（因為語音生成需要 task_id）
        // 使用 'speech' 類型，因為語音適合口語化的演講風格
        const contentResult = await APIClient.staff.generateContent(text, 'speech', 'short');

        if (!contentResult.success) {
            showNotification(`創建任務失敗: ${contentResult.error}`, 'error');
            return;
        }

        const taskId = contentResult.task_id;
        currentVoiceTaskId = taskId;

        // 步驟 2: 審核通過任務（語音生成需要已審核的任務）
        const approveResult = await APIClient.staff.approveTask(taskId);

        if (!approveResult.success) {
            showNotification(`審核任務失敗: ${approveResult.error}`, 'error');
            return;
        }

        // 步驟 3: 生成語音
        const voiceResult = await APIClient.staff.generateVoice(taskId);

        if (!voiceResult.success) {
            showNotification(`語音生成失敗: ${voiceResult.error}`, 'error');
            return;
        }

        // 成功生成語音
        const audioPath = voiceResult.file_path;
        generatedAudioUrl = `/${audioPath}`; // 構建音頻URL

        showNotification(`語音生成成功！任務ID: ${taskId}`, 'success');

        // 顯示音頻播放器
        displayAudioPlayer(generatedAudioUrl);

    } catch (error) {
        console.error('❌ 語音生成錯誤:', error);
        showNotification(`語音生成過程中發生錯誤: ${error.message}`, 'error');
    }
}

/**
 * 顯示音頻播放器
 * @param {string} audioUrl - 音頻 URL
 */
function displayAudioPlayer(audioUrl) {
    const voiceSection = document.querySelector('#voice .voice-settings');

    // 移除舊的播放器
    const oldPlayer = voiceSection?.querySelector('.audio-player-container');
    if (oldPlayer) {
        oldPlayer.remove();
    }

    // 創建新的播放器
    const playerDiv = document.createElement('div');
    playerDiv.className = 'audio-player-container';
    playerDiv.style.cssText = `
        margin-top: 1rem;
        padding: 1rem;
        background: #f0f9ff;
        border-radius: 8px;
        border: 1px solid #bfdbfe;
    `;

    playerDiv.innerHTML = `
        <h4 style="margin: 0 0 0.5rem 0; color: #0369a1;">🎵 生成的語音</h4>
        <audio controls style="width: 100%; margin-top: 0.5rem;">
            <source src="${audioUrl}" type="audio/mpeg">
            您的瀏覽器不支援音頻播放。
        </audio>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.875rem; color: #6b7280;">
            任務ID: ${currentVoiceTaskId}
        </p>
    `;

    voiceSection?.appendChild(playerDiv);
}

/**
 * 初始化新增音檔彈窗
 */
function initAudioAddModal() {
    const addChooseBtn = $('#addChooseBtn');
    const addAudioInput = $('#addAudioInput');
    const addBtnClose = $('#addBtnClose');
    const addBtnCreate = $('#addBtnCreate');

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
            const emotion = $('#addEmotion')?.value.trim();
            const source = $('#addSource')?.value.trim();

            if (!file) {
                showNotification('請選擇音檔檔案', 'warning');
                return;
            }

            if (!emotion) {
                showNotification('請輸入情緒', 'warning');
                return;
            }

            // 這裡可以加入實際的新增邏輯
            showNotification(`已新增音檔: ${file.name}`, 'success');
            closeAudioAddModal();
        });
    }
}

/**
 * 打開新增音檔彈窗
 */
function openAudioAddModal() {
    const modal = $('#audioAddModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
    }
    document.body.classList.add('no-scroll');
}

/**
 * 關閉新增音檔彈窗
 */
function closeAudioAddModal() {
    const modal = $('#audioAddModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
    }
    document.body.classList.remove('no-scroll');

    // 重置表單
    const addChooseBtn = $('#addChooseBtn');
    const addAudioInput = $('#addAudioInput');
    const addEmotion = $('#addEmotion');
    const addSource = $('#addSource');

    if (addChooseBtn) addChooseBtn.innerHTML = '＋ 選擇檔案';
    if (addAudioInput) addAudioInput.value = '';
    if (addEmotion) addEmotion.value = '';
    if (addSource) addSource.value = '';
}

/**
 * 保存音頻文件
 */
function saveAudioFile() {
    if (!generatedAudioUrl) {
        showNotification('請先生成語音', 'warning');
        return;
    }

    try {
        // 創建下載鏈接
        const a = document.createElement('a');
        a.href = generatedAudioUrl;
        a.download = `voice_${currentVoiceTaskId || Date.now()}.mp3`;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        showNotification('音檔下載已開始', 'success');
    } catch (error) {
        console.error('❌ 保存音檔錯誤:', error);
        showNotification(`保存音檔失敗: ${error.message}`, 'error');
    }
}

// ==================== 全局導出（供 HTML 內聯事件使用） ====================

if (typeof window !== 'undefined') {
    window.voiceGenerator = {
        generate,
        save,
        openAudioAddModal,
        closeAudioAddModal
    };
}
