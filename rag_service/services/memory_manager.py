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
        記錄人工修改作為學習樣本（強化版）
        幫助 LLM 學習正確的用字遣詞，並分析修改模式
        """
        memory = self.get_memory(task_id)

        # 分析修改差異，提取學習要點
        learning_insights = self._analyze_edits(original, edited)

        # 儲存原始與修改後的對比，加上學習要點
        memory.save_context(
            {"input": f"【原始文案】\n{original}"},
            {"text": f"【幕僚修改後】\n{edited}\n\n【學習要點】\n{learning_insights}"}
        )

        logger.info(f"💾 儲存修改記錄並提取學習要點: {task_id}")

    def _analyze_edits(self, original: str, edited: str) -> str:
        """
        分析原始與修改後的文案差異，提取學習要點
        幫助 AI 更好地理解修改意圖
        """
        insights = []

        # 1. 檢查長度變化
        len_diff = len(edited) - len(original)
        if abs(len_diff) > 20:
            if len_diff > 0:
                insights.append("✏️ 幕僚傾向於更詳細的描述，增加了具體內容")
            else:
                insights.append("✂️ 幕僚傾向於精簡表達，刪除了冗餘內容")

        # 2. 檢查特定用詞的替換（簡單版本）
        replacements = []
        # 常見的用詞替換模式
        common_pairs = [
            ("民眾", "市民"),
            ("民眾", "鄉親"),
            ("很多", "眾多"),
            ("很多", "許多"),
            ("非常", "相當"),
            ("非常", "十分"),
            ("我們", "市府團隊"),
            ("我們", "咱們"),
        ]

        for old_word, new_word in common_pairs:
            if old_word in original and new_word in edited and old_word not in edited:
                replacements.append(f"將「{old_word}」改為「{new_word}」")

        if replacements:
            insights.append(f"📝 用詞優化: {'; '.join(replacements)}")

        # 3. 檢查是否加入了數據或事實
        if ("%" in edited and "%" not in original) or ("座" in edited and "座" not in original):
            insights.append("📊 幕僚加入了具體數據，使內容更有說服力")

        # 4. 檢查是否調整了開頭
        original_start = original[:20] if len(original) >= 20 else original
        edited_start = edited[:20] if len(edited) >= 20 else edited
        if original_start != edited_start:
            insights.append(f"🎯 開頭調整: 從「{original_start}...」改為「{edited_start}...」")

        if not insights:
            insights.append("✅ 幕僚做了細微調整，整體結構保持不變")

        return "\n".join(insights)
    
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

    def get_learning_summary(self, task_id: str) -> dict:
        """
        獲取學習摘要
        返回該任務的記憶統計信息
        """
        memory = self.get_memory(task_id)

        # 獲取記憶內容
        try:
            messages = memory.chat_memory.messages

            summary = {
                "task_id": task_id,
                "total_interactions": len(messages) // 2,  # 每次互動有 input 和 output
                "has_feedback": any("幕僚修改後" in str(msg.content) for msg in messages),
                "learning_points": []
            }

            # 提取所有學習要點
            for msg in messages:
                content = str(msg.content)
                if "【學習要點】" in content:
                    points = content.split("【學習要點】")[1].strip()
                    summary["learning_points"].append(points)

            return summary

        except Exception as e:
            logger.error(f"獲取學習摘要失敗: {e}")
            return {"task_id": task_id, "error": str(e)}