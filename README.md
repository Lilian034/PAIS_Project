# PAIS - 政務分身智能系統

> 基於 LangChain + Gemini + Docker 的市長智能助理
>
> **功能：** 民眾問答 + 幕僚文案生成 + 知識庫管理

---

## 系統架構

```
┌─────────────────────────────────────────┐
│  前端 (Nginx)                            │
│  - 民眾聊天介面 (index.html)            │
│  - 幕僚系統介面 (admin.html)            │
└────────────┬────────────────────────────┘
             │
      ┌──────┴──────┐
      │             │
┌─────▼────┐  ┌────▼─────┐
│民眾問答API│  │幕僚系統API│
│  8000    │  │   8001   │
│          │  │          │
│ RAG 問答 │  │ 文案生成 │
│ + Memory │  │ + Memory │
└────┬─────┘  └────┬─────┘
     │             │
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │Qdrant 向量庫│
     │   6333     │
     └─────────────┘
```

---

## 核心功能

### 民眾問答系統 (port 8000)
- AI 聊天機器人 (Agent + Memory)
- RAG 知識庫問答
- 對話記憶功能
- 語氣模仿

### 幕僚系統 (port 8001)
- **文案生成** (LLM + Memory + RAG)
  - 自動從知識庫檢索資料
  - 學習市長用字遣詞
  - 持續優化生成品質

- **文案審核**
  - 人工修改與優化
  - 版本控制
  - 修改記錄作為學習樣本

- **語音克隆** (ElevenLabs)
  - 文字轉語音
  - 克隆市長聲音

- **影片生成** (Runway)
  - 圖片轉動態影片

- **知識庫管理**
  - 文件上傳
  - 自動向量化

---

### 3. 訪問系統

| 服務 | 網址 | 說明 |
|------|------|------|
| 民眾聊天 | http://localhost | 公開訪問 |
| 幕僚後台 | http://localhost/admin.html | 需要密碼 |
| 民眾 API | http://localhost:8000/docs | Swagger UI |
| 幕僚 API | http://localhost:8001/docs | Swagger UI |
| Qdrant | http://localhost:6333/dashboard | 向量資料庫 |

---

## 專案結構

```
PAIS_Project/
├── frontend/                          # 前端檔案
│   ├── index.html                    # 民眾聊天介面
│   ├── index.css                     # 民眾系統樣式
│   ├── index.js                      # 民眾系統腳本
│   │
│   ├── admin.html                    # 幕僚系統介面
│   ├── admin.css                     # 幕僚系統樣式
│   ├── admin.js                      # 幕僚系統主入口
│   │
│   ├── utils/                        # 工具模組
│   │   ├── dom-helper.js            # DOM 操作工具
│   │   └── notification.js          # 通知系統
│   │
│   ├── api/                          # API 客戶端
│   │   └── api-client.js            # 統一 API 接口管理
│   │
│   └── modules/                      # 功能模組
│       ├── tab-manager.js           # 標籤切換
│       ├── document-manager.js      # 文件管理
│       ├── proofreading.js          # 校稿對話
│       ├── content-generator.js     # 內容生成
│       ├── voice-generator.js       # 語音生成
│       ├── video-generator.js       # 影片生成
│       └── data-monitor.js          # 數據監控
│
├── rag_service/                      # 後端服務
│   ├── public_service.py            # 民眾問答 API (8000)
│   ├── staff_service.py             # 幕僚系統 API (8001)
│   │
│   ├── prompts/                      # 提示詞模組
│   │   ├── __init__.py
│   │   ├── public_agent.py          # 民眾 Agent 提示詞
│   │   └── staff_agent.py           # 幕僚 Agent 提示詞
│   │
│   ├── services/                     # 業務邏輯層
│   │   ├── chat_service.py          # 聊天服務
│   │   ├── content_generator.py     # 文案生成
│   │   ├── memory_manager.py        # 記憶管理
│   │   ├── elevenlabs_service.py    # 語音服務
│   │   └── runway_service.py        # 影片服務
│   │
│   ├── utils/                        # 工具模組
│   │   ├── error_handler.py         # 統一錯誤處理
│   │   ├── db_helper.py             # 資料庫工具
│   │   └── task_manager.py          # 任務管理
│   │
│   └── models/                       # 資料模型
│       ├── chat_models.py
│       ├── staff_models.py
│       └── document_models.py
│
├── documents/                        # 知識庫文件
│
├── chat_history/                     # 對話記錄
│   ├── public/                      # 民眾對話
│   └── staff/                       # 幕僚記憶
│
├── generated_content/                # 生成內容
│   ├── drafts/                      # 草稿
│   ├── approved/                    # 已審核
│   ├── voices/                      # 語音檔
│   └── videos/                      # 影片檔
│
├── database/                         # SQLite 資料庫
│   └── staff_system.db
│
├── logs/                             # 系統日誌
├── qdrant_storage/                   # 向量資料庫
│
├── docker-compose.yml                # Docker 配置
├── nginx.conf                        # Nginx 配置
├── .env                              # 環境變數
└── setup.sh                          # 快速部署腳本
```

---

## LangChain 架構說明

### 民眾問答系統
```
Agent (ReAct)
  └─> Tools
       ├─> 搜尋知識庫 (RAG)
       ├─> 查詢政策
       └─> 儲存記錄
  └─> Memory (ConversationBufferMemory)
```

### 幕僚系統
```
LLMChain (文案生成)
  └─> Prompt (含記憶學習)
  └─> Memory (每個任務獨立記憶)
  └─> RAG (知識庫檢索)
  └─> 持續學習 (儲存修改記錄)
```

---

## 常用指令

```bash
# 啟動服務
docker-compose up -d

# 查看日誌
docker-compose logs -f public_api   # 民眾系統
docker-compose logs -f staff_api    # 幕僚系統

# 重新啟動
docker-compose restart

# 停止服務
docker-compose down

# 重新建置
docker-compose up -d --build

# 進入容器
docker exec -it pais-public-api bash
docker exec -it pais-staff-api bash

# 查看系統狀態
curl http://localhost:8000/health    # 民眾系統
curl http://localhost:8001/health    # 幕僚系統
```

---

## 資料庫說明

### Qdrant (向量資料庫)
- 儲存知識庫文件向量
- 兩系統共用
- 支援語義搜尋
- 使用 HuggingFace Embeddings

### SQLite (幕僚系統)
| 資料表 | 說明 |
|-------|------|
| `content_tasks` | 文案任務主表 |
| `content_versions` | 文案版本歷史 |
| `media_records` | 多媒體生成記錄 |

---

## 注意事項

### 記憶管理
- 記憶檔案會持續增長
- 建議定期清理舊任務記憶
- 位置: `chat_history/staff/`

### 知識庫
- 兩系統共用知識庫 (`documents/`)
- 文案生成會從知識庫檢索資料
- 確保上傳足夠的市政文件

### 效能
- 初次啟動需要下載模型 (約 1-2 分鐘)
- 文案生成時間約 5-15 秒
- 語音生成時間約 10-30 秒
- 影片生成時間約 1-5 分鐘

### 模組導入
- 前端使用 ES6 模組，需確保 `<script type="module">`
- 舊版瀏覽器可能需要 polyfill
- 開發時使用現代瀏覽器（Chrome, Firefox, Safari）

---
PAIS 政務分身智能系統開發團隊
© 2024 PAIS Project. All rights reserved.
