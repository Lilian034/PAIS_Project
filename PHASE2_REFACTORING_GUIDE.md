# Phase 2 前端 JavaScript 重構指南

## 📊 重構概覽

**目標**: 將 1,673 行的 `admin.js` 拆分為模組化、可維護的結構
**原則**: ES6 Modules、單一職責、關注點分離
**狀態**: ✅ 基礎設施完成，📝 模組拆分進行中

---

## ✅ 已完成的基礎設施

### 1. 工具模組 (`/frontend/utils/`)

#### `dom-helper.js` - DOM 操作輔助工具
```javascript
// 提供的功能：
- $(selector)          // 選擇單個元素
- $$(selector)         // 選擇多個元素
- createElement()      // 創建元素
- addClass/removeClass // 類別操作
- show/hide/toggle     // 顯示/隱藏
- on/off/delegate      // 事件處理
- escapeHtml()         // HTML 轉義
- formatFileSize()     // 檔案大小格式化
- getFileIcon()        // 獲取檔案圖標
- formatDateTime()     // 日期時間格式化
```

#### `notification.js` - 通知系統
```javascript
// 提供的功能：
- showNotification(message, type, duration)
- success(message)
- error(message)
- warning(message)
- info(message)
- confirm(message)
- prompt(message, defaultValue)
```

### 2. API 客戶端 (`/frontend/api/`)

#### `api-client.js` - 統一 API 客戶端
```javascript
// 提供的 API 模組：
APIClient.staff          // 幕僚系統 API
  - generateContent()
  - proofread()
  - getTasks()
  - getTask()
  - updateTask()
  - approveTask()
  - generateVoice()
  - generateVideo()

APIClient.documents      // 知識庫管理 API
  - upload()
  - list()
  - delete()
  - ingest()

APIClient.system         // 系統監控 API
  - getStats()
  - healthCheck()
  - staffHealthCheck()

APIClient.visitor        // 訪客統計 API
  - getStats()
  - increment()
  - getTotal()
```

### 3. 示範模組 (`/frontend/modules/`)

#### `proofreading.js` - 校稿功能模組（✅ 已完成）
```javascript
// 導出的功能：
export function init()                // 初始化模組
export function clearProofreadChat()  // 清除對話
export function getSessionId()        // 獲取 session ID
```

---

## 📋 待完成的模組拆分

### 原始 admin.js 結構分析

| 模組 | 行數範圍 | 行數 | 主要功能 | 優先級 |
|------|---------|------|---------|--------|
| **Tab Switching** | 27-42 | 16 | 標籤切換 | 🔴 高 |
| **Document Management** | 44-605 | 562 | 文檔管理 | 🔴 高 |
| **Proofreading** | 607-775 | 169 | 校稿功能 | ✅ 完成 |
| **Content Generation** | 777-878 | 102 | 文案生成 | 🟡 中 |
| **Voice Generation** | 880-1113 | 234 | 語音生成 | 🟡 中 |
| **Video Generation** | 1115-1265 | 151 | 視頻生成 | 🟡 中 |
| **Data Monitoring** | 1267-1499 | 233 | 數據監控 | 🟢 低 |
| **Utilities** | 1501-1673 | 173 | 工具函數 | 🔴 高 |

---

## 🔨 模組拆分指南

### 模組拆分模板

每個模組應遵循以下結構：

```javascript
/**
 * [模組名稱] 模組
 * [模組功能描述]
 */

import { $, $$, addClass, removeClass, on } from '../utils/dom-helper.js';
import { showNotification, success, error } from '../utils/notification.js';
import APIClient from '../api/api-client.js';

// ==================== 模組狀態 ====================
let moduleState = {
    // 模組私有狀態
};

// ==================== 公開函數 ====================

/**
 * 初始化模組
 * @export
 */
export function init() {
    // 初始化邏輯
    bindEvents();
    loadInitialData();
    console.log('✅ [模組名稱] 已初始化');
}

/**
 * 綁定事件監聽器
 */
function bindEvents() {
    // 綁定 DOM 事件
}

/**
 * 載入初始數據
 */
async function loadInitialData() {
    // 載入數據
}

// ==================== 私有函數 ====================

// 其他輔助函數...

// ==================== 導出其他公開函數 ====================

export function somePublicFunction() {
    // 可以被外部調用的函數
}
```

---

## 📝 具體模組實作指南

### 1. Tab Manager (`tab-manager.js`) - 🔴 高優先級

**原始代碼**: 第 27-42 行
**功能**: 標籤切換管理

