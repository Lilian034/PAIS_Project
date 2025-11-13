// ==================== PAIS 前端 API 連接 ====================
// 給團隊後台 (admin.html) 使用

const API_BASE_URL = '/api';
const STAFF_API_URL = '/api/staff';

// 從環境變數或 localStorage 獲取密碼
let STAFF_PASSWORD = 'admin123456'; // 默認密碼，建議從登入後存儲

/**
 * 設置管理員密碼
 */
function setStaffPassword(password) {
    STAFF_PASSWORD = password;
    localStorage.setItem('staff_password', password);
}

/**
 * 獲取管理員密碼
 */
function getStaffPassword() {
    const stored = localStorage.getItem('staff_password');
    return stored || STAFF_PASSWORD;
}

// ==================== 幕僚系統 API ====================

/**
 * 生成文案 (幕僚專用)
 */
async function generateStaffContent(topic, style = "formal", length = "medium") {
    try {
        const response = await fetch(`${STAFF_API_URL}/content/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getStaffPassword()}`
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
            task_id: data.task_id,
            content: data.content,
            message: data.message
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
 * 校稿 - 使用聊天 API
 * @param {string} text - 用戶輸入的文本
 * @param {string|null} sessionId - 會話 ID（用於對話記憶）
 * @param {boolean} isFirstMessage - 是否為首次對話
 */
async function proofreadContent(text, sessionId = null, isFirstMessage = false) {
    try {
        // 只在首次對話時添加校稿說明，後續對話直接發送用戶訊息以保持對話連貫性
        const message = isFirstMessage
            ? `請幫我校稿以下內容，檢查語法、用詞和事實正確性：\n\n${text}`
            : text;

        console.log('🔍 proofreadContent 調用參數:', {
            sessionId,
            isFirstMessage,
            messageLength: message.length
        });

        const requestBody = {
            message: message,
            session_id: sessionId
        };
        console.log('📤 發送到後端:', requestBody);

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('📥 後端返回:', data);

        return {
            success: true,
            response: data.reply,  // 後端返回的是 'reply' 而非 'response'
            session_id: data.session_id,
            sources: data.sources
        };
    } catch (error) {
        console.error('校稿失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 取得任務列表
 */
async function getTasks(limit = 50) {
    try {
        const response = await fetch(`${STAFF_API_URL}/content/tasks?limit=${limit}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getStaffPassword()}`
            }
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
            tasks: data.tasks,
            total: data.total
        };
    } catch (error) {
        console.error('取得任務列表失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 取得單一任務
 */
async function getTask(taskId) {
    try {
        const response = await fetch(`${STAFF_API_URL}/content/task/${taskId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getStaffPassword()}`
            }
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
            task: data.task
        };
    } catch (error) {
        console.error('取得任務失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 更新任務內容
 */
async function updateTask(taskId, content, editor = 'admin') {
    try {
        const response = await fetch(`${STAFF_API_URL}/content/task/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getStaffPassword()}`
            },
            body: JSON.stringify({
                content: content,
                editor: editor
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
            message: data.message
        };
    } catch (error) {
        console.error('更新任務失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 審核通過任務
 */
async function approveTask(taskId) {
    try {
        const response = await fetch(`${STAFF_API_URL}/content/task/${taskId}/approve`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getStaffPassword()}`
            }
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
            message: data.message
        };
    } catch (error) {
        console.error('審核任務失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 生成語音
 */
async function generateVoice(taskId) {
    try {
        const response = await fetch(`${STAFF_API_URL}/media/voice/${taskId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getStaffPassword()}`
            }
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
            task_id: data.task_id,
            media_type: data.media_type,
            file_path: data.file_path,
            message: data.message
        };
    } catch (error) {
        console.error('生成語音失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 生成影片
 */
async function generateVideo(taskId, imagePath, prompt = null) {
    try {
        const response = await fetch(`${STAFF_API_URL}/media/video/${taskId}?image_path=${encodeURIComponent(imagePath)}${prompt ? '&prompt=' + encodeURIComponent(prompt) : ''}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getStaffPassword()}`
            }
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
            task_id: data.task_id,
            media_type: data.media_type,
            file_path: data.file_path,
            message: data.message
        };
    } catch (error) {
        console.error('生成影片失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// ==================== 知識庫管理 API ====================

/**
 * 上傳單個檔案到知識庫
 * @param {File} file - 要上傳的文件
 * @param {string} folder - 目標資料夾路徑（可選）
 */
async function uploadFile(file, folder = '') {
    try {
        const formData = new FormData();
        formData.append('file', file);
        if (folder) {
            formData.append('folder', folder);
        }

        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getStaffPassword()}`
            },
            body: formData
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('密碼錯誤');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // 檢查是否有錯誤字段（部分失敗的情況）
        if (data.error) {
            return {
                success: false,
                message: data.message,
                error: data.error,
                filename: data.filename,
                chunks: data.chunks || 0
            };
        }

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
async function ingestDocuments(folderPath = "documents") {
    try {
        const response = await fetch(`${API_BASE_URL}/ingest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getStaffPassword()}`
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
 * 列出知識庫中的文檔
 */
async function listDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getStaffPassword()}`
            }
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
            documents: data.documents || [],
            total: data.total || 0
        };
    } catch (error) {
        console.error('取得文檔列表失敗:', error);
        return {
            success: false,
            error: error.message,
            documents: [],
            total: 0
        };
    }
}

/**
 * 刪除知識庫中的文檔
 */
async function deleteDocument(filePath) {
    try {
        const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filePath)}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${getStaffPassword()}`
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('密碼錯誤');
            }
            if (response.status === 404) {
                throw new Error('文件不存在');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return {
            success: true,
            message: data.message,
            filename: data.filename
        };
    } catch (error) {
        console.error('刪除文檔失敗:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// ==================== 系統監控 API ====================

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
 * 健康檢查 - 公眾 API
 */
async function healthCheck() {
    try {
        const response = await fetch('/api/health');
        return await response.json();
    } catch (error) {
        console.error('健康檢查失敗:', error);
        return { status: 'error' };
    }
}

/**
 * 健康檢查 - 幕僚 API
 */
async function staffHealthCheck() {
    try {
        const response = await fetch('/api/staff-health');
        return await response.json();
    } catch (error) {
        console.error('幕僚系統健康檢查失敗:', error);
        return { status: 'error' };
    }
}