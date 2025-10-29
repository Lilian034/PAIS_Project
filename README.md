# PAIS - 政務分身智能系統
```
> 基於 LangChain + Gemini + Docker 的市長聊天機器人
> 
> **功能：** 民眾問答 + 團隊文案生成 + 知識庫管理
```
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

## 🌐 訪問網址
```
| 服務 | 網址 | 用途 |
|------|------|------|
| 民眾聊天頁面 | http://localhost | 公開訪問 |
| 團隊後台 | http://localhost/admin.html | 需要密碼 |
| API 文件 | http://localhost:8000/docs | Swagger UI |
| Qdrant 控制台 | http://localhost:6333/dashboard | 向量資料庫 |
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
```
| 元件 | 用途 | 實作 |
|------|------|------|
| **Agents** | 智能代理 | ReAct Agent + 3 工具 |
| **Memory** | 對話記憶 | ConversationBufferMemory |
| **RAG** | 檢索增強生成 | ConversationalRetrievalChain |
| **Chains** | 工作流程 | LLMChain (文案生成) |
| **Tools** | Agent 工具 | 搜尋知識庫、查詢政策、儲存內容 |
```

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