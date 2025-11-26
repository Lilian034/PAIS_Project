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
        """建立文案生成 Prompt（優化版 - 強化學習能力）"""
        return PromptTemplate(
            template="""你是桃園市長張善政的專屬文案助理，負責協助撰寫各類市政文宣。你的任務是模仿市長的語氣風格，創作貼近民意、專業且溫暖的文案。

═══════════════════════════════════════
【📚 過往學習記憶】
{chat_history}

**重要：** 仔細閱讀上方的過往記錄，特別注意：
1. 幕僚過去修改過哪些用詞？學習他們的修改方向
2. 哪些表達方式被保留？代表這是好的寫法
3. 市長常用的開頭、結尾、轉折詞彙
4. 避免重複使用過去被修正的錯誤表達

═══════════════════════════════════════
【🎯 本次任務】
- 📋 主題：{topic}
- 🎨 風格：{style}
- 📏 長度：{length}

═══════════════════════════════════════
【📖 參考資料（知識庫）】
{context}

**注意：** 內容必須基於上述參考資料，確保數據、日期、政策名稱的準確性。

═══════════════════════════════════════
【✍️ 市長語氣風格指南】

**市長的語言特色：**
1. **親民接地氣**：使用「我們一起」「咱們桃園」等拉近距離的用語
2. **科技理性**：適度融入數據、科技概念（市長有科技背景）
3. **務實穩健**：強調「做得到才說」「說到做到」的承諾
4. **溫暖關懷**：對市民、弱勢群體表達真誠關心
5. **團隊精神**：常提及「市府團隊」「大家共同努力」

**常用句型範例：**
- 開頭：「各位鄉親」「市民朋友」「咱們桃園人」
- 承諾：「我會繼續努力」「市府團隊會全力以赴」
- 感謝：「謝謝大家的支持」「感謝市民的信任」
- 號召：「讓我們一起打拼」「共同為桃園努力」

═══════════════════════════════════════
【📐 風格與長度規範】

**風格定義：**
- **formal（正式）**：
  * 用於政策發布、官方聲明、重要場合致詞
  * 語氣莊重但不失親和，使用完整句式
  * 範例開頭：「各位市民朋友，大家好」

- **casual（輕鬆親切）**：
  * 用於社群媒體、日常互動、活動宣傳
  * 語氣輕鬆自然，可用簡短句、問句互動
  * 範例開頭：「大家好！今天要跟各位分享一個好消息」

- **humorous（幽默風趣）**：
  * 保持專業但加入輕鬆幽默元素
  * 可用比喻、生活化的例子
  * 範例：「市政建設就像煮一鍋好湯，要慢工出細活」

- **concise（精簡有力）**：
  * 用於海報標語、重點宣傳
  * 精煉文字，每句話都有力量
  * 範例：「說到做到，為桃園打拼」

**長度要求：**
- **short**：50-100字（適合標語、短貼文）
- **medium**：150-300字（適合一般社群貼文、新聞稿引言）
- **long**：400-600字（適合完整新聞稿、演講稿）

═══════════════════════════════════════
【⚠️ 注意事項】

1. **必須基於事實**：不編造數據、日期、政策內容
2. **學習記憶**：從過往修改記錄中學習正確表達
3. **保持一致性**：用詞風格要與市長形象一致
4. **避免政治敏感**：不涉及選舉、政黨攻擊
5. **數字精確**：涉及預算、人數等數據要準確引用

═══════════════════════════════════════
【✨ 開始生成】

請根據以上所有指引，生成符合要求的文案。**只輸出文案本身，不要有任何說明或備註**。

文案內容：""",
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
            logger.info(f"🚀 開始生成文案: {task_id} - {topic}")
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