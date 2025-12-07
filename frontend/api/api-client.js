/**
 * 統一 API 客戶端模組
 * 整合所有 API 調用，提供統一的接口
 */

// API 基礎配置
const API_CONFIG = {
    baseURL: '/api',
    staffURL: '/api/staff',
    adminPassword: 'admin123456',  // 知識庫管理
    get staffPassword() {
        return localStorage.getItem('staff_password') || 'admin123';
    },
    set staffPassword(password) {
        localStorage.setItem('staff_password', password);
    }
};

/**
 * 統一 HTTP 請求處理
 * @param {string} url - 請求 URL
 * @param {Object} options - 請求選項
 * @returns {Promise<any>}
 */
async function request(url, options = {}) {
    const {
        method = 'GET',
        body,
        requireAuth = false,
        requireAdminAuth = false,
        contentType = 'application/json'
    } = options;

    const headers = {};

    // 設置 Content-Type
    if (contentType && !(body instanceof FormData)) {
        headers['Content-Type'] = contentType;
    }

    // 設置授權
    if (requireAdminAuth) {
        headers['Authorization'] = `Bearer ${API_CONFIG.adminPassword}`;
    } else if (requireAuth) {
        headers['Authorization'] = `Bearer ${API_CONFIG.staffPassword}`;
    }

    try {
        const fetchOptions = { method, headers };

        // 設置請求體
        if (body) {
            fetchOptions.body = body instanceof FormData ? body : JSON.stringify(body);
        }

        const response = await fetch(url, fetchOptions);

        // 處理錯誤狀態
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('密碼錯誤或未授權');
            }
            if (response.status === 404) {
                throw new Error('資源不存在');
            }

            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `請求失敗 (${response.status})`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API 請求失敗 [${method} ${url}]:`, error.message);
        throw error;
    }
}

/**
 * API 客戶端類
 */
class APIClient {
    /**
     * 幕僚系統 API
     */
    static staff = {
        /**
         * 生成文案
         * @param {string} topic - 文案主題
         * @param {string} style - 文案類型 (press/speech/facebook/instagram/poster)
         * @param {string} length - 文案長度 (short/medium/long)
         */
        async generateContent(topic, style = 'speech', length = 'medium') {
            try {
                const data = await request(`${API_CONFIG.staffURL}/content/generate`, {
                    method: 'POST',
                    body: { topic, style, length },
                    requireAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 校稿
         */
        async proofread(text, sessionId = null, isFirstMessage = false) {
            try {
                const message = isFirstMessage
                    ? `請幫我校稿以下內容，檢查語法、用詞和事實正確性：\n\n${text}`
                    : text;

                const data = await request(`${API_CONFIG.baseURL}/chat`, {
                    method: 'POST',
                    body: { message, session_id: sessionId, role: 'staff' }
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
        },

        /**
         * 獲取任務列表
         */
        async getTasks(limit = 50) {
            try {
                const data = await request(`${API_CONFIG.staffURL}/content/tasks?limit=${limit}`, {
                    requireAuth: true
                });
                return { success: true, tasks: data.tasks, total: data.total };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 獲取單個任務
         */
        async getTask(taskId) {
            try {
                const data = await request(`${API_CONFIG.staffURL}/content/task/${taskId}`, {
                    requireAuth: true
                });
                return { success: true, task: data.task };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 更新任務
         */
        async updateTask(taskId, content, editor = 'admin') {
            try {
                const data = await request(`${API_CONFIG.staffURL}/content/task/${taskId}`, {
                    method: 'PUT',
                    body: { content, editor },
                    requireAuth: true
                });
                return { success: true, message: data.message };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 審核通過任務
         */
        async approveTask(taskId) {
            try {
                const data = await request(`${API_CONFIG.staffURL}/content/task/${taskId}/approve`, {
                    method: 'POST',
                    requireAuth: true
                });
                return { success: true, message: data.message };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 生成語音
         */
        async generateVoice(taskId) {
            try {
                const data = await request(`${API_CONFIG.staffURL}/media/voice/${taskId}`, {
                    method: 'POST',
                    requireAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 生成 Avatar Video（HeyGen）- 使用任務音頻
         */
        async generateVideo(taskId, imagePath, prompt = null) {
            try {
                const queryParams = `image_path=${encodeURIComponent(imagePath)}`;
                const data = await request(`${API_CONFIG.staffURL}/media/avatar-video/${taskId}?${queryParams}`, {
                    method: 'POST',
                    requireAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 生成 Avatar Video（HeyGen）- 使用上傳的音頻
         */
        async generateVideoWithUploadedAudio(audioPath, imagePath, prompt = null) {
            try {
                const queryParams = `audio_path=${encodeURIComponent(audioPath)}&image_path=${encodeURIComponent(imagePath)}`;
                const data = await request(`${API_CONFIG.staffURL}/media/avatar-video-upload?${queryParams}`, {
                    method: 'POST',
                    requireAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 查詢媒體生成狀態
         */
        async getMediaStatus(taskId) {
            try {
                const data = await request(`${API_CONFIG.staffURL}/media/status/${taskId}`, {
                    requireAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 獲取可用的語音列表
         */
        async getVoices() {
            try {
                const data = await request(`${API_CONFIG.staffURL}/media/voices`, {
                    requireAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 獲取可用的 Avatar 列表
         */
        async getAvatars() {
            try {
                const data = await request(`${API_CONFIG.staffURL}/media/avatars`, {
                    requireAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 健康檢查（包含 API 配置狀態）
         */
        async healthCheck() {
            try {
                const data = await request(`${API_CONFIG.staffURL.replace('/api/staff', '')}/health`);
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        }
    };

    /**
     * 知識庫管理 API
     */
    static documents = {
        /**
         * 上傳媒體素材（音頻、圖片）
         * 用於短影音生成，不加入知識庫
         */
        async upload(file, folder = '') {
            try {
                const formData = new FormData();
                formData.append('file', file);
                if (folder) formData.append('folder', folder);

                const data = await request(`${API_CONFIG.baseURL}/upload`, {
                    method: 'POST',
                    body: formData,
                    requireAuth: true  // 使用幕僚密碼
                });

                return data.error ? { success: false, ...data } : { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 上傳政務文檔（PDF、DOCX等）
         * 加入知識庫
         */
        async uploadDocument(file, folder = '') {
            try {
                const formData = new FormData();
                formData.append('file', file);
                if (folder) formData.append('folder', folder);

                const data = await request(`${API_CONFIG.baseURL}/documents/upload`, {
                    method: 'POST',
                    body: formData,
                    requireAdminAuth: true  // 使用管理員密碼
                });

                return data.error ? { success: false, ...data } : { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 批次處理文檔
         */
        async ingest(folderPath = 'documents') {
            try {
                const data = await request(`${API_CONFIG.baseURL}/ingest`, {
                    method: 'POST',
                    body: { folder_path: folderPath },
                    requireAdminAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 列出文檔
         */
        async list(sort = 'newest') {
            try {
                const data = await request(`${API_CONFIG.baseURL}/documents?sort=${sort}`, {
                    requireAdminAuth: true
                });
                return {
                    success: true,
                    documents: data.documents || [],
                    total: data.total || 0
                };
            } catch (error) {
                return {
                    success: false,
                    error: error.message,
                    documents: [],
                    total: 0
                };
            }
        },

        /**
         * 刪除文檔
         */
        async delete(filePath) {
            try {
                const data = await request(`${API_CONFIG.baseURL}/documents/${encodeURIComponent(filePath)}`, {
                    method: 'DELETE',
                    requireAdminAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        }
    };

    /**
     * 系統監控 API
     */
    static system = {
        /**
         * 獲取統計信息
         */
        async getStats() {
            try {
                return await request(`${API_CONFIG.baseURL}/stats`);
            } catch (error) {
                return null;
            }
        },

        /**
         * 健康檢查
         */
        async healthCheck() {
            try {
                return await request(`${API_CONFIG.baseURL}/health`);
            } catch (error) {
                return { status: 'error' };
            }
        },

        /**
         * 幕僚系統健康檢查
         */
        async staffHealthCheck() {
            try {
                return await request(`/api/staff-health`);
            } catch (error) {
                return { status: 'error' };
            }
        }
    };

    /**
     * 訪客統計 API
     */
    static visitor = {
        /**
         * 獲取訪客統計
         */
        async getStats(month = null) {
            try {
                const url = month
                    ? `${API_CONFIG.baseURL}/visitor/stats?month=${month}`
                    : `${API_CONFIG.baseURL}/visitor/stats`;
                const data = await request(url);
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 增加訪客計數
         */
        async increment() {
            try {
                const data = await request(`${API_CONFIG.baseURL}/visitor/increment`, {
                    method: 'POST'
                });
                return { success: true, ...data };
            } catch (error) {
                console.error('增加訪客計數失敗:', error.message);
                return { success: false, error: error.message };
            }
        },

        /**
         * 獲取總訪客數
         */
        async getTotal() {
            try {
                const data = await request(`${API_CONFIG.baseURL}/visitor/stats`);
                return {
                    success: true,
                    total: data.count || 0,
                    count: data.count || 0,
                    ...data
                };
            } catch (error) {
                return { success: false, error: error.message };
            }
        }
    };

    /**
     * 設置幕僚密碼
     */
    static setStaffPassword(password) {
        API_CONFIG.staffPassword = password;
    }

    /**
     * 獲取幕僚密碼
     */
    static getStaffPassword() {
        return API_CONFIG.staffPassword;
    }
}

// 導出 API 客戶端
export default APIClient;

// 向後兼容：導出舊的函數名稱
export const generateStaffContent = APIClient.staff.generateContent.bind(APIClient.staff);
export const proofreadContent = APIClient.staff.proofread.bind(APIClient.staff);
export const getTasks = APIClient.staff.getTasks.bind(APIClient.staff);
export const getTask = APIClient.staff.getTask.bind(APIClient.staff);
export const updateTask = APIClient.staff.updateTask.bind(APIClient.staff);
export const approveTask = APIClient.staff.approveTask.bind(APIClient.staff);
export const generateVoice = APIClient.staff.generateVoice.bind(APIClient.staff);
export const generateVideo = APIClient.staff.generateVideo.bind(APIClient.staff);
export const uploadFile = APIClient.documents.upload.bind(APIClient.documents);
export const listDocuments = APIClient.documents.list.bind(APIClient.documents);
export const deleteDocument = APIClient.documents.delete.bind(APIClient.documents);
export const ingestDocuments = APIClient.documents.ingest.bind(APIClient.documents);
export const getStats = APIClient.system.getStats.bind(APIClient.system);
export const healthCheck = APIClient.system.healthCheck.bind(APIClient.system);
export const staffHealthCheck = APIClient.system.staffHealthCheck.bind(APIClient.system);
export const getVisitorStats = APIClient.visitor.getStats.bind(APIClient.visitor);
export const incrementVisitor = APIClient.visitor.increment.bind(APIClient.visitor);
export const getTotalVisitors = APIClient.visitor.getTotal.bind(APIClient.visitor);
export const setStaffPassword = APIClient.setStaffPassword.bind(APIClient);
export const getStaffPassword = APIClient.getStaffPassword.bind(APIClient);
