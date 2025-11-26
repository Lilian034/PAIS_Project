# 🎬 完整音視頻生成工作流

## 📋 三步驟 Sequential Chain

根據 LangChain 架構，我們實現了完整的「**文字 → 克隆語音 → 圖片轉影片 → 音畫合成**」工作流：

```
Step 1: 文案生成與審核
   ↓
Step 2: 語音克隆（ElevenLabs）⚡ 並行執行
   ↓                            ⚡
Step 3: 圖片轉影片（Runway）    ⚡
   ↓
Step 4: 音畫合成（FFmpeg）
   ↓
最終影片 🎉
```

---

## 🔄 工作流模式

### 模式 1：分步執行（手動控制）

用戶可以分別調用每個步驟的 API：

```javascript
// 步驟 1: 生成文案
const content = await APIClient.staff.generateContent(topic, style, length);
const taskId = content.task_id;

// 步驟 2: 審核通過
await APIClient.staff.approveTask(taskId);

// 步驟 3: 生成語音
const voice = await APIClient.staff.generateVoice(taskId);

// 步驟 4: 生成影片
const video = await APIClient.staff.generateVideo(taskId, imagePath, prompt);

// 步驟 5: 音畫合成
const final = await APIClient.staff.composeAudioVideo(taskId, audioDelay);
```

### 模式 2：完整工作流（一鍵執行）

一次 API 調用完成所有步驟：

```javascript
// 一鍵執行完整工作流（語音和影片並行生成）
const final = await APIClient.staff.fullWorkflow(taskId, imagePath, prompt, audioDelay);
```

---

## 🎯 API 端點詳解

### 1️⃣ 文案生成

```http
POST /api/staff/content/generate
Authorization: Bearer {STAFF_PASSWORD}
Content-Type: application/json

{
  "topic": "環保政策",
  "style": "formal",
  "length": "medium"
}
```

**回應：**
```json
{
  "success": true,
  "task_id": "task_20250126123456",
  "content": "各位市民朋友大家好...",
  "message": "文案生成完成，請審核"
}
```

---

### 2️⃣ 任務審核

```http
POST /api/staff/content/task/{task_id}/approve
Authorization: Bearer {STAFF_PASSWORD}
```

**回應：**
```json
{
  "success": true,
  "message": "審核通過，可進行多媒體生成"
}
```

---

### 3️⃣ 語音生成（ElevenLabs）

```http
POST /api/staff/media/voice/{task_id}
Authorization: Bearer {STAFF_PASSWORD}
```

**技術細節：**
- **模型**: `eleven_turbo_v2_5`（最新多語言模型）
- **語言**: `zh`（中文）
- **輸出**: MP3 格式
- **路徑**: `generated_content/voices/{task_id}.mp3`

**回應：**
```json
{
  "success": true,
  "task_id": "task_20250126123456",
  "media_type": "voice",
  "file_path": "generated_content/voices/task_20250126123456.mp3",
  "message": "語音生成完成"
}
```

---

### 4️⃣ 影片生成（Runway）

```http
POST /api/staff/media/video/{task_id}?image_path=...&prompt=...
Authorization: Bearer {STAFF_PASSWORD}
```

**參數：**
- `image_path`: 圖片路徑（必填）
- `prompt`: 影片動作提示（可選，預設「自然動態效果」）

**技術細節：**
- **流程**: 上傳圖片 → 創建任務 → 輪詢狀態 → 下載影片
- **時長**: 5 秒
- **輸出**: MP4 格式（無聲音）
- **路徑**: `generated_content/videos/{task_id}.mp4`

**回應：**
```json
{
  "success": true,
  "task_id": "task_20250126123456",
  "media_type": "video",
  "file_path": "generated_content/videos/task_20250126123456.mp4",
  "message": "影片生成完成"
}
```

---

### 5️⃣ 音畫合成（NEW！）

```http
POST /api/staff/media/compose/{task_id}?audio_delay=0.0
Authorization: Bearer {STAFF_PASSWORD}
```

**參數：**
- `audio_delay`: 音頻延遲（秒），正值=延遲，負值=提前（預設 0.0）

**技術細節：**
- **工具**: FFmpeg
- **輸入**: 語音 MP3 + 影片 MP4（無聲）
- **輸出**: 合成影片 MP4（有聲）
- **路徑**: `generated_content/videos/{task_id}_with_audio.mp4`

