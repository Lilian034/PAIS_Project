"""
文案生成服務 (帶記憶功能)
遵循 Single Responsibility Principle：專注於文案生成邏輯
"""
import os
from typing import Optional
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from langchain_community.embeddings import HuggingFaceEmbeddings
from loguru import logger

from .memory_manager import StaffMemoryManager


class ContentGenerator:
    """文案生成器 (帶記憶學習功能)"""
    
    def __init__(
        self, 
        memory_manager: StaffMemoryManager,
        gemini_api_key: Optional[str] = None,
        qdrant_host: str = "qdrant",
        qdrant_port: int = 6333
    ):
        self.memory_manager = memory_manager
        
        # 初始化 LLM
        api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.llm = GoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.7,
            max_output_tokens=1024
        )
        
        # 初始化向量資料庫 (共用知識庫)
        embeddings = HuggingFaceEmbeddings(
            model_name="moka-ai/m3e-base",
            model_kwargs={'device': 'cpu'}
        )
        
        qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.vectorstore = Qdrant(
            client=qdrant_client,
            collection_name="pais_knowledge_base",
            embeddings=embeddings
        )
        
        # 建立 Prompt 模板
        self.prompt = self._build_prompt()
        logger.info("✅ 文案生成器初始化完成")
    
    def _build_prompt(self) -> PromptTemplate:
        """建立文案生成 Prompt"""
        return PromptTemplate(
            template="""你是桃園市長的專屬文案助理。

【過往學習記錄】
{chat_history}

【本次任務】
- 主題：{topic}
- 風格：{style}
- 長度：{length}

【參考資料】
{context}

【要求】
1. 完全模仿市長的語氣和用字遣詞
2. 根據過往記錄持續學習和優化
3. 風格說明：
   - formal (正式)：官方正式用語，適合政策宣布
   - casual (輕鬆)：親切口吻，適合日常互動
   - humorous (幽默)：加入輕鬆幽默元素
4. 長度要求：
   - short：50-100字
   - medium：150-300字
   - long：400-600字
5. 內容必須基於參考資料，避免虛構

請直接生成文案，不要有其他說明：""",
            input_variables=["topic", "style", "length", "context", "chat_history"]
        )
    
    async def generate(
        self, 
        task_id: str, 
        topic: str, 
        style: str, 
        length: str
    ) -> str:
        """
        生成文案
        
        Args:
            task_id: 任務 ID
            topic: 文案主題
            style: 風格 (formal/casual/humorous)
            length: 長度 (short/medium/long)
        
        Returns:
            生成的文案內容
        """
        try:
            # 從知識庫檢索相關資料
            context = self._retrieve_context(topic)
            
            # 取得記憶
            memory = self.memory_manager.get_memory(task_id)
            
            # 建立 Chain
            chain = LLMChain(
                llm=self.llm,
                prompt=self.prompt,
                memory=memory,
                verbose=True
            )
            
            # 生成文案
            logger.info(f"🚀 開始生成文案: {task_id} - {topic}")
            result = await chain.ainvoke({
                "topic": topic,
                "style": style,
                "length": length,
                "context": context
            })
            
            content = result["text"].strip()
            
            # 記錄生成結果到記憶
            self.memory_manager.add_generation_record(
                task_id, topic, style, content
            )
            
            logger.info(f"✅ 文案生成完成: {task_id} ({len(content)} 字)")
            return content
            
        except Exception as e:
            logger.error(f"❌ 文案生成失敗: {task_id} - {e}")
            raise
    
    def _retrieve_context(self, topic: str, k: int = 3) -> str:
        """從知識庫檢索相關資料"""
        try:
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})
            docs = retriever.invoke(topic)
            
            if docs:
                context = "\n\n".join([doc.page_content for doc in docs])
                logger.info(f"📚 檢索到 {len(docs)} 筆相關資料")
                return context[:2000]  # 限制長度
            else:
                logger.warning("⚠️ 知識庫中未找到相關資料")
                return "（無特定參考資料）"
                
        except Exception as e:
            logger.error(f"❌ 檢索知識庫失敗: {e}")
            return "（檢索失敗）"
    
    def save_edit_feedback(self, task_id: str, original: str, edited: str):
        """儲存人工修改作為學習樣本"""
        self.memory_manager.save_feedback(task_id, original, edited)
        logger.info(f"📚 已儲存修改記錄作為學習樣本: {task_id}")