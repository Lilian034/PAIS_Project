# PAIS - 政務分身智能系統

> 基於 LangChain + Gemini + Docker 的市長智能助理
>
> **功能：** 民眾問答 + 幕僚文案生成 + 知識庫管理

---

## 📦 系統架構

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

## 🌟 核心功能

### 1️⃣ 民眾問答系統 (port 8000)
- 🤖 AI 聊天機器人 (Agent + Memory)
- 📚 RAG 知識庫問答
- 💬 對話記憶功能
- 🎯 語氣模仿

### 2️⃣ 幕僚系統 (port 8001)
- ✍️ **文案生成** (LLM + Memory + RAG)
  - 自動從知識庫檢索資料
  - 學習市長用字遣詞
  - 持續優化生成品質

- ✏️ **文案審核**
  - 人工修改與優化
  - 版本控制
  - 修改記錄作為學習樣本

- 🎤 **語音克隆** (ElevenLabs)
  - 文字轉語音
  - 克隆市長聲音

- 🎬 **影片生成** (Runway)
  - 圖片轉動態影片

- 📚 **知識庫管理**
  - 文件上傳
  - 自動向量化

---

## 🚀 快速開始

### 前置需求
- Docker Desktop
- docker-compose

### 1. 設定環境變數

複製 `.env.example` 為 `.env` 並填入 API Keys:

```bash
cp .env.example .env
```

編輯 `.env`:
```bash
# 必填
GEMINI_API_KEY=your_gemini_api_key

# 選填 (沒填對應功能無法使用)
ELEVENLABS_API_KEY=your_elevenlabs_key  # 語音克隆
MAYOR_VOICE_ID=your_voice_id             # 語音克隆
RUNWAY_API_KEY=your_runway_key           # 影片生成
```

### 2. 一鍵部署

```bash
chmod +x setup.sh
./setup.sh
```

### 3. 訪問系統

| 服務 | 網址 | 說明 |
|------|------|------|
| 民眾聊天 | http://localhost | 公開訪問 |
| 幕僚後台 | http://localhost/admin.html | 需要密碼 |
| 民眾 API | http://localhost:8000/docs | Swagger UI |
| 幕僚 API | http://localhost:8001/docs | Swagger UI |
| Qdrant | http://localhost:6333/dashboard | 向量資料庫 |

---

## 🗂️ 專案結構

```
PAIS_Project/
├── frontend/                          # 前端檔案（已重構 - Phase 2 & 3）
│   ├── index.html                    # 民眾聊天介面
│   ├── index.css                     # 民眾系統樣式（BEM 重構）
│   ├── index.js                      # 民眾系統腳本
│   │
│   ├── admin.html                    # 幕僚系統介面
│   ├── admin.css                     # 幕僚系統樣式（BEM 重構）
│   ├── admin.js                      # 幕僚系統主入口（271 行，ES6 模組）
│   │
│   ├── utils/                        # 🔧 工具模組
│   │   ├── dom-helper.js            # DOM 操作工具
│   │   └── notification.js          # 通知系統
│   │
│   ├── api/                          # 🌐 API 客戶端
│   │   └── api-client.js            # 統一 API 接口管理
│   │
│   └── modules/                      # 📦 功能模組
│       ├── tab-manager.js           # 標籤切換
│       ├── document-manager.js      # 文件管理
│       ├── proofreading.js          # 校稿對話
│       ├── content-generator.js     # 內容生成
│       ├── voice-generator.js       # 語音生成
│       ├── video-generator.js       # 影片生成
│       └── data-monitor.js          # 數據監控
│
├── rag_service/                      # 後端服務（已重構 - Phase 1）
│   ├── public_service.py            # 民眾問答 API (8000)
│   ├── staff_service.py             # 幕僚系統 API (8001)
│   │
│   ├── prompts/                      # 🎯 提示詞模組（新增）
│   │   ├── __init__.py
│   │   ├── public_agent.py          # 民眾 Agent 提示詞
│   │   └── staff_agent.py           # 幕僚 Agent 提示詞
│   │
│   ├── services/                     # 💼 業務邏輯層
│   │   ├── chat_service.py          # 聊天服務（新增）
│   │   ├── content_generator.py     # 文案生成
│   │   ├── memory_manager.py        # 記憶管理
│   │   ├── elevenlabs_service.py    # 語音服務
│   │   └── runway_service.py        # 影片服務
│   │
│   ├── utils/                        # 🔧 工具模組
│   │   ├── error_handler.py         # 統一錯誤處理（新增）
│   │   ├── db_helper.py             # 資料庫工具
│   │   └── task_manager.py          # 任務管理
│   │
│   └── models/                       # 📋 資料模型
│       ├── chat_models.py
│       ├── staff_models.py
│       └── document_models.py
│
├── documents/                        # 📁 知識庫文件
│
├── chat_history/                     # 💬 對話記錄
│   ├── public/                      # 民眾對話
│   └── staff/                       # 幕僚記憶
│
├── generated_content/                # ✍️ 生成內容
│   ├── drafts/                      # 草稿
│   ├── approved/                    # 已審核
│   ├── voices/                      # 語音檔
│   └── videos/                      # 影片檔
│
├── database/                         # 🗄️ SQLite 資料庫
│   └── staff_system.db
│
├── logs/                             # 📊 系統日誌
├── qdrant_storage/                   # 🗄️ 向量資料庫
│
├── docker-compose.yml                # Docker 配置
├── nginx.conf                        # Nginx 配置
├── .env                              # 環境變數
└── setup.sh                          # 快速部署腳本
```

