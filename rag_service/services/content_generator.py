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
        logger.info("✅文案生成器初始化完成")
    
    def _build_prompt(self) -> PromptTemplate:
        """建立文案生成 Prompt"""
        return PromptTemplate(
            template="""你是市長張善政的數位分身與首席文膽。

【核心思維：工程師人文主義】
- 視角：理工腦（數據實證）+ 父母心（同理關懷）
- 聲紋：沈穩親切、務實不空泛
- 信念：說到做到、團隊共同努力
- 語庫：「各位鄉親」「市府團隊全力以赴」「讓我們一起打拼」「謝謝大家的支持」

【學習記憶】
{chat_history}
**從過往修改中學習幕僚偏好，避免重複錯誤，保持風格一致。**

【任務】主題：{topic} | 類型：{style} | 長度：{length}

【知識庫】
{context}
**數據、日期、政策名稱必須基於上述資料，不得編造。**

【文案類型協議】

**press（新聞稿）**
- 第三人稱客觀報導（「市長張善政表示」「桃園市政府宣布」）
- 結構：5W1H 導言 → 引述發言 → 政策細節 → 預期效益
- 禁用第一人稱「我」「我們」
- 範例：「桃園市長張善政今日宣布...」

**speech（演講稿）**
- 第一人稱情感連結
- 結構：開場問候 → 主題鋪陳 → 核心論述 → 情感號召 → 感謝結語
- 口語技巧：短句、重複強調、設問修辭
- 範例：「各位鄉親、市民朋友，大家好！」

**facebook（Facebook 貼文）**
- 第一人稱親民互動，可用表情符號、問句
- 結構：吸睛開場 → 生活化敘事 → 政策說明 → 互動號召
- 範例：「大家好！今天要跟各位分享一個好消息😊」

**instagram（Instagram 貼文）**
- 第一人稱視覺為主，精簡明快
- 結構：簡短開場 → 核心訊息（2-3句）→ hashtag
- 範例：「桃園的改變，你看見了嗎？✨#桃園 #市政建設」

**poster（宣傳海報）**
- 無人稱或祈使句，20-50 字最佳
- 結構：主標（核心訴求）+ 副標（補充說明）
- 範例：「說到做到，為桃園打拼 | 市長張善政，與您一起建設幸福桃園」

【長度規範】
- short (50-100字)：Instagram、海報
- medium (150-300字)：Facebook、新聞稿導言
- long (400-600字)：完整新聞稿、演講稿

【安全閥】
- 數據零容忍：不編造數字、日期
- 承諾邊界：慎用「一定」「保證」，用「會努力」「持續推動」
- 形象防護：不涉及選舉、政黨攻擊
- 品質閥：邏輯通順、風格一致、符合長度要求

**只輸出文案本身，不要有任何說明或備註。**
開始生成：""",
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

            # 取得記憶並手動提取 chat_history
            memory = self.memory_manager.get_memory(task_id)
            chat_history = memory.load_memory_variables({}).get("chat_history", "")

            # 建立 Chain（不使用自動 memory，手動傳入 chat_history）
            chain = LLMChain(
                llm=self.llm,
                prompt=self.prompt,
                verbose=True
            )

            # 生成文案
            logger.info(f"開始生成文案: {task_id} - {topic}")
            result = await chain.ainvoke({
                "topic": topic,
                "style": style,
                "length": length,
                "context": context,
                "chat_history": chat_history
            })

            content = result["text"].strip()

            # 手動保存到記憶
            memory.save_context(
                {"input": f"生成文案 - 主題: {topic}, 風格: {style}, 長度: {length}"},
                {"text": content}
            )

            # 記錄生成結果到記憶
            self.memory_manager.add_generation_record(
                task_id, topic, style, content
            )

            logger.info(f"✅文案生成完成: {task_id} ({len(content)} 字)")
            return content
            
        except Exception as e:
            logger.error(f"❌文案生成失敗: {task_id} - {e}")
            raise
    
    def _retrieve_context(self, topic: str, k: int = 3) -> str:
        """從知識庫檢索相關資料"""
        try:
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})
            docs = retriever.invoke(topic)
            
            if docs:
                context = "\n\n".join([doc.page_content for doc in docs])
                logger.info(f"檢索到 {len(docs)} 筆相關資料")
                return context[:2000]
            else:
                logger.warning("⚠️知識庫中未找到相關資料")
                return "（無特定參考資料）"
                
        except Exception as e:
            logger.error(f"❌檢索知識庫失敗: {e}")
            return "（檢索失敗）"
    
    def save_edit_feedback(self, task_id: str, original: str, edited: str):
        """儲存人工修改作為學習樣本"""
        self.memory_manager.save_feedback(task_id, original, edited)
        logger.info(f"已儲存修改記錄作為學習樣本: {task_id}")