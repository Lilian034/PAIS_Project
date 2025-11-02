"""
幕僚系統記憶管理
遵循 Single Responsibility Principle：專注於記憶的儲存與檢索
目的：讓 LLM 學習市長的用字遣詞
"""
from pathlib import Path
from typing import Dict
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import FileChatMessageHistory
from loguru import logger


class StaffMemoryManager:
    """幕僚系統記憶管理器"""
    
    def __init__(self, base_path: str = "chat_history/staff"):
        self.memory_store: Dict[str, ConversationBufferMemory] = {}
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"🧠 記憶管理器初始化: {self.base_path}")
    
    def get_memory(self, task_id: str) -> ConversationBufferMemory:
        """
        為每個任務建立獨立記憶
        讓 LLM 能夠學習並保持一致的語氣風格
        """
        memory_key = f"content_task_{task_id}"
        
        if memory_key not in self.memory_store:
            history_file = self.base_path / f"{memory_key}.json"
            message_history = FileChatMessageHistory(str(history_file))
            
            self.memory_store[memory_key] = ConversationBufferMemory(
                chat_memory=message_history,
                memory_key="chat_history",
                return_messages=True,
                output_key="text"  # 指定輸出鍵
            )
            logger.info(f"🆕 建立記憶: {memory_key}")
        
        return self.memory_store[memory_key]
    
    def save_feedback(self, task_id: str, original: str, edited: str):
        """
        記錄人工修改作為學習樣本
        幫助 LLM 學習正確的用字遣詞
        """
        memory = self.get_memory(task_id)
        
        # 儲存原始與修改後的對比
        memory.save_context(
            {"input": f"原始文案:\n{original}"},
            {"text": f"修改後:\n{edited}"}
        )
        
        logger.info(f"💾 儲存修改記錄: {task_id}")
    
    def add_generation_record(self, task_id: str, topic: str, style: str, content: str):
        """記錄生成的文案"""
        memory = self.get_memory(task_id)
        
        memory.save_context(
            {"input": f"生成 {style} 風格文案，主題：{topic}"},
            {"text": content}
        )
        
        logger.info(f"📝 記錄文案生成: {task_id}")
    
    def clear_memory(self, task_id: str):
        """清除特定任務的記憶"""
        memory_key = f"content_task_{task_id}"
        
        if memory_key in self.memory_store:
            del self.memory_store[memory_key]
            
            # 刪除檔案
            history_file = self.base_path / f"{memory_key}.json"
            if history_file.exists():
                history_file.unlink()
            
            logger.info(f"🗑️ 清除記憶: {memory_key}")