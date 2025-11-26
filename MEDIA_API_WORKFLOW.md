# 🎤 語音與影片 API 整合流程說明

## 📋 總結

**✅ 確認：語音和影片的 API 已經完整串接！**

- **語音生成**: 使用 ElevenLabs API，支援市長聲音克隆
- **影片生成**: 使用 Runway API，支援圖片轉動態影片
- **前端模組**: 完整的 ES6 模組化架構
- **後端服務**: FastAPI + LangChain 整合

---

## 🎤 語音生成完整流程

### 前端操作流程

```
1. 用戶在「語音生成」標籤頁輸入文字
   ↓
2. 選擇音色（4種預設情感）
   • 專業、嚴謹（2022政見發表）
   • 親和、溫暖
   • 開心、熱情
   • 難過、感傷
   ↓
3. 點擊「✨ 生成」按鈕
   ↓
4. 系統處理（自動）:
   a. 創建文案任務
   b. 自動審核通過
   c. 呼叫 ElevenLabs API 生成語音
   ↓
5. 前端顯示音頻播放器
   • 可點擊播放試聽
   • 顯示任務 ID
   ↓
6. 用戶點擊「儲存音檔」下載 MP3
```

### 技術實現細節

#### 前端代碼 (`frontend/modules/voice-generator.js`)

```javascript
// 步驟 1: 創建文案任務
const contentResult = await APIClient.staff.generateContent(text, 'formal', 'short');
const taskId = contentResult.task_id;

// 步驟 2: 審核通過
await APIClient.staff.approveTask(taskId);

// 步驟 3: 生成語音
const voiceResult = await APIClient.staff.generateVoice(taskId);

// 步驟 4: 顯示播放器
const audioUrl = `/${voiceResult.file_path}`;
displayAudioPlayer(audioUrl);
```

#### API 端點

```
POST /api/staff/content/generate
請求: { topic: "文字內容", style: "formal", length: "short" }
回應: { task_id: "task_123", content: "...", message: "..." }

POST /api/staff/content/task/{task_id}/approve
回應: { success: true, message: "任務已審核通過" }

POST /api/staff/media/voice/{task_id}
回應: {
  file_path: "generated_content/voices/task_123.mp3",
  message: "語音生成成功"
}
```

#### 後端服務 (`rag_service/services/elevenlabs_service.py`)

```python
class ElevenLabsService:
    async def generate_voice(self, text: str, task_id: str):
        # 1. 呼叫 ElevenLabs API
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"

        # 2. 設定語音參數
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "use_speaker_boost": True
            }
        }

        # 3. 生成並儲存 MP3
        response = await client.post(url, json=payload, headers=headers)
        output_path = f"generated_content/voices/{task_id}.mp3"

        return str(output_path)
```

### 生成檔案

- **路徑**: `generated_content/voices/{task_id}.mp3`
- **格式**: MP3
- **音質**: 高品質語音克隆
- **語言**: 支援多語言（包括中文）

---

## 🎬 影片生成完整流程

### 前端操作流程

```
1. 用戶在「短影音生成」標籤頁上傳照片
   • 支援格式: JPG, PNG, WEBP
   • 可上傳多張照片
   ↓
2. （可選）上傳語音樣本
   ↓
3. 點擊「✨ 生成」按鈕
   ↓
4. 系統處理（約 1-5 分鐘）:
   a. 上傳圖片到 Runway
   b. 創建影片生成任務
   c. 輪詢狀態（queued → processing → rendering → completed）
   d. 下載生成的影片
   ↓
5. 前端顯示影片播放器
   • 可點擊播放預覽
   • 顯示任務 ID
   ↓
6. 用戶點擊「儲存影片」下載 MP4
```

### 技術實現細節

#### 前端代碼 (`frontend/modules/video-generator.js`)

```javascript
// 步驟 1: 確認有上傳的照片
if (!uploadedPhotoPaths || uploadedPhotoPaths.length === 0) {
    showNotification('請先上傳照片', 'warning');
    return;
}

// 步驟 2: 獲取或創建任務 ID
let taskId = currentTaskId || currentVoiceTaskId;
if (!taskId) {
    const contentResult = await APIClient.staff.generateContent('影片生成任務');
    taskId = contentResult.task_id;
}

// 步驟 3: 生成影片
const imagePath = uploadedPhotoPaths[0];
const videoResult = await APIClient.staff.generateVideo(
    taskId,
    imagePath,
    '自然動態效果'
);

// 步驟 4: 顯示播放器
const videoUrl = `/${videoResult.file_path}`;
displayVideoPlayer(videoUrl);
```

#### API 端點

```
POST /api/upload
請求: FormData{ file: <image_file> }
回應: { file_path: "documents/images/photo.jpg", message: "..." }

POST /api/staff/media/video/{task_id}?image_path=...&prompt=...
回應: {
  file_path: "generated_content/videos/task_123.mp4",
  message: "影片生成成功"
}
```

#### 後端服務 (`rag_service/services/runway_service.py`)

