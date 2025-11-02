"""
PAIS 幕僚系統 API
遵循 KISS、YAGNI、SOLID 原則
專注於文案生成工作流程：生成 → 審核 → 語音 → 影片
"""
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
from services.runway_service import RunwayService
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
video_service = RunwayService()

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
    return {
        "status": "healthy",
        "database": "✅ connected",
        "memory": "✅ active",
        "llm": "✅ ready"
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
        # 取得任務
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")
        
        if task['status'] != TaskStatus.APPROVED.value:
            raise HTTPException(status_code=400, detail="任務尚未審核通過")
        
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
                message="語音生成完成"
            )
            
        except Exception as voice_error:
            task_mgr.fail_media(media_id)
            raise voice_error
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 語音生成失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/staff/media/video/{task_id}", response_model=MediaResponse)
async def generate_video(
    task_id: str,
    image_path: str,
    prompt: str = None,
    authorized: bool = Depends(verify_password)
):
    """
    步驟 4: 圖片轉影片
    
    使用 Runway API 將圖片轉成影片
    """
    try:
        # 取得任務
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")
        
        # 建立媒體記錄
        media_id = task_mgr.create_media_record(task_id, MediaType.VIDEO.value)
        
        # 更新任務狀態
        task_mgr.update_status(task_id, TaskStatus.GENERATING_VIDEO)
        
        # 生成影片
        try:
            file_path = await video_service.generate_video(
                image_path=image_path,
                task_id=task_id,
                prompt=prompt
            )
            
            task_mgr.complete_media(media_id, file_path)
            task_mgr.update_status(task_id, TaskStatus.COMPLETED)
            logger.info(f"✅ 影片生成成功: {task_id}")
            
            return MediaResponse(
                success=True,
                task_id=task_id,
                media_type=MediaType.VIDEO.value,
                file_path=file_path,
                message="影片生成完成，所有流程結束"
            )
            
        except Exception as video_error:
            task_mgr.fail_media(media_id)
            raise video_error
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 影片生成失敗: {e}")
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