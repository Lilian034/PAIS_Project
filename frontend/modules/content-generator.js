/**
 * 文案生成模組
 * 負責文宣內容的AI生成功能
 */

import { $, escapeHtml } from '../utils/dom-helper.js';
import { showNotification } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// ==================== 模組狀態 ====================

let currentTaskId = null; // 當前任務 ID

// ==================== 公開函數 ====================

/**
 * 初始化文案生成功能
 * @export
 */
export function init() {
    console.log('✅ 文案生成已初始化');
}

/**
 * 生成文案
 * @export
 */
export async function generate() {
    const contentType = $('#contentType')?.value;
    const prompt = $('#genPrompt')?.value;

    if (!prompt?.trim()) {
        showNotification('請輸入生成指令', 'warning');
        return;
    }

    const outputDiv = $('#generatedContent');
    if (!outputDiv) {
        console.error('找不到輸出容器');
        return;
    }

    // 顯示加載狀態
    outputDiv.innerHTML = '<div class="placeholder-text"><p>生成中，請稍候...</p></div>';

    try {
        // 根據內容類型選擇風格
        const style = getStyleByType(contentType);

        // 調用 API
        const result = await APIClient.staff.generateContent(prompt, style, 'medium');

        if (result.success) {
            // 保存任務 ID
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

            showNotification('文案生成成功', 'success');
        } else {
            outputDiv.innerHTML = `
                <div class="placeholder-text" style="color: #dc2626;">
                    <p>❌ 生成失敗: ${escapeHtml(result.error)}</p>
                </div>
            `;
            showNotification(`生成失敗: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('❌ 生成錯誤:', error);
        outputDiv.innerHTML = `
            <div class="placeholder-text" style="color: #dc2626;">
                <p>❌ 生成過程中發生未預期錯誤</p>
            </div>
        `;
        showNotification('生成過程中發生錯誤', 'error');
    }
}

/**
 * 複製文案
 * @export
 */
export function copy() {
    const outputDiv = $('#generatedContent');
    const content = outputDiv?.innerText;

    if (!content || content.includes('生成中') || content.includes('請輸入')) {
        showNotification('沒有可複製的內容', 'warning');
        return;
    }

    navigator.clipboard.writeText(content).then(() => {
        showNotification('已複製到剪貼簿', 'success');
    }).catch((error) => {
        console.error('❌ 複製失敗:', error);
        showNotification('複製失敗', 'error');
    });
}

/**
 * 儲存文案為 TXT 檔案
 * @export
 */
export function save() {
    const outputDiv = $('#generatedContent');
    const content = outputDiv?.innerText;

    if (!content || content.includes('生成中') || content.includes('請輸入')) {
        showNotification('沒有可儲存的內容', 'warning');
        return;
    }

    try {
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');

        // 生成檔案名稱（包含時間戳記）
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        a.href = url;
        a.download = `文宣內容_${timestamp}.txt`;

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        URL.revokeObjectURL(url);

        showNotification('檔案已儲存', 'success');
    } catch (error) {
        console.error('❌ 儲存失敗:', error);
        showNotification('儲存失敗', 'error');
    }
}

/**
 * 獲取當前任務 ID
 * @returns {string|null}
 * @export
 */
export function getCurrentTaskId() {
    return currentTaskId;
}

// ==================== 私有函數 ====================

/**
 * 根據內容類型獲取風格
 * @param {string} contentType - 內容類型
 * @returns {string}
 */
function getStyleByType(contentType) {
    const styleMap = {
        'press': 'formal',      // 新聞稿
        'speech': 'formal',     // 演講稿
        'facebook': 'casual',   // Facebook
        'instagram': 'casual',  // Instagram
        'poster': 'concise'     // 海報
    };

    return styleMap[contentType] || 'formal';
}

// ==================== 全局導出（供 HTML 內聯事件使用） ====================

if (typeof window !== 'undefined') {
    window.contentGenerator = {
        generate,
        copy,
        save
    };
}
