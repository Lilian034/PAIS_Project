import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from .db_helper import StaffDatabase
from models.staff_models import TaskStatus


class TaskManager:
    """任務流程管理器"""
    
    def __init__(self, db: StaffDatabase):
        self.db = db
    
    def create_task(self, topic: str, style: str, length: str) -> str:
        """建立新任務"""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        memory_id = f"content_task_{task_id}"
        
        task_data = {
            'id': task_id,
            'topic': topic,
            'style': style,
            'length': length,
            'status': TaskStatus.DRAFT.value,
            'content': None,
            'memory_id': memory_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.db.create_task(task_data)
        logger.info(f"✅ 建立任務: {task_id} - {topic}")
        return task_id
    
    def update_content(self, task_id: str, content: str, editor: str = "system") -> bool:
        """更新文案內容並記錄版本"""
        # 取得當前版本號
        latest_version = self.db.get_latest_version(task_id)
        new_version = latest_version + 1
        
        # 儲存版本
        version_data = {
            'id': f"ver_{uuid.uuid4().hex[:12]}",
            'task_id': task_id,
            'version': new_version,
            'content': content,
            'created_by': editor,
            'created_at': datetime.now().isoformat()
        }
        self.db.create_version(version_data)
        
        # 更新任務內容
        self.db.update_task(task_id, {'content': content})
        logger.info(f"📝 更新文案: {task_id} v{new_version}")
        return True
    
    def update_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新任務狀態"""
        return self.db.update_task(task_id, {'status': status.value})
    
    def approve_task(self, task_id: str) -> bool:
        """審核通過"""
        success = self.update_status(task_id, TaskStatus.APPROVED)
        if success:
            logger.info(f"✅ 任務審核通過: {task_id}")
        return success
    
    def create_media_record(self, task_id: str, media_type: str) -> str:
        """建立多媒體生成記錄"""
        media_id = f"media_{uuid.uuid4().hex[:12]}"
        
        media_data = {
            'id': media_id,
            'task_id': task_id,
            'media_type': media_type,
            'file_path': None,
            'status': 'processing',
            'created_at': datetime.now().isoformat()
        }
        
        self.db.create_media_record(media_data)
        logger.info(f"🎬 建立媒體記錄: {media_id} ({media_type})")
        return media_id
    
    def complete_media(self, media_id: str, file_path: str) -> bool:
        """完成多媒體生成"""
        return self.db.update_media_record(media_id, {
            'file_path': file_path,
            'status': 'completed'
        })
    
    def fail_media(self, media_id: str) -> bool:
        """多媒體生成失敗"""
        return self.db.update_media_record(media_id, {'status': 'failed'})
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """取得任務詳情"""
        return self.db.get_task(task_id)
    
    def list_tasks(self, limit: int = 50) -> list:
        """列出所有任務"""
        return self.db.get_all_tasks(limit)