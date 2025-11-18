// ==================== 幕僚端 API ====================
// 專門給 admin.html 使用的 API 函數

const ADMIN_API_BASE_URL = '/api';
const STAFF_API_URL = '/api/staff';
let ADMIN_STAFF_PASSWORD = 'admin123';
const ADMIN_PASSWORD = 'admin123456';  // 用於知識庫管理

function setStaffPassword(password) {
    ADMIN_STAFF_PASSWORD = password;
    localStorage.setItem('staff_password', password);
}

function getStaffPassword() {
    return localStorage.getItem('staff_password') || ADMIN_STAFF_PASSWORD;
}

// ==================== 統一 HTTP 請求處理 ====================

async function adminApiRequest(url, options = {}) {
    const { method = 'GET', body, requireAuth = false, requireAdminAuth = false, contentType = 'application/json' } = options;

    const headers = {};
    if (contentType) headers['Content-Type'] = contentType;
    if (requireAdminAuth) headers['Authorization'] = `Bearer ${ADMIN_PASSWORD}`;
    else if (requireAuth) headers['Authorization'] = `Bearer ${getStaffPassword()}`;

    try {
        const fetchOptions = { method, headers };
        if (body) {
            fetchOptions.body = body instanceof FormData ? body : JSON.stringify(body);
            if (body instanceof FormData) delete headers['Content-Type'];
        }

        const response = await fetch(url, fetchOptions);

        if (!response.ok) {
            if (response.status === 401) throw new Error('密碼錯誤');
            if (response.status === 404) throw new Error('資源不存在');
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `請求失敗 (${response.status})`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API 請求失敗 [${method} ${url}]:`, error.message);
        throw error;
    }
}

// ==================== 幕僚系統 API ====================

async function generateStaffContent(topic, style = "formal", length = "medium") {
    try {
        const data = await adminApiRequest(`${STAFF_API_URL}/content/generate`, {
            method: 'POST',
            body: { topic, style, length },
            requireAuth: true
        });
        return { success: true, ...data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function proofreadContent(text, sessionId = null, isFirstMessage = false) {
    try {
        const message = isFirstMessage
            ? `請幫我校稿以下內容，檢查語法、用詞和事實正確性：\n\n${text}`
            : text;

        const data = await adminApiRequest(`${ADMIN_API_BASE_URL}/chat`, {
            method: 'POST',
            body: { message, session_id: sessionId, role: "staff" }
        });

        return {
            success: true,
            response: data.reply,
            session_id: data.session_id,
            sources: data.sources
        };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function getTasks(limit = 50) {
    try {
        const data = await adminApiRequest(`${STAFF_API_URL}/content/tasks?limit=${limit}`, { requireAuth: true });
        return { success: true, tasks: data.tasks, total: data.total };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function getTask(taskId) {
    try {
        const data = await adminApiRequest(`${STAFF_API_URL}/content/task/${taskId}`, { requireAuth: true });
        return { success: true, task: data.task };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function updateTask(taskId, content, editor = 'admin') {
    try {
        const data = await adminApiRequest(`${STAFF_API_URL}/content/task/${taskId}`, {
            method: 'PUT',
            body: { content, editor },
            requireAuth: true
        });
        return { success: true, message: data.message };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function approveTask(taskId) {
    try {
        const data = await adminApiRequest(`${STAFF_API_URL}/content/task/${taskId}/approve`, {
            method: 'POST',
            requireAuth: true
        });
        return { success: true, message: data.message };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function generateVoice(taskId) {
    try {
        const data = await adminApiRequest(`${STAFF_API_URL}/media/voice/${taskId}`, {
            method: 'POST',
            requireAuth: true
        });
        return { success: true, ...data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function generateVideo(taskId, imagePath, prompt = null) {
    try {
        const queryParams = `image_path=${encodeURIComponent(imagePath)}${prompt ? '&prompt=' + encodeURIComponent(prompt) : ''}`;
        const data = await adminApiRequest(`${STAFF_API_URL}/media/video/${taskId}?${queryParams}`, {
            method: 'POST',
            requireAuth: true
        });
        return { success: true, ...data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// ==================== 知識庫管理 API ====================

async function uploadFile(file, folder = '') {
    try {
        const formData = new FormData();
        formData.append('file', file);
        if (folder) formData.append('folder', folder);

        const data = await adminApiRequest(`${ADMIN_API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData,
            requireAdminAuth: true
        });

        if (data.error) {
            return { success: false, ...data };
        }
        return { success: true, ...data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function ingestDocuments(folderPath = "documents") {
    try {
        const data = await adminApiRequest(`${ADMIN_API_BASE_URL}/ingest`, {
            method: 'POST',
            body: { folder_path: folderPath },
            requireAuth: true
        });
        return { success: true, ...data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function listDocuments() {
    try {
        const data = await adminApiRequest(`${ADMIN_API_BASE_URL}/documents`, { requireAdminAuth: true });
        return { success: true, documents: data.documents || [], total: data.total || 0 };
    } catch (error) {
        return { success: false, error: error.message, documents: [], total: 0 };
    }
}

async function deleteDocument(filePath) {
    try {
        const data = await adminApiRequest(`${ADMIN_API_BASE_URL}/documents/${encodeURIComponent(filePath)}`, {
            method: 'DELETE',
            requireAdminAuth: true
        });
        return { success: true, ...data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// ==================== 系統監控 API ====================

async function getStats() {
    try {
        return await adminApiRequest(`${ADMIN_API_BASE_URL}/stats`);
    } catch (error) {
        return null;
    }
}

async function healthCheck() {
    try {
        return await adminApiRequest(`${ADMIN_API_BASE_URL}/health`);
    } catch (error) {
        return { status: 'error' };
    }
}

async function staffHealthCheck() {
    try {
        return await adminApiRequest(`${ADMIN_API_BASE_URL}/staff-health`);
    } catch (error) {
        return { status: 'error' };
    }
}

// ==================== 訪客計數器 API ====================

async function getVisitorStats(month = null) {
    try {
        const url = month ? `${ADMIN_API_BASE_URL}/visitor/stats?month=${month}` : `${ADMIN_API_BASE_URL}/visitor/stats`;
        const data = await adminApiRequest(url);
        return { success: true, ...data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function incrementVisitor() {
    try {
        const data = await adminApiRequest(`${ADMIN_API_BASE_URL}/visitor/increment`, {
            method: 'POST'
        });
        return { success: true, ...data };
    } catch (error) {
        console.error('增加訪客計數失敗:', error.message);
        return { success: false, error: error.message };
    }
}

async function getTotalVisitors() {
    try {
        const data = await adminApiRequest(`${ADMIN_API_BASE_URL}/visitor/stats`);
        return { success: true, total: data.count || 0, count: data.count || 0, ...data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}