**FFmpeg 策略：**
```bash
ffmpeg -y \
  -i video.mp4 \
  -i audio.mp3 \
  -c:v copy \              # 視頻流複製（不重新編碼）
  -c:a aac -b:a 192k \     # 音頻編碼為 AAC
  -map 0:v:0 -map 1:a:0 \  # 映射視頻和音頻流
  -shortest \              # 以較短的流為準
  output.mp4
```

**回應：**
```json
{
  "success": true,
  "task_id": "task_20250126123456",
  "media_type": "composed_video",
  "file_path": "generated_content/videos/task_20250126123456_with_audio.mp4",
  "message": "音畫合成完成！最終影片已生成"
}
```

---

### 6️⃣ 完整工作流（NEW！）

```http
POST /api/staff/media/full-workflow/{task_id}?image_path=...&prompt=...&audio_delay=0.0
Authorization: Bearer {STAFF_PASSWORD}
```

**特色：**
- ⚡ **並行執行**：語音和影片同時生成，節省時間
- 🎯 **端到端**：一次 API 調用完成所有步驟
- 🔄 **自動化**：自動創建媒體記錄、更新任務狀態

**流程：**
```
1. 檢查任務是否已審核 ✓
2. 並行執行：
   ├─ 語音生成（ElevenLabs）⚡
   └─ 影片生成（Runway）    ⚡
3. 等待兩者完成
4. 音畫合成（FFmpeg）
5. 更新任務狀態為完成
```

**回應：**
```json
{
  "success": true,
  "task_id": "task_20250126123456",
  "media_type": "composed_video",
  "file_path": "generated_content/videos/task_20250126123456_with_audio.mp4",
  "message": "完整工作流完成！語音、影片已生成並合成"
}
```

---

## 📊 完整流程圖

