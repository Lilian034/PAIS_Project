import os
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form, BackgroundTasks
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

load_dotenv()
logger.add("logs/staff_{time}.log", rotation="1 day", retention="30 days")

app = FastAPI(title="PAIS Staff API", version="2.5.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
db = StaffDatabase()
task_mgr = TaskManager(db)
memory_mgr = StaffMemoryManager()
content_gen = ContentGenerator(memory_mgr)
voice_service = ElevenLabsService()
heygen_service = HeyGenService()

STAFF_PASSWORD = os.getenv("STAFF_PASSWORD", "staff123456")
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8000")

def verify_password(authorization: str = Header(None)):
    if not authorization or authorization != f"Bearer {STAFF_PASSWORD}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ngrok_url": SERVER_BASE_URL,
        "services": {
            "elevenlabs": bool(voice_service.api_key),
            "heygen": bool(heygen_service.api_key)
        }
    }

# --- Content Generation ---

@app.post("/api/staff/content/generate", response_model=GenerateResponse)
async def generate_content(req: ContentRequest, auth: bool = Depends(verify_password)):
    """AI 生成模式：這是給「文宣生成」用的，會潤色"""
    try:
        task_id = task_mgr.create_task(req.topic, req.style.value, req.length.value)
        content = await content_gen.generate(task_id, req.topic, req.style.value, req.length.value)
        task_mgr.update_content(task_id, content)
        task_mgr.update_status(task_id, TaskStatus.REVIEWING)
        return {"success": True, "task_id": task_id, "content": content, "message": "Generated"}
    except Exception as e:
        logger.error(f"Gen Error: {e}")
        raise HTTPException(500, str(e))

@app.post("/api/staff/content/direct", response_model=GenerateResponse)
async def create_direct_content(req: ContentRequest, auth: bool = Depends(verify_password)):
    """
    【新增】直接輸入模式：這是給「語音生成」用的
    功能：跳過 AI，直接儲存用戶輸入的文字，確保照稿念
    """
    try:
        topic_preview = req.topic[:20] + ("..." if len(req.topic) > 20 else "")
        task_id = task_mgr.create_task(topic_preview, req.style.value, req.length.value)
        content = req.topic
        task_mgr.update_content(task_id, content, editor="user")
        task_mgr.update_status(task_id, TaskStatus.APPROVED)
        logger.info(f"📝 建立直接輸入任務 (無潤色): {task_id}")
        return {"success": True, "task_id": task_id, "content": content, "message": "Content Saved"}
    except Exception as e:
        logger.error(f"Direct content error: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/staff/content/tasks", response_model=TaskListResponse)
async def list_tasks(limit: int = 50, auth: bool = Depends(verify_password)):
    tasks = task_mgr.list_tasks(limit)
    return {"success": True, "tasks": tasks, "total": len(tasks)}

@app.get("/api/staff/content/task/{task_id}")
async def get_task(task_id: str, auth: bool = Depends(verify_password)):
    task = task_mgr.get_task(task_id)
    if not task: raise HTTPException(404, "Task not found")
    return {"success": True, "task": task}

@app.put("/api/staff/content/task/{task_id}")
async def update_content(task_id: str, update: ContentUpdate, auth: bool = Depends(verify_password)):
    task = task_mgr.get_task(task_id)
    if not task: raise HTTPException(404, "Task not found")
    task_mgr.update_content(task_id, update.content, update.editor)
    if task.get('content') != update.content:
        content_gen.save_edit_feedback(task_id, task.get('content', ''), update.content)
    return {"success": True, "message": "Updated"}

@app.post("/api/staff/content/task/{task_id}/approve")
async def approve_content(task_id: str, auth: bool = Depends(verify_password)):
    if task_mgr.approve_task(task_id):
        return {"success": True, "message": "Approved"}
    raise HTTPException(500, "Approval failed")

# --- Media Generation ---

@app.post("/api/staff/media/voice/{task_id}", response_model=MediaResponse)
async def generate_voice(task_id: str, auth: bool = Depends(verify_password)):
    try:
        task = task_mgr.get_task(task_id)
        if not task or not task.get('content'): raise HTTPException(400, "No content")
        media_id = task_mgr.create_media_record(task_id, "voice")
        task_mgr.update_status(task_id, TaskStatus.GENERATING_VOICE)
        
        path = await voice_service.generate_voice(task['content'], task_id)
        
        task_mgr.complete_media(media_id, path)
        return {"success": True, "task_id": task_id, "media_type": "voice", "file_path": path, "message": "Voice Ready"}
    except Exception as e:
        logger.error(f"Voice failed: {e}")
        raise HTTPException(500, str(e))