```javascript
/**
 * 標籤管理模組
 */
import { $$, addClass, removeClass } from '../utils/dom-helper.js';

export function init() {
    const navItems = $$('.nav-item');
    const tabContents = $$('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');

            navItems.forEach(nav => removeClass(nav, 'active'));
            tabContents.forEach(content => removeClass(content, 'active'));

            addClass(item, 'active');
            const targetTab = document.getElementById(tabId);
            if (targetTab) addClass(targetTab, 'active');
        });
    });

    console.log('✅ 標籤管理已初始化');
}
```

---

### 2. Document Manager (`document-manager.js`) - 🔴 高優先級

**原始代碼**: 第 44-605 行（562 行）
**功能**: 文檔上傳、列表、刪除、搜尋、排序

**建議子功能拆分**:
```javascript
// document-manager.js 主模組
export function init()
export function loadDocuments()
export function refreshList()

// 內部函數：
- uploadDocument()
- deleteDocument()
- searchDocuments()
- sortDocuments()
- groupByFolder()
- createDocumentItem()
```

**關鍵代碼位置**:
- 上傳處理: 第 306-355 行
- 列表載入: 第 67-125 行
- 刪除功能: 第 406-441 行
- 搜尋功能: 第 236-251 行
- 排序功能: 第 253-272 行

---

### 3. Content Generator (`content-generator.js`) - 🟡 中優先級

**原始代碼**: 第 777-878 行（102 行）
**功能**: 文案生成、複製、下載

```javascript
export function init()
export function generateContent()
export function copyDraft()
export function saveDraft()

// 內部函數：
- validateInput()
- displayResult()
- handleError()
```

---

### 4. Voice Generator (`voice-generator.js`) - 🟡 中優先級

**原始代碼**: 第 880-1113 行（234 行）
**功能**: 語音生成、播放、下載

```javascript
export function init()
export function generateVoice()
export function displayAudioPlayer()
export function saveAudio()

// 包含模態框管理：
- openAudioAddModal()
- closeAudioAddModal()
- saveAudioFile()
```

---

### 5. Video Generator (`video-generator.js`) - 🟡 中優先級

**原始代碼**: 第 1115-1265 行（151 行）
**功能**: 視頻生成、播放、下載

```javascript
export function init()
export function generateVideo()
export function displayVideoPlayer()
export function saveVideo()

// 內部函數：
- validateImagePath()
- handleProgress()
```

---

### 6. Data Monitor (`data-monitor.js`) - 🟢 低優先級

**原始代碼**: 第 1267-1499 行（233 行）
**功能**: 系統統計、訪客統計、健康檢查

```javascript
export function init()
export function refreshAnalytics()
export function loadVisitorStats()
export function loadSystemStats()

// 顯示函數：
- displayStats()
- displayVisitorChart()
```

---

## 🔄 重寫 admin.js 主文件

完成模組拆分後，`admin.js` 應該簡化為：

```javascript
/**
 * 幕僚管理系統主入口
 * 負責初始化所有功能模組
 */

import * as TabManager from './modules/tab-manager.js';
import * as DocumentManager from './modules/document-manager.js';
import * as Proofreading from './modules/proofreading.js';
import * as ContentGenerator from './modules/content-generator.js';
import * as VoiceGenerator from './modules/voice-generator.js';
import * as VideoGenerator from './modules/video-generator.js';
import * as DataMonitor from './modules/data-monitor.js';
import APIClient from './api/api-client.js';

// ==================== 應用初始化 ====================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 幕僚管理系統啟動中...');

    // 檢查 API 連接
    await checkAPIConnection();

    // 初始化所有模組
    TabManager.init();
    DocumentManager.init();
    Proofreading.init();
    ContentGenerator.init();
    VoiceGenerator.init();
    VideoGenerator.init();
    DataMonitor.init();

    // 初始化登出功能
    initLogout();

    console.log('✅ 所有模組已初始化');
});

/**
 * 檢查 API 連接
 */
async function checkAPIConnection() {
    try {
        const [publicHealth, staffHealth] = await Promise.all([
            APIClient.system.healthCheck(),
            APIClient.system.staffHealthCheck()
        ]);

        const allHealthy = publicHealth?.status === 'healthy' &&
                          staffHealth?.status === 'healthy';

        if (!allHealthy) {
            console.warn('⚠️ 部分 API 服務可能未啟動');
        } else {
            console.log('✅ API 連接正常');
        }
    } catch (error) {
        console.error('❌ API 連接測試失敗:', error);
    }
}

/**
 * 初始化登出功能
 */
function initLogout() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('確定要登出嗎？')) {
                localStorage.removeItem('staff_password');
                window.location.href = './';
            }
        });
    }
}
```

---

## 📄 更新 admin.html

需要更新 HTML 以支援 ES6 Modules：