---

## 🏗️ 重構架構說明

本專案經過三階段全面重構，採用現代化架構模式：

### Phase 1: 後端 Python 重構 ✅

#### 核心改進
1. **提示詞模組化** (`prompts/`)
   - 將 220+ 行硬編碼提示詞提取到獨立模組
   - 便於版本控制和 A/B 測試
   - 支援多語言和多角色擴展

2. **統一錯誤處理** (`utils/error_handler.py`)
   - 自定義異常類型層次結構
   - 裝飾器模式 (`@handle_api_error`)
   - 支援同步/異步函數
   - 自動日誌記錄

3. **服務層模式** (`services/chat_service.py`)
   - 將 147 行 `/api/chat` 端點簡化為 30 行
   - 依賴注入模式提升可測試性
   - 統一 Agent 和 RAG Chain 處理邏輯

#### 範例：錯誤處理裝飾器
```python
from utils.error_handler import handle_api_error, APIError

@handle_api_error(error_message="聊天處理失敗", log_error=True)
async def process_chat(message: str, session_id: str):
    # 業務邏輯
    if not message:
        raise ValidationError("訊息不能為空")
    return await chat_service.process(message, session_id)
```

### Phase 2: 前端 JavaScript 重構 ✅

#### 核心改進
1. **ES6 模組化**
   - `admin.js` 從 1,673 行減少到 271 行（-84%）
   - 採用 `import/export` 語法
   - 功能模組獨立開發和測試

2. **模組結構**
   ```javascript
   // admin.js - 主入口
   import * as TabManager from './modules/tab-manager.js';
   import * as DocumentManager from './modules/document-manager.js';
   import APIClient from './api/api-client.js';

   document.addEventListener('DOMContentLoaded', () => {
       TabManager.init();
       DocumentManager.init();
       // ... 其他模組初始化
   });
   ```

3. **統一 API 客戶端** (`api/api-client.js`)
   ```javascript
   // 模組化 API 接口
   class APIClient {
       static staff = {
           async generateContent(topic, style, length) { /* ... */ },
           async proofread(text, sessionId) { /* ... */ }
       };

       static documents = {
           async upload(file, folder) { /* ... */ },
           async list() { /* ... */ }
       };
   }
   ```

4. **全局導出（向後兼容）**
   ```javascript
   // 支援 HTML 內聯事件處理
   if (typeof window !== 'undefined') {
       window.contentGenerator = { generate, copy, save };
   }
   ```

#### 工具模組
- **dom-helper.js**: 統一 DOM 操作（選擇器、創建元素、事件綁定）
- **notification.js**: 通知系統（成功/錯誤/警告/確認對話框）

### Phase 3: 前端 CSS 重構 ✅

#### 核心改進
1. **BEM 命名規範**
   ```css
   /* Block__Element--Modifier */
   .navbar__brand { }
   .navbar__avatar { }
   .navbar__logout-btn { }

   .sidebar__item { }
   .sidebar__item--active { }

   .btn--primary { }
   .btn--danger { }
   .btn--icon { }
   ```

2. **CSS 變量系統**
   ```css
   :root {
       /* 間距系統 */
       --spacing-xs: 0.5rem;
       --spacing-sm: 1rem;
       --spacing-md: 1.5rem;
       --spacing-lg: 2rem;

       /* 圓角系統 */
       --radius-sm: 6px;
       --radius-md: 10px;
       --radius-lg: 14px;
   }
   ```

3. **功能區組織**
   ```css
   /* ==================== Base Styles ==================== */
   /* 重置、變量、字體 */

   /* ==================== Layout Components ==================== */
   /* 導航欄、側邊欄、主容器 */

   /* ==================== UI Components ==================== */
   /* 按鈕、輸入框、卡片 */

   /* ==================== Utilities ==================== */
   /* 輔助類 */
   ```

4. **100% 向後兼容**
   - 保留所有舊類名（`.nav-item`, `.btn`, `.card`）
   - 新增 BEM 類名作為推薦使用
   - 漸進式遷移策略

---

