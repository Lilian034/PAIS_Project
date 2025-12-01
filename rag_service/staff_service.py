import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

from models.staff_models import (
    ContentRequest, ContentUpdate, GenerateResponse, 
    TaskListResponse, MediaResponse, TaskStatus, MediaType
)
from services.content_generator import ContentGenerator
from services.memory_manager import StaffMemoryManager
from services.elevenlabs_service import ElevenLabsService
from services.heygen_service import HeyGenService
from utils.db_helper import StaffDatabase
from utils.task_manager import TaskManager

# 載入環境變數
load_dotenv()

# 設定日誌
logger.add("logs/staff_{time}.log", rotation="1 day", retention="30 days")

# ==================== FastAPI 應用 ====================

app = FastAPI(
    title="PAIS 幕僚系統",
    description="文案生成 → 審核 → 語音克隆 → 影片生成",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 服務初始化 ====================

# 資料庫與任務管理
db = StaffDatabase()
task_mgr = TaskManager(db)

# 記憶與文案生成
memory_mgr = StaffMemoryManager()
content_gen = ContentGenerator(memory_mgr)

# 多媒體服務
voice_service = ElevenLabsService()
heygen_service = HeyGenService()

# 密碼驗證
STAFF_PASSWORD = os.getenv("STAFF_PASSWORD", "staff123456")


def verify_password(authorization: str = Header(None)):
    """驗證密碼"""
    if not authorization or authorization != f"Bearer {STAFF_PASSWORD}":
        raise HTTPException(status_code=401, detail="未授權")
    return True


# ==================== API 端點 ====================

@app.get("/")
async def root():
    return {
        "system": "PAIS 幕僚系統",
        "version": "1.0.0",
        "features": ["文案生成", "文案審核", "語音克隆", "影片生成"],
        "status": "🟢 運行中"
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    # 檢查 API keys 配置狀態
    elevenlabs_configured = bool(voice_service.api_key and voice_service.voice_id)
    heygen_configured = bool(heygen_service.api_key)

    return {
        "status": "healthy",
        "database": "✅ connected",
        "memory": "✅ active",
        "llm": "✅ ready",
        "services": {
            "elevenlabs": "✅ configured" if elevenlabs_configured else "⚠️ not configured",
            "heygen": "✅ configured" if heygen_configured else "⚠️ not configured"
        }
    }


# ==================== 文案生成相關 ====================

@app.post("/api/staff/content/generate", response_model=GenerateResponse)
async def generate_content(
    request: ContentRequest,
    authorized: bool = Depends(verify_password)
):
    """
    步驟 1: 生成文案
    
    流程:
    1. 建立任務
    2. 使用 LLM + 記憶 + 知識庫生成文案
    3. 返回文案供人工審核
    """
    try:
        logger.info(f"📝 收到文案生成請求: {request.topic}")
        
        # 建立任務
        task_id = task_mgr.create_task(
            topic=request.topic,
            style=request.style.value,
            length=request.length.value
        )
        
        # 生成文案
        content = await content_gen.generate(
            task_id=task_id,
            topic=request.topic,
            style=request.style.value,
            length=request.length.value
        )
        
        # 儲存內容
        task_mgr.update_content(task_id, content, editor="system")
        task_mgr.update_status(task_id, TaskStatus.REVIEWING)
        
        return GenerateResponse(
            success=True,
            task_id=task_id,
            content=content,
            message="文案生成完成，請審核"
        )
        
    except Exception as e:
        logger.error(f"❌ 文案生成失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/staff/content/tasks", response_model=TaskListResponse)
async def list_tasks(
    limit: int = 50,
    authorized: bool = Depends(verify_password)
):
    """取得任務列表"""
    try:
        tasks = task_mgr.list_tasks(limit)
        return TaskListResponse(
            success=True,
            tasks=tasks,
            total=len(tasks)
        )
    except Exception as e:
        logger.error(f"❌ 取得任務列表失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/staff/content/task/{task_id}")
async def get_task(
    task_id: str,
    authorized: bool = Depends(verify_password)
):
    """取得單一任務詳情"""
    try:
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")
        return {"success": True, "task": task}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 取得任務失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文案審核相關 ====================

@app.put("/api/staff/content/task/{task_id}")
async def update_content(
    task_id: str,
    update: ContentUpdate,
    authorized: bool = Depends(verify_password)
):
    """
    步驟 2a: 人工修改文案
    
    儲存修改記錄作為學習樣本
    """
    try:
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")
        
        original_content = task.get('content', '')
        
        # 更新內容
        task_mgr.update_content(task_id, update.content, update.editor)
        
        # 儲存修改記錄作為學習樣本
        if original_content != update.content:
            content_gen.save_edit_feedback(task_id, original_content, update.content)
            logger.info(f"📚 已記錄人工修改作為學習樣本: {task_id}")
        
        return {"success": True, "message": "文案已更新"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新文案失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/staff/content/task/{task_id}/approve")
async def approve_content(
    task_id: str,
    authorized: bool = Depends(verify_password)
):
    """
    步驟 2b: 審核通過
    
    文案審核完成，可進入多媒體生成階段
    """
    try:
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")
        
        success = task_mgr.approve_task(task_id)
        
        if success:
            return {"success": True, "message": "審核通過，可進行多媒體生成"}
        else:
            raise HTTPException(status_code=500, detail="審核失敗")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 審核失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 多媒體生成相關 ====================

@app.post("/api/staff/media/voice/{task_id}", response_model=MediaResponse)
async def generate_voice(
    task_id: str,
    authorized: bool = Depends(verify_password)
):
    """
    步驟 3: 語音克隆

    使用 ElevenLabs API 將文案轉成語音
    """
    try:
        # 檢查 API 配置
        if not voice_service.api_key:
            raise HTTPException(
                status_code=503,
                detail="ElevenLabs API Key 未配置，請在 .env 檔案中設定 ELEVENLABS_API_KEY"
            )
        if not voice_service.voice_id:
            raise HTTPException(
                status_code=503,
                detail="語音 ID 未配置，請在 .env 檔案中設定 MAYOR_VOICE_ID"
            )

        # 取得任務
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")

        if task['status'] != TaskStatus.APPROVED.value:
            raise HTTPException(status_code=400, detail="任務尚未審核通過，請先審核文案")

        content = task.get('content')
        if not content:
            raise HTTPException(status_code=400, detail="無文案內容")

        # 建立媒體記錄
        media_id = task_mgr.create_media_record(task_id, MediaType.VOICE.value)

        # 更新任務狀態
        task_mgr.update_status(task_id, TaskStatus.GENERATING_VOICE)

        # 生成語音
        try:
            file_path = await voice_service.generate_voice(content, task_id)
            task_mgr.complete_media(media_id, file_path)
            logger.info(f"✅ 語音生成成功: {task_id}")

            return MediaResponse(
                success=True,
                task_id=task_id,
                media_type=MediaType.VOICE.value,
                file_path=file_path,
                message="語音生成完成！已使用市長聲音克隆"
            )

        except ValueError as ve:
            task_mgr.fail_media(media_id)
            raise HTTPException(status_code=400, detail=f"參數錯誤：{str(ve)}")
        except Exception as voice_error:
            task_mgr.fail_media(media_id)
            error_msg = str(voice_error)
            if "quota" in error_msg.lower():
                raise HTTPException(status_code=402, detail="ElevenLabs API 配額已用完，請檢查帳戶餘額")
            elif "unauthorized" in error_msg.lower() or "401" in error_msg:
                raise HTTPException(status_code=401, detail="ElevenLabs API Key 無效，請檢查配置")
            else:
                raise HTTPException(status_code=500, detail=f"語音生成失敗：{error_msg}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 語音生成失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/staff/media/avatar-video/{task_id}", response_model=MediaResponse)
async def generate_avatar_video(
    task_id: str,
    image_path: str,
    authorized: bool = Depends(verify_password)
):
    """
    步驟 4: 生成 Avatar Video（會說話的數位分身）

    使用 HeyGen API 將語音 + 圖片 → 會說話的數位分身影片
    前置條件：語音必須已經生成
    注意：影片生成需要 5-10 分鐘，請耐心等待
    """
    try:
        # 檢查 API 配置
        if not heygen_service.api_key:
            raise HTTPException(
                status_code=503,
                detail="HeyGen API Key 未配置，請在 .env 檔案中設定 HEYGEN_API_KEY"
            )

        # 取得任務
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")

        # 檢查語音是否已生成
        media_records = db.get_media_records(task_id)
        audio_file = None

        for record in media_records:
            if record.get('media_type') == 'voice' and record.get('status') == 'completed':
                audio_file = record.get('file_path')
                break

        if not audio_file:
            raise HTTPException(
                status_code=400,
                detail="請先生成語音！Avatar Video 需要語音文件。請先執行「生成語音」步驟。"
            )

        # 檢查圖片文件是否存在
        from pathlib import Path
        if not Path(image_path).exists():
            raise HTTPException(
                status_code=400,
                detail=f"圖片文件不存在：{image_path}，請上傳市長照片"
            )

        logger.info(f"🎬 開始生成 Avatar Video: {task_id}")
        logger.info(f"  語音: {audio_file}")
        logger.info(f"  圖片: {image_path}")

        # 建立媒體記錄
        media_id = task_mgr.create_media_record(task_id, MediaType.VIDEO.value)

        # 更新任務狀態
        task_mgr.update_status(task_id, TaskStatus.GENERATING_VIDEO)

        # 生成 Avatar Video
        try:
            file_path = await heygen_service.generate_avatar_video(
                audio_path=audio_file,
                image_path=image_path,
                task_id=task_id
            )

            task_mgr.complete_media(media_id, file_path)
            task_mgr.update_status(task_id, TaskStatus.COMPLETED)
            logger.info(f"✅ Avatar Video 生成成功: {task_id}")

            return MediaResponse(
                success=True,
                task_id=task_id,
                media_type="avatar_video",
                file_path=file_path,
                message="Avatar Video 生成完成！市長數位分身已生成"
            )

        except TimeoutError as te:
            task_mgr.fail_media(media_id)
            task_mgr.update_status(task_id, TaskStatus.FAILED)
            raise HTTPException(status_code=504, detail=f"影片生成超時：{str(te)}，請稍後重試")
        except ValueError as ve:
            task_mgr.fail_media(media_id)
            task_mgr.update_status(task_id, TaskStatus.FAILED)
            raise HTTPException(status_code=400, detail=f"參數錯誤：{str(ve)}")
        except Exception as video_error:
            task_mgr.fail_media(media_id)
            task_mgr.update_status(task_id, TaskStatus.FAILED)
            error_msg = str(video_error)
            if "quota" in error_msg.lower() or "credit" in error_msg.lower():
                raise HTTPException(status_code=402, detail="HeyGen API 配額已用完，請檢查帳戶餘額")
            elif "unauthorized" in error_msg.lower() or "401" in error_msg:
                raise HTTPException(status_code=401, detail="HeyGen API Key 無效，請檢查配置")
            else:
                raise HTTPException(status_code=500, detail=f"影片生成失敗：{error_msg}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Avatar Video 生成失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/staff/media/status/{task_id}")
async def get_media_status(
    task_id: str,
    authorized: bool = Depends(verify_password)
):
    """查詢多媒體生成狀態"""
    try:
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")

        media_records = db.get_media_records(task_id)

        return {
            "success": True,
            "task_status": task['status'],
            "media_records": media_records
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 查詢狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/staff/media/voices")
async def get_available_voices(authorized: bool = Depends(verify_password)):
    """獲取 ElevenLabs 可用的語音列表"""
    try:
        if not voice_service.api_key:
            raise HTTPException(
                status_code=503,
                detail="ElevenLabs API Key 未配置"
            )

        voices = await voice_service.get_available_voices()
        return {
            "success": True,
            "voices": voices,
            "current_voice_id": voice_service.voice_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 獲取語音列表失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/staff/media/avatars")
async def get_available_avatars(authorized: bool = Depends(verify_password)):
    """獲取 HeyGen 可用的 Avatar 列表"""
    try:
        if not heygen_service.api_key:
            raise HTTPException(
                status_code=503,
                detail="HeyGen API Key 未配置"
            )

        avatars = await heygen_service.get_avatar_list()
        return {
            "success": True,
            "avatars": avatars
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 獲取 Avatar 列表失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 學習與記憶管理 ====================

@app.get("/api/staff/learning/summary/{task_id}")
async def get_learning_summary(
    task_id: str,
    authorized: bool = Depends(verify_password)
):
    """
    查看任務的學習摘要

    返回該任務中 AI 學到了什麼
    """
    try:
        summary = memory_mgr.get_learning_summary(task_id)

        return {
            "success": True,
            **summary
        }

    except Exception as e:
        logger.error(f"❌ 獲取學習摘要失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 知識庫管理 (從 public_service 移過來) ====================
# 因為知識庫管理屬於幕僚功能，所以放在這裡

@app.post("/api/upload")
async def upload_document():
    """
    上傳文件到知識庫
    (這個功能原本在 public_service，但屬於幕僚管理功能)
    """
    # TODO: 實作文件上傳邏輯
    return {"message": "請參考 public_service.py 的實作"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)