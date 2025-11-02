import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
from loguru import logger


class StaffDatabase:
    """幕僚系統資料庫管理"""
    
    def __init__(self, db_path: str = "database/staff_system.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化資料表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 文案任務表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_tasks (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                style TEXT NOT NULL,
                length TEXT NOT NULL,
                status TEXT NOT NULL,
                content TEXT,
                memory_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 文案版本表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_versions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES content_tasks(id)
            )
        """)
        
        # 多媒體記錄表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_records (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                media_type TEXT NOT NULL,
                file_path TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES content_tasks(id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 資料庫初始化完成: {self.db_path}")
    
    def _get_connection(self):
        """取得資料庫連線"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 讓結果可以用欄位名稱存取
        return conn
    
    # ==================== Content Tasks ====================
    
    def create_task(self, task_data: Dict[str, Any]) -> str:
        """建立文案任務"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO content_tasks 
            (id, topic, style, length, status, content, memory_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_data['id'],
            task_data['topic'],
            task_data['style'],
            task_data['length'],
            task_data['status'],
            task_data.get('content'),
            task_data['memory_id'],
            task_data['created_at'],
            task_data['updated_at']
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"📝 建立任務: {task_data['id']}")
        return task_data['id']
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """取得單一任務"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM content_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """取得所有任務"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM content_tasks ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新任務"""
        if not updates:
            return False
        
        updates['updated_at'] = datetime.now().isoformat()
        
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [task_id]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"UPDATE content_tasks SET {set_clause} WHERE id = ?",
            values
        )
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"🔄 更新任務: {task_id}")
        return affected > 0
    
    # ==================== Content Versions ====================
    
    def create_version(self, version_data: Dict[str, Any]) -> str:
        """建立文案版本"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO content_versions 
            (id, task_id, version, content, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            version_data['id'],
            version_data['task_id'],
            version_data['version'],
            version_data['content'],
            version_data['created_by'],
            version_data['created_at']
        ))
        
        conn.commit()
        conn.close()
        return version_data['id']
    
    def get_versions(self, task_id: str) -> List[Dict[str, Any]]:
        """取得任務的所有版本"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM content_versions WHERE task_id = ? ORDER BY version DESC",
            (task_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_latest_version(self, task_id: str) -> int:
        """取得最新版本號"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT MAX(version) as max_version FROM content_versions WHERE task_id = ?",
            (task_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result['max_version'] if result['max_version'] else 0
    
    # ==================== Media Records ====================
    
    def create_media_record(self, media_data: Dict[str, Any]) -> str:
        """建立多媒體記錄"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO media_records 
            (id, task_id, media_type, file_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            media_data['id'],
            media_data['task_id'],
            media_data['media_type'],
            media_data.get('file_path'),
            media_data['status'],
            media_data['created_at']
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"🎬 建立媒體記錄: {media_data['id']}")
        return media_data['id']
    
    def get_media_records(self, task_id: str) -> List[Dict[str, Any]]:
        """取得任務的多媒體記錄"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM media_records WHERE task_id = ?",
            (task_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_media_record(self, media_id: str, updates: Dict[str, Any]) -> bool:
        """更新多媒體記錄"""
        if not updates:
            return False
        
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [media_id]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"UPDATE media_records SET {set_clause} WHERE id = ?",
            values
        )
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0