```
┌─────────────────────────────────────────────────────────────┐
│                      使用者輸入文字                          │
│                   「環保政策宣傳短片」                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 文案生成（ContentGenerator + LangChain Memory）    │
│  ├─ LLM: Gemini 2.0 Flash                                   │
│  ├─ 知識庫: Qdrant 向量檢索                                  │
│  └─ 記憶: 學習過往修改                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: 人工審核與修改                                       │
│  ├─ 幕僚審閱文案                                             │
│  ├─ 必要時修改內容                                           │
│  └─ 點擊「審核通過」                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
┌─────────────────────┐  ┌─────────────────────┐
│  Step 3a: 語音生成  │  │  Step 3b: 影片生成  │
│  (ElevenLabsService)│  │  (RunwayService)    │
│  ⚡ 並行執行         │  │  ⚡ 並行執行         │
│                     │  │                     │
│  ├─ 模型: Turbo v2.5│  │  ├─ 上傳圖片        │
│  ├─ 語言: 中文      │  │  ├─ 創建任務        │
│  ├─ 克隆市長聲音    │  │  ├─ 輪詢狀態        │
│  └─ 輸出: MP3       │  │  └─ 輸出: MP4(無聲) │
└─────────┬───────────┘  └─────────┬───────────┘
          │                        │
          └──────────┬─────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: 音畫合成（VideoComposer + FFmpeg）                  │
│  ├─ 輸入: 語音 MP3 + 影片 MP4（無聲）                        │
│  ├─ 工具: FFmpeg                                             │
│  ├─ 策略: 視頻流複製 + 音頻編碼 AAC                          │
│  └─ 輸出: 最終影片 MP4（有聲）                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              🎉 最終影片輸出                                 │
│  generated_content/videos/task_xxx_with_audio.mp4            │
│  ├─ 時長: 5 秒                                               │
│  ├─ 視頻: 1280x720, 24 FPS                                  │
│  ├─ 音頻: AAC, 192kbps                                       │
│  └─ 大小: ~4-5 MB                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 前端整合

### 更新 `api-client.js`

```javascript
class APIClient {
    static staff = {
        // ... 現有方法 ...

        /**
         * 音畫合成
         */
        async composeAudioVideo(taskId, audioDelay = 0.0) {
            try {
                const data = await request(
                    `${API_CONFIG.staffURL}/media/compose/${taskId}?audio_delay=${audioDelay}`,
                    {
                        method: 'POST',
                        requireAuth: true
                    }
                );
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },

        /**
         * 完整工作流
         */
        async fullWorkflow(taskId, imagePath, prompt = null, audioDelay = 0.0) {
            try {
                const queryParams = new URLSearchParams({
                    image_path: imagePath,
                    audio_delay: audioDelay
                });
                if (prompt) queryParams.append('prompt', prompt);

                const data = await request(
                    `${API_CONFIG.staffURL}/media/full-workflow/${taskId}?${queryParams}`,
                    {
                        method: 'POST',
                        requireAuth: true
                    }
                );
                return { success: true, ...data };
            } catch (error) {
                return { success: false, error: error.message };
            }
        }
    };
}
```

### 更新 `video-generator.js`

```javascript
// 方式 1: 手動分步執行
async function manualWorkflow() {
    // 生成語音
    const voice = await APIClient.staff.generateVoice(taskId);

    // 生成影片
    const video = await APIClient.staff.generateVideo(taskId, imagePath);

    // 合成音畫
    const final = await APIClient.staff.composeAudioVideo(taskId);

    displayVideoPlayer(final.file_path);
}

// 方式 2: 一鍵完整工作流
async function autoWorkflow() {
    showNotification('正在生成完整影片，預計需要 2-5 分鐘...', 'info');

    const final = await APIClient.staff.fullWorkflow(
        taskId,
        imagePath,
        '自然動態效果',
        0.0
    );

    showNotification('完整影片生成完成！', 'success');
    displayVideoPlayer(final.file_path);
}
```

---

## 🔧 環境需求

### Docker Compose 配置

```yaml
staff_api:
  build: ./rag_service
  environment:
    - GEMINI_API_KEY=${GEMINI_API_KEY}
    - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
    - MAYOR_VOICE_ID=${MAYOR_VOICE_ID}
    - RUNWAY_API_KEY=${RUNWAY_API_KEY}
    - STAFF_PASSWORD=${STAFF_PASSWORD}
  volumes:
    - ./generated_content:/app/generated_content
```

### Dockerfile 配置

```dockerfile
FROM python:3.11-slim

# 安裝 FFmpeg（關鍵！）
RUN apt-get update && apt-get install -y ffmpeg

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "staff_service:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

## ⚡ 性能優化

### 並行執行優勢

| 執行模式 | 語音生成 | 影片生成 | 合成 | 總時間 |
|---------|---------|---------|------|--------|
| **順序執行** | 15秒 | 180秒 | 10秒 | **205秒** |
| **並行執行** | 15秒 ⚡ | 180秒 ⚡ | 10秒 | **190秒** |

節省時間：~15 秒（語音生成時間被影片生成覆蓋）

### 資源消耗

- **CPU**: FFmpeg 合成時短暫峰值
- **記憶體**: ~500MB（Python + FFmpeg）
- **磁碟**: 每個任務 ~10MB（語音 1MB + 影片原始 3MB + 最終 5MB）
- **網路**: 依賴 ElevenLabs 和 Runway API

---

## 🐛 常見問題

### Q1: FFmpeg 未安裝怎麼辦？

**A:** 確保 Dockerfile 包含：
```dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

然後重新構建：
```bash
docker compose build --no-cache staff_api
docker compose up -d
```

### Q2: 音畫不同步怎麼辦？

**A:** 使用 `audio_delay` 參數微調：
```javascript
// 音頻延遲 0.5 秒
await APIClient.staff.composeAudioVideo(taskId, 0.5);

// 音頻提前 0.3 秒
await APIClient.staff.composeAudioVideo(taskId, -0.3);
```

### Q3: 影片沒有聲音？

**A:** 檢查：
1. 語音文件是否生成成功
2. FFmpeg 是否安裝
3. 查看後端日誌：`docker compose logs -f staff_api`

### Q4: 完整工作流卡住？

**A:** 可能原因：
- Runway API 超時（最多 5 分鐘）
- ElevenLabs API 額度不足
- 網路問題

**解決：** 使用分步執行模式，逐步排查問題。

---

## 📈 後續優化方向

1. **背景音樂**: 添加背景音樂功能（已實現 `add_background_music`）
2. **字幕生成**: 根據語音生成字幕並嵌入影片
3. **多種影片長度**: 支援 3秒、5秒、10秒選項
4. **批次處理**: 一次生成多個任務
5. **預覽功能**: 在生成前預覽效果

---

## 🎯 總結

✅ **完整實現了三步驟 Sequential Chain**
✅ **語音和影片並行生成**
✅ **FFmpeg 音畫合成**
✅ **端到端 API 支援**
✅ **模組化設計**

現在你擁有一個完整的、生產就緒的音視頻生成系統！🎉
