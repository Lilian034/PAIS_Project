# PAIS - 政務分身智能系統

> 基於 LangChain + Gemini + Docker 的市長聊天機器人
> 
> **功能：** 民眾問答 + 團隊文案生成 + 知識庫管理

---

## 📦 系統架構
```
┌─────────────────────────────────────────┐
│  前端 (Nginx)                            │
│  - 民眾聊天介面                          │
│  - 團隊後台管理                          │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│  後端 API (FastAPI + LangChain)          │
│  - RAG 問答 (Agent + Memory)            │
│  - 文案生成 (Chain)                      │
│  - 知識庫管理 (Document Loaders)        │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│  向量資料庫 (Qdrant)                     │
│  - 儲存文件向量                          │
│  - 語義搜尋                              │
└─────────────────────────────────────────┘
```

---

## 🚀 快速開始

### 1️⃣ 前置需求

- ✅ Docker Desktop
- ✅ Gemini API Key ([取得連結](https://makersuite.google.com/app/apikey))

### 2️⃣ 安裝步驟
```bash
# 1. 複製環境變數範本
cp .env.example .env

# 2. 編輯 .env，填入你的 API Key
nano .env

# 3. 建立並啟動所有容器
docker-compose up -d --build

# 4. 查看日誌
docker-compose logs -f rag_api
```

### 3️⃣ 上傳知識庫

**方式一：放入檔案後批量處理**
```bash
# 1. 將文件放入 documents/ 資料夾
cp 你的文件.pdf documents/

# 2. 觸發向量化
curl -X POST http://localhost:8000/api/ingest \
  -H "Authorization: Bearer 你的管理員密碼" \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "documents"}'
```

**方式二：透過網頁上傳**
- 訪問後台上傳頁面
- 選擇檔案上傳（會自動向量化）

## 🌐 訪問網址

| 服務 | 網址 | 用途 |
|------|------|------|
| 民眾聊天頁面 | http://localhost | 公開訪問 |
| 團隊後台 | http://localhost/admin.html | 需要密碼 |
| API 文件 | http://localhost:8000/docs | Swagger UI |
| Qdrant 控制台 | http://localhost:6333/dashboard | 向量資料庫 |

---

## 📚 API 使用說明

### 🟢 民眾端 API（公開）

#### 1. 對話問答
```bash
POST /api/chat

{
  "message": "市長最近在推動什麼政策？",
  "session_id": "user_123",  # 可選
  "use_agent": true          # 是否使用 Agent
}
```

**回應範例：**
```json
{
  "reply": "市長目前正在推動智慧城市計畫...",
  "sources": ["documents/政策白皮書.pdf"],
  "session_id": "user_123",
  "timestamp": "2025-10-28T10:30:00",
  "thought_process": "..."
}
```

#### 2. 查看對話記憶
```bash
GET /api/memory/{session_id}
```

### 🔴 團隊後台 API（需要密碼）

所有請求需要在 Header 加上：
```
Authorization: Bearer 你的管理員密碼
```

#### 1. 生成文案
```bash
POST /api/generate

{
  "topic": "桃園智慧城市計畫",
  "style": "輕鬆",
  "length": "中"
}
```

#### 2. 上傳檔案
```bash
POST /api/upload
Content-Type: multipart/form-data

file: [你的檔案]
```

#### 3. 批量處理知識庫
```bash
POST /api/ingest

{
  "folder_path": "documents"
}
```

#### 4. 清除對話記憶
```bash
DELETE /api/memory/{session_id}
```

---

## 🗂️ 資料夾結構
```
PAIS-Project/
├── docker-compose.yml
├── .env
├── nginx.conf
├── setup.sh
│
├── rag_service/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── index.css
│   ├── people.js
│   ├── admin.html
│   ├── admin.css
│   ├── admin.js
│   └── api.js
│
├── documents/          # 📁 知識庫文件
├── chat_history/       # 💬 對話記錄
├── generated_content/  # ✍️ 生成的文案
├── logs/              # 📊 系統日誌
└── qdrant_storage/    # 🗄️ 向量資料庫
```

---

## 🔧 LangChain 架構說明

### 核心元件

| 元件 | 用途 | 實作 |
|------|------|------|
| **Agents** | 智能代理 | ReAct Agent + 3 工具 |
| **Memory** | 對話記憶 | ConversationBufferMemory |
| **RAG** | 檢索增強生成 | ConversationalRetrievalChain |
| **Chains** | 工作流程 | LLMChain (文案生成) |
| **Tools** | Agent 工具 | 搜尋知識庫、查詢政策、儲存內容 |

---

## 🛠️ 常用指令
```bash
# 啟動服務
docker-compose up -d

# 查看日誌
docker-compose logs -f rag_api

# 停止服務
docker-compose down

# 重新建置
docker-compose up -d --build

# 進入容器
docker exec -it pais-backend bash

# 查看系統狀態
curl http://localhost:8000/health

# 查看統計資訊
curl http://localhost:8000/api/stats
```

---

## 📝 環境變數說明
```bash
# .env 檔案內容

# Gemini API Key (必填)
GEMINI_API_KEY=你的_API_金鑰

# 管理員密碼 (必填)
ADMIN_PASSWORD=你的強密碼

# Qdrant 設定
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

---

## 🐛 故障排除

### 問題 1：容器啟動失敗
```bash
# 檢查 .env 是否正確設定
cat .env

# 查看詳細錯誤
docker-compose logs rag_api
```

### 問題 2：API 回應 401 未授權
```bash
# 確認 Authorization Header 格式
Authorization: Bearer 你的管理員密碼
```

### 問題 3：知識庫搜尋無結果
```bash
# 檢查是否已上傳文件
curl http://localhost:8000/api/stats

# 重新處理知識庫
curl -X POST http://localhost:8000/api/ingest \
  -H "Authorization: Bearer 密碼" \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "documents"}'