from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ContentStyle(str, Enum):
    """文案類型"""
    PRESS = "press"           # 新聞稿
    SPEECH = "speech"         # 演講稿
    FACEBOOK = "facebook"     # Facebook 貼文
    INSTAGRAM = "instagram"   # Instagram 貼文
    POSTER = "poster"         # 宣傳海報文案


class ContentLength(str, Enum):
    """文案長度"""
    SHORT = "short"      # 50-100字
    MEDIUM = "medium"    # 150-300字
    LONG = "long"        # 400-600字


class TaskStatus(str, Enum):
    """任務狀態"""
    DRAFT = "draft"                      # 草稿
    REVIEWING = "reviewing"              # 審核中
    APPROVED = "approved"                # 已審核
    GENERATING_VOICE = "generating_voice"  # 生成語音中
    GENERATING_VIDEO = "generating_video"  # 生成影片中
    COMPLETED = "completed"              # 完成
    FAILED = "failed"                    # 失敗


class MediaType(str, Enum):
    """多媒體類型"""
    VOICE = "voice"
    VIDEO = "video"


# ==================== Request Models ====================

class ContentRequest(BaseModel):
    """文案生成請求"""
    topic: str = Field(..., description="文案主題")
    style: ContentStyle = Field(..., description="文案風格")
    length: ContentLength = Field(..., description="文案長度")


class ContentUpdate(BaseModel):
    """文案更新請求"""
    content: str = Field(..., description="修改後的文案內容")
    editor: str = Field(default="admin", description="編輯者")


# ==================== Response Models ====================

class ContentTask(BaseModel):
    """文案任務"""
    id: str
    topic: str
    style: str
    length: str
    status: str
    content: Optional[str] = None
    memory_id: str
    created_at: str
    updated_at: str


class ContentVersion(BaseModel):
    """文案版本"""
    id: str
    task_id: str
    version: int
    content: str
    created_by: str
    created_at: str


class MediaRecord(BaseModel):
    """多媒體記錄"""
    id: str
    task_id: str
    media_type: str
    file_path: str
    status: str
    created_at: str


class GenerateResponse(BaseModel):
    """生成回應"""
    success: bool
    task_id: str
    content: str
    message: str


class TaskListResponse(BaseModel):
    """任務列表回應"""
    success: bool
    tasks: List[ContentTask]
    total: int


class MediaResponse(BaseModel):
    """多媒體生成回應"""
    success: bool
    task_id: str
    media_type: str
    file_path: Optional[str] = None
    message: str