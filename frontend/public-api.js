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

// ==================== 訪客計數器 API ====================

/**
 * 增加訪客計數
 */
async function incrementVisitorCount() {
    try {
        const response = await fetch(`${PUBLIC_API_BASE_URL}/visitor/increment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('增加訪客計數失敗');
        }

        return await response.json();
    } catch (error) {
        console.error('增加訪客計數失敗:', error);
        throw error;
    }
}

/**
 * 獲取訪客統計
 */
async function getVisitorStats(month = null) {
    try {
        const url = month
            ? `${PUBLIC_API_BASE_URL}/visitor/stats?month=${month}`
            : `${PUBLIC_API_BASE_URL}/visitor/stats`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error('獲取訪客統計失敗');
        }

        return await response.json();
    } catch (error) {
        console.error('獲取訪客統計失敗:', error);
        throw error;
    }
}
