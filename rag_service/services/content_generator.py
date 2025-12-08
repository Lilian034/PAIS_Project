import os
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from langchain.agents import create_react_agent, Tool, AgentExecutor
from langchain.prompts import PromptTemplate
from loguru import logger
from .memory_manager import StaffMemoryManager
# 匯入 Agent Prompt
from prompts import CONTENT_GENERATION_AGENT_PROMPT

class ContentGenerator:
    """
    文案生成服務 (Agent 版)
    職責：整合 LLM、記憶與知識庫工具，主動查證後生成文案
    """
    
    def __init__(self, memory_manager: StaffMemoryManager):
        self.memory_manager = memory_manager
        # 1. 初始化 LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-001",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.4,
            max_output_tokens=2048
        )
        
        # 2. 初始化 Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="moka-ai/m3e-base",
            model_kwargs={'device': 'cpu'}
        )
        
        # 3. 初始化知識庫連線
        self.vectorstore = Qdrant(
            client=QdrantClient(
                host=os.getenv("QDRANT_HOST", "qdrant"),
                port=int(os.getenv("QDRANT_PORT", 6333))
            ),
            collection_name="pais_knowledge_base",
            embeddings=self.embeddings
        )
        
        # 4. 初始化工具
        self.tools = [
            Tool(
                name="KnowledgeSearch",
                func=self._search_knowledge_base,
                description="用於搜尋桃園市的政策、數據、活動細節或市長發言。輸入關鍵字即可。"
            )
        ]
        
        # 5. 初始化 Agent
        self.prompt = PromptTemplate(
            template=CONTENT_GENERATION_AGENT_PROMPT,
            input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"]
        )
        
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True, 
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        logger.info("✅ ContentGenerator (Agent Mode) Ready")

    def _clean_text(self, text: str) -> str:
        if not text: return ""
        return re.sub(r'[\{\}]', '', text)

    def _search_knowledge_base(self, query: str) -> str:
        """Agent 使用的搜尋工具"""
        safe_query = self._clean_text(query)
        logger.info(f"🔍 [文案生成] Agent 正在查證: {safe_query}")
        try:
            docs = self.vectorstore.similarity_search(safe_query, k=3)
            if docs:
                contents = [self._clean_text(d.page_content) for d in docs]
                result = "\n\n".join(contents)
                return f"【查證結果】:\n{result[:2000]}"
            return "知識庫中沒有找到相關資料。"
        except Exception as e:
            return f"搜尋發生錯誤: {str(e)}"

    async def generate(self, task_id: str, topic: str, style: str, length: str) -> str:
        """執行文案生成 (Agent 流程)"""
        try:
            # 這裡會呼叫 self.memory_manager，如果 __init__ 沒設定好就會報錯
            memory = self.memory_manager.get_memory(task_id)
            history = memory.load_memory_variables({})["chat_history"]

            user_input = f"撰寫一份「{style}」風格的文案，主題是「{topic}」，篇幅要求「{length}」。請務必先查證相關資料。"

            logger.info(f"🚀 開始生成文案 (Task: {task_id})")
            
            result = await self.agent_executor.ainvoke({
                "input": user_input,
                "chat_history": history
            })
            
            content = result.get("output", "").strip()

            memory.save_context(
                {"input": f"生成文案: {topic}"},
                {"text": content}
            )
            
            return content

        except Exception as e:
            logger.error(f"❌ 文案生成失敗: {e}")
            raise e

    def save_edit_feedback(self, task_id: str, original: str, edited: str):
        self.memory_manager.save_feedback(task_id, original, edited)