@app.post("/api/staff/media/avatar-video/{task_id}", response_model=MediaResponse)
async def generate_avatar_video(task_id: str, image_path: str, auth: bool = Depends(verify_password)):
    try:
        records = db.get_media_records(task_id)
        audio_file = next((r['file_path'] for r in records if r['media_type'] == 'voice' and r['status'] == 'completed'), None)
        if not audio_file: raise HTTPException(400, "No voice file found")
        
        media_id = task_mgr.create_media_record(task_id, "avatar_video")
        task_mgr.update_status(task_id, TaskStatus.GENERATING_VIDEO)
        
        logger.info(f"🎬 HeyGen 請求 (Base URL: {SERVER_BASE_URL})")
        
        video_path = await heygen_service.generate_avatar_video(
            audio_path=audio_file,
            image_path=image_path,
            task_id=task_id,
            base_url=SERVER_BASE_URL
        )
        
        task_mgr.complete_media(media_id, video_path)
        task_mgr.update_status(task_id, TaskStatus.COMPLETED)
        return {"success": True, "task_id": task_id, "media_type": "video", "file_path": video_path, "message": "Video Ready"}
    except Exception as e:
        logger.error(f"Video failed: {e}")
        task_mgr.update_status(task_id, TaskStatus.FAILED)
        raise HTTPException(500, str(e))

# === 【關鍵修改】使用背景任務處理 HeyGen 生成 ===
@app.post("/api/staff/media/avatar-video-upload", response_model=MediaResponse)
async def generate_avatar_video_upload(
    audio_path: str, 
    image_path: str, 
    background_tasks: BackgroundTasks,
    auth: bool = Depends(verify_password)
):
    try:
        import time
        task_id = f"upload_{int(time.time())}"
        
        # 1. 建立記錄並設為處理中
        media_id = task_mgr.create_media_record(task_id, "avatar_video")
        task_mgr.update_status(task_id, TaskStatus.GENERATING_VIDEO)

        logger.info(f"🎬 [API] 收到請求，已排入後台: {task_id}")

        # 2. 定義後台任務
        async def _background_generate():
            try:
                logger.info(f"🚀 [Background] 開始 HeyGen 任務: {task_id}")
                video_path = await heygen_service.generate_avatar_video(
                    audio_path=audio_path,
                    image_path=image_path,
                    task_id=task_id,
                    base_url=SERVER_BASE_URL
                )
                task_mgr.complete_media(media_id, video_path)
                task_mgr.update_status(task_id, TaskStatus.COMPLETED)
                logger.info(f"✅ [Background] 任務完成: {task_id}")
            except Exception as e:
                logger.error(f"❌ [Background] 任務失敗: {e}")
                db.update_media_record(media_id, {'status': 'failed'})
                task_mgr.update_status(task_id, TaskStatus.FAILED)

        # 3. 加入背景執行
        background_tasks.add_task(_background_generate)

        # 4. 立刻回傳（不需要等待生成完畢）
        return {
            "success": True, 
            "task_id": task_id, 
            "media_type": "video", 
            "file_path": None,  # 還沒好，所以是空值
            "message": "Video generation started in background"
        }

    except Exception as e:
        logger.error(f"Video upload failed: {e}")
        raise HTTPException(500, str(e))

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), folder: str = Form(""), auth: bool = Depends(verify_password)):
    try:
        from pathlib import Path
        import shutil
        base_dir = Path("documents")
        target_dir = base_dir / folder if folder else base_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "file_path": str(file_path), "message": "Uploaded"}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/staff/media/status/{task_id}")
async def get_media_status(task_id: str, auth: bool = Depends(verify_password)):
    task = task_mgr.get_task(task_id)
    return {
        "success": True, 
        "task_status": task['status'] if task else "unknown", 
        "media_records": db.get_media_records(task_id)
    }

@app.get("/api/staff/media/voices")
async def get_available_voices(auth: bool = Depends(verify_password)):
    if not voice_service.api_key: raise HTTPException(503, "API Key missing")
    return {"success": True, "voices": await voice_service.get_available_voices()}

@app.get("/api/staff/media/avatars")
async def get_available_avatars(auth: bool = Depends(verify_password)):
    if not heygen_service.api_key: raise HTTPException(503, "API Key missing")
    return {"success": True, "avatars": await heygen_service.get_avatar_list()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)