## 🔧 幕僚系統工作流程

### 步驟 1: 文案生成
```bash
POST /api/staff/content/generate
{
  "topic": "市政建設成果",
  "style": "casual",      # formal/casual/humorous
  "length": "medium"      # short/medium/long
}
```

**前端調用範例：**
```javascript
import APIClient from './api/api-client.js';

const result = await APIClient.staff.generateContent(
    '市政建設成果',
    'casual',
    'medium'
);

if (result.success) {
    console.log('任務 ID:', result.task_id);
    console.log('生成內容:', result.content);
}
```

### 步驟 2a: 人工修改
```bash
PUT /api/staff/content/task/{task_id}
{
  "content": "修改後的文案內容...",
  "editor": "admin"
}
```

### 步驟 2b: 審核通過
```bash
POST /api/staff/content/task/{task_id}/approve
```

### 步驟 3: 語音克隆
```bash
POST /api/staff/media/voice/{task_id}
```

**前端調用範例：**
```javascript
const voiceResult = await APIClient.staff.generateVoice(taskId);
if (voiceResult.success) {
    console.log('語音檔案:', voiceResult.file_path);
}
```

### 步驟 4: 影片生成
```bash
POST /api/staff/media/video/{task_id}
{
  "image_path": "path/to/image.jpg",
  "prompt": "自然動態效果"
}
```

---

## 🧠 LangChain 架構說明

### 民眾問答系統
```
Agent (ReAct)
  └─> Tools
       ├─> 搜尋知識庫 (RAG)
       ├─> 查詢政策
       └─> 儲存記錄
  └─> Memory (ConversationBufferMemory)
```

**核心實現：**
```python
# services/chat_service.py
class ChatService:
    async def process_chat(self, message: str, session_id: str,
                          memory: ConversationBufferMemory,
                          use_agent: bool = True):
        if use_agent:
            # 使用 Agent 模式
            agent_executor = AgentExecutor.from_agent_and_tools(
                agent=self.agent,
                tools=self.tools,
                memory=memory
            )
            result = await agent_executor.ainvoke({"input": message})
        else:
            # 使用 RAG Chain 模式
            result = await self.rag_chain.ainvoke({
                "question": message,
                "chat_history": memory.chat_memory.messages
            })
        return result
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

## 💻 開發指南

### 前端開發規範

#### 1. JavaScript 模組開發
```javascript
// modules/example-module.js

import { $, createElement } from '../utils/dom-helper.js';
import { showNotification } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// ==================== 模組狀態 ====================
let moduleState = null;

// ==================== 公開函數 ====================

/**
 * 初始化模組
 * @export
 */
export function init() {
    bindEvents();
    console.log('✅ 模組已初始化');
}

/**
 * 執行操作
 * @export
 */
export async function performAction() {
    try {
        const result = await APIClient.staff.someMethod();
        if (result.success) {
            showNotification('操作成功', 'success');
        }
    } catch (error) {
        showNotification('操作失敗', 'error');
    }
}

// ==================== 私有函數 ====================

function bindEvents() {
    const btn = $('#actionBtn');
    if (btn) {
        btn.addEventListener('click', performAction);
    }
}

// ==================== 全局導出（供 HTML 內聯事件使用） ====================

if (typeof window !== 'undefined') {
    window.exampleModule = {
        performAction
    };
}
```

#### 2. CSS BEM 命名
```css
/* 區塊 (Block) */
.feature-card { }

/* 元素 (Element) */
.feature-card__header { }
.feature-card__title { }
.feature-card__description { }

/* 修飾符 (Modifier) */
.feature-card--highlighted { }
.feature-card--disabled { }

/* 組合使用 */
.feature-card__title--large { }
```

#### 3. API 客戶端擴展
```javascript
// api/api-client.js

class APIClient {
    // 新增 API 分組
    static newFeature = {
        async getData(params) {
            const response = await fetch('/api/new-feature/data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            return await response.json();
        }
    };
}

// 向後兼容導出
export const getNewFeatureData = APIClient.newFeature.getData.bind(APIClient.newFeature);
```

### 後端開發規範

#### 1. 服務層開發
```python
# services/new_service.py

from utils.error_handler import handle_api_error, APIError
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class NewService:
    """新服務類 - 負責特定業務邏輯"""

    def __init__(self, dependency):
        self.dependency = dependency

    @handle_api_error(error_message="操作失敗", log_error=True)
    async def perform_operation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行業務操作

        Args:
            params: 操作參數

        Returns:
            操作結果字典