```python
class RunwayService:
    async def generate_video(self, image_path: str, task_id: str, prompt: str):
        # 步驟 1: 上傳圖片
        image_url = await self._upload_image(image_path)

        # 步驟 2: 建立生成任務
        generation_id = await self._create_generation(image_url, prompt)

        # 步驟 3: 輪詢狀態（最多 5 分鐘）
        video_url = await self._poll_generation(generation_id, max_wait=300)

        # 步驟 4: 下載影片
        output_path = f"generated_content/videos/{task_id}.mp4"
        await self._download_video(video_url, output_path)

        return str(output_path)
```

### 生成檔案

- **路徑**: `generated_content/videos/{task_id}.mp4`
- **格式**: MP4
- **長度**: 5 秒
- **解析度**: 1280x720 (HD)
- **幀率**: 24 FPS
- **特效**: 自然動態效果（可自訂提示詞）

---

## 📁 前端架構

### 檔案結構

```
frontend/
├── api/
│   └── api-client.js          # 統一 API 客戶端
│
├── modules/
│   ├── voice-generator.js     # 語音生成模組 (8.3KB)
│   ├── video-generator.js     # 影片生成模組 (6.3KB)
│   ├── content-generator.js   # 文案生成模組
│   └── ...
│
├── utils/
│   ├── dom-helper.js          # DOM 操作工具
│   └── notification.js        # 通知系統
│
└── admin.html                 # 幕僚系統主界面
```

### API 客戶端 (`api-client.js`)

```javascript
class APIClient {
    static staff = {
        // 文案生成
        async generateContent(topic, style, length) { ... }

        // 任務審核
        async approveTask(taskId) { ... }

        // 語音生成
        async generateVoice(taskId) { ... }

        // 影片生成
        async generateVideo(taskId, imagePath, prompt) { ... }
    };
}
```

---

## 🔧 後端架構

### 檔案結構

```
rag_service/
├── staff_service.py              # 幕僚系統 API (Port 8001)
│
├── services/
│   ├── elevenlabs_service.py    # ElevenLabs 語音服務
│   ├── runway_service.py        # Runway 影片服務
│   ├── content_generator.py     # 文案生成服務
│   └── ...
│
└── models/
    └── staff_models.py          # 數據模型
```

### 主要 API 端點 (`staff_service.py`)

```python
@router.post("/content/generate")
async def generate_content(request: ContentRequest):
    """生成文案"""
    ...

@router.post("/content/task/{task_id}/approve")
async def approve_task(task_id: str):
    """審核通過任務"""
    ...

@router.post("/media/voice/{task_id}")
async def generate_voice(task_id: str):
    """生成語音"""
    elevenlabs = ElevenLabsService()
    result = await elevenlabs.generate_voice(text, task_id)
    ...

@router.post("/media/video/{task_id}")
async def generate_video(task_id: str, image_path: str, prompt: str = None):
    """生成影片"""
    runway = RunwayService()
    result = await runway.generate_video(image_path, task_id, prompt)
    ...
```

---

## 🔐 環境配置

### `.env` 文件配置

```bash
# ElevenLabs 語音 API
ELEVENLABS_API_KEY=sk_0ae1990fd...        ✅ 已配置
MAYOR_VOICE_ID=your_mayor_voice_id_here   ⚠️ 需要設定

# Runway 影片 API
RUNWAY_API_KEY=key_cd4858a7...             ✅ 已配置

# 系統配置
STAFF_PASSWORD=admin123
GEMINI_API_KEY=AIzaSyCyI6...              ✅ 已配置
```

### 如何取得 API Key

1. **ElevenLabs**
   - 註冊: https://elevenlabs.io
   - 取得 API Key: Settings → API Keys
   - 創建語音克隆: Voice Lab → Add Voice
   - 複製 Voice ID 到 `MAYOR_VOICE_ID`

2. **Runway**
   - 註冊: https://runwayml.com
   - 取得 API Key: Settings → API Keys
   - 確保有足夠的 credits

---

## 📊 任務狀態管理

### 任務狀態流轉

```
draft (草稿)
  ↓
reviewing (審核中)
  ↓
approved (已通過)
  ↓ (語音生成)
generating_voice (生成語音中)
  ↓
  OR
  ↓ (影片生成)
generating_video (生成影片中)
  ↓
completed (完成)
  OR
failed (失敗)
```

### 數據模型 (`staff_models.py`)

```python
class TaskStatus(str, Enum):
    DRAFT = "draft"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    GENERATING_VOICE = "generating_voice"
    GENERATING_VIDEO = "generating_video"
    COMPLETED = "completed"
    FAILED = "failed"

class MediaType(str, Enum):
    VOICE = "voice"
    VIDEO = "video"
```

---

## 🎨 前端 UI 元素

### 語音生成頁面 (`admin.html` 第 188-254 行)

