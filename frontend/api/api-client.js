/**
 * 統一 API 客戶端模組
 * 整合所有 API 調用，提供統一的接口
 */

// API 基礎配置
const API_CONFIG = {
    baseURL: '/api',
    staffURL: '/api/staff',
    adminPassword: 'admin123456',
    get staffPassword() {
        return localStorage.getItem('staff_password') || 'admin123';
    },
    set staffPassword(password) {
        localStorage.setItem('staff_password', password);
    }
};

/**
 * 統一 HTTP 請求處理
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

    if (contentType && !(body instanceof FormData)) {
        headers['Content-Type'] = contentType;
    }

    if (requireAdminAuth) {
        headers['Authorization'] = `Bearer ${API_CONFIG.adminPassword}`;
    } else if (requireAuth) {
        headers['Authorization'] = `Bearer ${API_CONFIG.staffPassword}`;
    }

    try {
        const fetchOptions = { method, headers };

        if (body) {
            fetchOptions.body = body instanceof FormData ? body : JSON.stringify(body);
        }

        const response = await fetch(url, fetchOptions);

        if (!response.ok) {
            if (response.status === 401) throw new Error('密碼錯誤或未授權');
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

/**
 * API 客戶端類
 */
class APIClient {
    static staff = {
        /**
         * 生成文案 (AI 生成模式)
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
         * 【新增】直接建立內容 (不經 AI 生成)
         * 專門給語音生成使用，確保照稿念
         */
        async createDirectContent(content) {
            try {
                const data = await request(`${API_CONFIG.staffURL}/content/direct`, {
                    method: 'POST',
                    body: { 
                        topic: content,  // 將原文放入 topic 欄位
                        style: 'speech',
                        length: 'medium'
                    },
                    requireAuth: true
                });
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

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

        async healthCheck() {
            try {
                const data = await request(`${API_CONFIG.staffURL.replace('/api/staff', '')}/health`);
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        }
    };

    static documents = {
        async upload(file, folder = '') {
            try {
                const formData = new FormData();
                formData.append('file', file);
                if (folder) formData.append('folder', folder);

                const data = await request(`${API_CONFIG.baseURL}/upload`, {
                    method: 'POST',
                    body: formData,
                    requireAuth: true
                });
                return data.error ? { success: false, ...data } : { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        async uploadDocument(file, folder = '') {
            try {
                const formData = new FormData();
                formData.append('file', file);
                if (folder) formData.append('folder', folder);

                const data = await request(`${API_CONFIG.baseURL}/documents/upload`, {
                    method: 'POST',
                    body: formData,
                    requireAdminAuth: true
                });
                return data.error ? { success: false, ...data } : { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

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

        async list() {
            try {
                const data = await request(`${API_CONFIG.baseURL}/documents`, {
                    requireAdminAuth: true
                });
                return {
                    success: true,
                    documents: data.documents || [],
                    total: data.total || 0
                };
            } catch (error) {
                return { success: false, error: error.message, documents: [], total: 0 };
            }
        },

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

    static system = {
        async getStats() {
            try {
                return await request(`${API_CONFIG.baseURL}/stats`);
            } catch (error) {
                return null;
            }
        },
        async healthCheck() {
            try {
                return await request(`${API_CONFIG.baseURL}/health`);
            } catch (error) {
                return { status: 'error' };
            }
        },
        async staffHealthCheck() {
            try {
                return await request(`/api/staff-health`);
            } catch (error) {
                return { status: 'error' };
            }
        }
    };

    static visitor = {
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

    static setStaffPassword(password) {
        API_CONFIG.staffPassword = password;
    }
    static getStaffPassword() {
        return API_CONFIG.staffPassword;
    }
}

export default APIClient;

export const generateStaffContent = APIClient.staff.generateContent.bind(APIClient.staff);
export const createDirectContent = APIClient.staff.createDirectContent.bind(APIClient.staff);
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