        Raises:
            ValidationError: 參數驗證失敗
            APIError: API 調用失敗
        """
        # 驗證參數
        if not params.get('required_field'):
            raise ValidationError("缺少必要參數")

        # 執行業務邏輯
        result = await self.dependency.process(params)

        return {
            "success": True,
            "data": result
        }
```

#### 2. API 端點開發
```python
# public_service.py 或 staff_service.py

from fastapi import APIRouter, HTTPException
from services.new_service import NewService
from models.new_models import NewRequest, NewResponse

router = APIRouter()
new_service = NewService(dependency)

@router.post("/api/new-endpoint", response_model=NewResponse)
async def new_endpoint(request: NewRequest):
    """
    新端點說明

    Args:
        request: 請求模型

    Returns:
        NewResponse: 響應模型
    """
    try:
        result = await new_service.perform_operation(request.dict())
        return NewResponse(**result)
    except ValueError as e:
        logger.error(f"❌ 處理錯誤: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 🛠️ 常用指令

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

## 📊 資料庫說明

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

## 🔑 環境變數說明

| 變數名稱 | 必填 | 說明 |
|---------|------|------|
| GEMINI_API_KEY | ✅ | Google Gemini API Key |
| QDRANT_HOST | ✅ | Qdrant 主機 (預設: qdrant) |
| QDRANT_PORT | ✅ | Qdrant 埠號 (預設: 6333) |
| ADMIN_PASSWORD | ✅ | 管理員密碼 |
| STAFF_PASSWORD | ✅ | 幕僚系統密碼 |
| ELEVENLABS_API_KEY | ❌ | ElevenLabs API Key |
| MAYOR_VOICE_ID | ❌ | 市長語音 ID |
| RUNWAY_API_KEY | ❌ | Runway API Key |

---

## ⚠️ 注意事項

### API Keys
- ElevenLabs 和 Runway 需要付費訂閱
- 沒設定的話對應功能無法使用
- 測試時可以先不填，跳過語音/影片生成

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

## 🐛 問題排查

### 容器啟動失敗
```bash
# 查看日誌
docker-compose logs

# 重新建置
docker-compose down
docker-compose up -d --build
```

### API 無法連線
```bash
# 檢查服務狀態
docker-compose ps

# 檢查網路
docker network ls

# 測試 API 連接
curl http://localhost:8000/health
curl http://localhost:8001/health/staff
```

### 知識庫檢索失敗
```bash
# 確認 Qdrant 正常運行
curl http://localhost:6333/dashboard

# 重新建立索引
docker exec -it pais-public-api python -c "from main import *; ingest_documents('documents')"
```

### 前端模組載入失敗
1. 檢查瀏覽器控制台是否有 CORS 錯誤
2. 確認 `admin.html` 中使用 `<script type="module">`
3. 檢查模組路徑是否正確
4. 確認所有模組都有正確的 `export` 語句

### CSS 樣式問題
1. 優先使用 BEM 類名（`.block__element--modifier`）
2. 舊類名仍然可用（向後兼容）
3. 檢查瀏覽器開發工具確認樣式是否被覆蓋
4. 使用 CSS 變量確保一致性

---

## 📝 重構成果總結

### Phase 1: 後端 Python 重構
- ✅ 提取 220+ 行提示詞到獨立模組
- ✅ 創建統一錯誤處理系統（228 行）
- ✅ 提取聊天服務類（445 行）
- ✅ 簡化 `/api/chat` 端點從 147 行到 30 行
- ✅ `public_service.py` 減少約 400 行

### Phase 2: 前端 JavaScript 重構
- ✅ `admin.js` 從 1,673 行減少到 271 行（-84%）
- ✅ 創建 7 個功能模組
- ✅ 創建統一 API 客戶端（457 行）
- ✅ 創建工具模組（dom-helper, notification）
- ✅ 100% 向後兼容（全局導出）

### Phase 3: 前端 CSS 重構
- ✅ `admin.css` 採用 BEM 命名（1,463 行）
- ✅ `index.css` 採用 BEM 命名（632 行）
- ✅ 新增 CSS 變量系統
- ✅ 功能區組織（Base, Layout, Components, Utilities）
- ✅ 100% 向後兼容（保留舊類名）

### 總體收益
- 🎯 **可維護性提升**: 模組化結構，單一職責原則
- 🧪 **可測試性提升**: 依賴注入，服務層分離
- 📦 **可擴展性提升**: 清晰的模組邊界，易於新增功能
- 🔄 **向後兼容**: 所有舊代碼仍可正常運行
- 📚 **文檔完善**: 完整的 Docstrings 和註釋

---

## 🚧 待開發功能

- [ ] 批次文案生成
- [ ] 定時任務排程
- [ ] 更多語音選項
- [ ] 影片樣式客製化
- [ ] 數據分析面板
- [ ] 單元測試覆蓋率提升
- [ ] E2E 測試框架
- [ ] 性能監控面板

---

## 👥 開發團隊

PAIS 政務分身智能系統開發團隊

---

## 📄 授權

© 2024 PAIS Project. All rights reserved.