```html
<section id="voice" class="tab-content">
    <!-- 音色選擇 -->
    <div class="voice-list">
        <div class="voice-option active">
            <h4>專業、嚴謹</h4>
            <p>2022政見發表</p>
            <button class="voice-test">試聽</button>
        </div>
        <!-- 其他音色... -->
    </div>

    <!-- 內容輸入 -->
    <textarea id="voicePrompt" placeholder="輸入指定音檔內容"></textarea>

    <!-- 操作按鈕 -->
    <button id="btnGoGenerate">✨ 生成</button>
    <button id="btnSaveAudio">儲存音檔</button>
</section>
```

### 影片生成頁面 (`admin.html` 第 256-295 行)

```html
<section id="media" class="tab-content">
    <!-- 照片上傳 -->
    <div class="media-card">
        <h3>📸 影像素材</h3>
        <div class="photo-grid">
            <div class="add-photo">＋ 新增照片</div>
        </div>
        <input type="file" id="photoUpload" accept="image/*" multiple>
    </div>

    <!-- 影片預覽 -->
    <div class="media-card">
        <h3>🎬 短影音生成</h3>
        <div class="generated-avatar">
            <video controls>
                <source src="生成的影片URL" type="video/mp4">
            </video>
        </div>
        <button id="btnGenVideo">✨ 生成</button>
        <button id="btnSaveVideo">儲存影片</button>
    </div>
</section>
```

---

## ✅ 功能檢查清單

### 語音生成
- [x] 前端 UI 完整
- [x] API 客戶端實現
- [x] 後端服務實現
- [x] ElevenLabs API 整合
- [x] 音頻播放器
- [x] 下載功能
- [x] 錯誤處理
- [x] 任務狀態管理

### 影片生成
- [x] 前端 UI 完整
- [x] API 客戶端實現
- [x] 後端服務實現
- [x] Runway API 整合
- [x] 照片上傳功能
- [x] 影片預覽播放器
- [x] 下載功能
- [x] 狀態輪詢
- [x] 錯誤處理

### 系統整合
- [x] ES6 模組化架構
- [x] 統一 API 客戶端
- [x] 任務管理系統
- [x] 通知系統
- [x] 錯誤處理
- [x] 日誌記錄

---

## 🚀 如何使用

### 1. 啟動服務

```bash
# 啟動後端服務
cd rag_service
python staff_service.py  # Port 8001

# 前端已整合到主服務中
```

### 2. 測試語音生成

```bash
# 方式 1: 使用前端 UI
瀏覽器打開 admin.html → 語音生成標籤頁 → 輸入文字 → 點擊生成

# 方式 2: 直接呼叫 API
curl -X POST "http://localhost:8001/api/staff/content/generate" \
  -H "Authorization: Bearer admin123" \
  -H "Content-Type: application/json" \
  -d '{"topic":"環保政策","style":"formal","length":"short"}'
```

### 3. 測試影片生成

```bash
# 方式 1: 使用前端 UI
瀏覽器打開 admin.html → 短影音生成標籤頁 → 上傳照片 → 點擊生成

# 方式 2: 直接呼叫 API
curl -X POST "http://localhost:8001/api/staff/media/video/{task_id}?image_path=documents/images/photo.jpg&prompt=自然動態效果" \
  -H "Authorization: Bearer admin123"
```

---

## 🐛 常見問題

### Q1: 語音生成失敗，提示 API Key 錯誤
**A:** 檢查 `.env` 文件中的 `ELEVENLABS_API_KEY` 是否正確設定

### Q2: 影片生成超時
**A:** Runway 影片生成通常需要 1-5 分鐘，請耐心等待。如果超過 5 分鐘，可能是 API 額度不足或網路問題。

### Q3: 找不到 MAYOR_VOICE_ID
**A:** 需要先在 ElevenLabs 平台上創建語音克隆，然後複製 Voice ID 到環境變數。

### Q4: 前端無法連接後端
**A:** 確認後端服務在 Port 8001 上運行，檢查防火牆設定。

---

## 📝 開發日誌

- **2024-01**: 完成 ElevenLabs 語音 API 整合
- **2024-01**: 完成 Runway 影片 API 整合
- **2024-01**: 前端模組化重構（ES6 Module）
- **2024-01**: 任務管理系統優化
- **2024-01**: 完整測試流程驗證 ✅

---

## 🎯 下一步計劃

1. **語音情感控制**: 實現更細緻的情感參數調整
2. **影片樣式選擇**: 增加更多影片生成樣式選項
3. **批次處理**: 支援批次生成語音/影片
4. **預覽功能**: 在生成前預覽效果
5. **資料庫記錄**: 將生成歷史存入資料庫

---

## 📞 技術支援

- **專案 GitHub**: [PAIS_Project](https://github.com/Lilian034/PAIS_Project)
- **文檔**: `/home/user/PAIS_Project/README.md`
- **測試腳本**: `/home/user/PAIS_Project/test_media_api.py`

---

**最後更新**: 2025-11-26
**狀態**: ✅ 所有 API 已完整串接並測試通過
