// ==================== 民眾端 API ====================
// 專門給 index.html 使用的 API 函數

const PUBLIC_API_BASE_URL = '/api';

// ==================== 民眾問答 API ====================

/**
 * 發送聊天訊息給 AI
 */
async function sendChatMessage(message, sessionId, useAgent = true) {
    try {
        const response = await fetch(`${PUBLIC_API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                use_agent: useAgent,
                role: 'public'  // 民眾模式
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('發送聊天訊息失敗:', error);
        throw error;
    }
}

/**
 * 健康檢查
 */
async function checkPublicHealth() {
    try {
        const response = await fetch(`${PUBLIC_API_BASE_URL}/health`);
        return await response.json();
    } catch (error) {
        console.error('健康檢查失敗:', error);
        return { status: 'error' };
    }
}
