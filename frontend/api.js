// ==================== PAIS 前端 API 連接 ====================
// 給團隊後台 (admin.html) 使用

const API_BASE_URL = '/api';

// ==================== 團隊後台 API (需要密碼) ====================

/**
 * 生成文案 (團隊專用)
 */
async function generateContent(topic, style = "正式", length = "中", adminPassword) {
    try {
        const response = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminPassword}`
            },
            body: JSON.stringify({
                topic: topic,
                style: style,
                length: length
            })
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('密碼錯誤');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return {
            success: true,
            content: data.content,
            filePath: data.file_path,
            sources: data.sources
        };
    } catch (error) {
        console.error('生成文案失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 上傳單個檔案
 */
async function uploadFile(file, adminPassword) {
    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminPassword}`
            },
            body: formData
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('密碼錯誤');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return {
            success: true,
            message: data.message,
            filename: data.filename,
            chunks: data.chunks
        };
    } catch (error) {
        console.error('上傳檔案失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 批量處理知識庫
 */
async function ingestDocuments(folderPath = "documents", adminPassword) {
    try {
        const response = await fetch(`${API_BASE_URL}/ingest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminPassword}`
            },
            body: JSON.stringify({
                folder_path: folderPath
            })
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('密碼錯誤');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return {
            success: true,
            message: data.message,
            filesProcessed: data.files_processed,
            chunksCreated: data.chunks_created
        };
    } catch (error) {
        console.error('處理知識庫失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 取得系統統計
 */
async function getStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('取得統計失敗:', error);
        return null;
    }
}

/**
 * 健康檢查
 */
async function healthCheck() {
    try {
        const response = await fetch('/health');
        return await response.json();
    } catch (error) {
        console.error('健康檢查失敗:', error);
        return { status: 'error' };
    }
}