```html
<!-- 移除舊的 script 標籤 -->
<!-- <script src="admin-api.js"></script> -->
<!-- <script src="admin.js"></script> -->

<!-- 使用新的模組化結構 -->
<script type="module" src="admin.js"></script>

<!-- 添加通知容器的 CSS -->
<style>
.notification-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.notification {
    min-width: 300px;
    padding: 16px;
    border-radius: 8px;
    background: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    align-items: center;
    gap: 12px;
    animation: slideIn 0.3s ease-out;
}

.notification-success { border-left: 4px solid #10b981; }
.notification-error { border-left: 4px solid #ef4444; }
.notification-warning { border-left: 4px solid #f59e0b; }
.notification-info { border-left: 4px solid #3b82f6; }

.notification-icon { font-size: 20px; }
.notification-text { flex: 1; }
.notification-close {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    color: #6b7280;
}

.notification-hide {
    animation: slideOut 0.3s ease-out forwards;
}

@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

@keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
}
</style>
```

---

## 🧪 測試檢查清單

完成重構後，請測試以下功能：

### 基礎功能
- [ ] 標籤切換正常
- [ ] 頁面載入無錯誤
- [ ] API 連接檢查正常

### 文檔管理
- [ ] 上傳文檔
- [ ] 顯示文檔列表
- [ ] 搜尋文檔
- [ ] 排序文檔
- [ ] 刪除文檔
- [ ] 下載文檔

### 校稿功能
- [ ] 發送校稿請求
- [ ] 接收 AI 回應
- [ ] 顯示參考來源
- [ ] 清除對話記憶

### 文案生成
- [ ] 生成文案
- [ ] 複製文案
- [ ] 下載文案

### 語音生成
- [ ] 生成語音
- [ ] 播放語音
- [ ] 下載語音

### 視頻生成
- [ ] 生成視頻
- [ ] 播放視頻
- [ ] 下載視頻

### 數據監控
- [ ] 顯示系統統計
- [ ] 顯示訪客統計
- [ ] 刷新數據

---

## 📈 重構進度追蹤

### 完成狀態

| 項目 | 狀態 | 行數 | 完成日期 |
|------|------|------|---------|
| **基礎設施** |  |  |  |
| ├─ DOM Helper | ✅ | 320 | 2025-11-19 |
| ├─ Notification | ✅ | 127 | 2025-11-19 |
| └─ API Client | ✅ | 457 | 2025-11-19 |
| **功能模組** |  |  |  |
| ├─ Tab Manager | ⏳ | ~20 | - |
| ├─ Document Manager | ⏳ | ~600 | - |
| ├─ Proofreading | ✅ | 230 | 2025-11-19 |
| ├─ Content Generator | ⏳ | ~150 | - |
| ├─ Voice Generator | ⏳ | ~250 | - |
| ├─ Video Generator | ⏳ | ~180 | - |
| └─ Data Monitor | ⏳ | ~250 | - |
| **主文件** |  |  |  |
| └─ admin.js 重寫 | ⏳ | ~50 | - |

**總進度**: 27% (1,134 / 4,200 行)

---

## 💡 重構最佳實踐

### 1. 保持向後兼容
- 使用命名導出保持舊函數名稱可用
- 漸進式重構，避免一次性大改

### 2. 錯誤處理
- 所有 API 調用都應有 try-catch
- 使用 notification.js 顯示錯誤訊息

### 3. 日誌記錄
- 模組初始化時輸出日誌
- 重要操作輸出日誌便於調試

### 4. 代碼風格
- 使用 ES6+ 語法 (const/let, 箭頭函數, 解構等)
- 函數命名清晰，遵循駝峰命名法
- 添加 JSDoc 註釋

### 5. 性能優化
- 避免重複的 DOM 查詢
- 使用事件委託處理動態元素
- 合理使用防抖/節流

---

## 🎯 下一步行動

### 立即執行（高優先級）
1. 創建 `tab-manager.js`
2. 拆分 `document-manager.js`（最大的模組）
3. 重寫 `admin.js` 主文件
4. 更新 `admin.html`
5. 測試基礎功能

### 後續執行（中優先級）
6. 拆分 `content-generator.js`
7. 拆分 `voice-generator.js`
8. 拆分 `video-generator.js`
9. 測試所有功能

### 最後執行（低優先級）
10. 拆分 `data-monitor.js`
11. 優化性能
12. 添加單元測試

---

## 📚 參考資源

- [ES6 Modules 文檔](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Guide/Modules)
- [JSDoc 註釋規範](https://jsdoc.app/)
- 已完成的示例模組: `frontend/modules/proofreading.js`

---

**Phase 2 重構指南**
**版本**: 1.0
**更新日期**: 2025-11-19
**狀態**: 🚧 進行中 (27% 完成)
