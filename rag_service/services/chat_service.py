"""
聊天服務模組
負責處理所有對話相關的業務邏輯
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from langchain.agents import AgentExecutor
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from loguru import logger


class ChatService:
    """
    聊天服務類
    處理 Agent 和 RAG Chain 模式的對話邏輯

    Attributes:
        llm: LangChain LLM 實例
        vectorstore: 向量資料庫實例
        tools: Agent 可用的工具列表
        agent: 公眾版 Agent (善寶)
        staff_agent: 幕僚版 Agent (校稿助理)
        rag_prompt: RAG Chain 使用的 Prompt
    """

    def __init__(
        self,
        llm,
        vectorstore,
        tools: list,
        agent=None,
        staff_agent=None,
        rag_prompt=None
    ):
        """
        初始化聊天服務

        Args:
            llm: LangChain LLM 實例
            vectorstore: Qdrant 向量資料庫
            tools: Agent 工具列表
            agent: 公眾版 Agent
            staff_agent: 幕僚版 Agent
            rag_prompt: RAG Prompt 模板
        """
        self.llm = llm
        self.vectorstore = vectorstore
        self.tools = tools
        self.agent = agent
        self.staff_agent = staff_agent
        self.rag_prompt = rag_prompt

        logger.info("✅ ChatService 初始化完成")

    async def process_chat(
        self,
        message: str,
        session_id: str,
        memory: ConversationBufferMemory,
        use_agent: bool = True,
        role: str = "public"
    ) -> Dict[str, Any]:
        """
        處理聊天請求的主要入口

        Args:
            message: 用戶訊息
            session_id: 會話 ID
            memory: 對話記憶
            use_agent: 是否使用 Agent 模式
            role: 角色 ("public" 或 "staff")

        Returns:
            包含回覆、來源、思考過程等的字典
            {
                "reply": str,
                "sources": List[str],
                "session_id": str,
                "timestamp": str,
                "thought_process": Optional[str]
            }

        Raises:
            ValueError: 當必要的 Agent 未初始化時
        """
        logger.info(f"💬 [{session_id}] 收到問題 (角色: {role}): {message}")

        try:
            if use_agent:
                return await self._handle_agent_mode(
                    message, session_id, memory, role
                )
            else:
                return await self._handle_rag_mode(
                    message, session_id, memory
                )
        except Exception as e:
            logger.error(
                f"❌ 對話處理失敗 ({session_id}): {str(e)}",
                exc_info=True
            )
            return self._build_error_response(
                session_id, role, error=e
            )

    async def _handle_agent_mode(
        self,
        message: str,
        session_id: str,
        memory: ConversationBufferMemory,
        role: str
    ) -> Dict[str, Any]:
        """
        處理 Agent 模式的對話

        Args:
            message: 用戶訊息
            session_id: 會話 ID
            memory: 對話記憶
            role: 角色 ("public" 或 "staff")

        Returns:
            對話結果字典

        Raises:
            ValueError: 當對應的 Agent 未初始化時
        """
        memory.output_key = "output"

        # 根據角色選擇 Agent
        if role == "staff":
            if not self.staff_agent:
                logger.error(
                    f"❌ Staff Agent 未初始化，無法處理幕僚請求 ({session_id})"
                )
                raise ValueError("幕僚系統 Agent 元件未初始化")
            current_agent = self.staff_agent
            logger.info(f"🎭 [{session_id}] 使用幕僚助理模式")
        else:
            if not self.agent:
                logger.error(
                    f"❌ Agent 未初始化，無法處理公眾請求 ({session_id})"
                )
                raise ValueError("系統 Agent 元件未初始化")
            current_agent = self.agent
            logger.info(f"🎭 [{session_id}] 使用善寶模式")

        # 創建 AgentExecutor
        agent_executor = AgentExecutor(
            agent=current_agent,
            tools=self.tools,
            memory=memory,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )

        # 執行 Agent
        logger.info(f"🚀 [{session_id}] 開始執行 Agent...")
        try:
            result = agent_executor.invoke({"input": message})
            raw_output = result.get("output", "")

            # 提取 Final Answer
            reply = self._extract_final_answer(raw_output)

            # 驗證回覆品質
            if not self._is_valid_reply(reply, raw_output):
                logger.warning(
                    f"⚠️ Final Answer 品質不佳 ({session_id})"
                )
                reply = self._get_fallback_reply(raw_output, role)

            # 提取來源
            sources = self._extract_agent_sources(result)

            # 構建思考過程字符串（用於調試）
            thought_process = self._build_thought_process(
                raw_output, result
            )

            logger.info(
                f"✅ [{session_id}] Agent 執行完成 (回覆長度: {len(reply)})"
            )

            return {
                "reply": reply,
                "sources": sources,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "thought_process": thought_process
            }

        except Exception as e:
            logger.error(
                f"❌ AgentExecutor 執行失敗 ({session_id}): {str(e)}",
                exc_info=True
            )
            return self._build_error_response(
                session_id, role, error=e, include_error_detail=True
            )

    async def _handle_rag_mode(
        self,
        message: str,
        session_id: str,
        memory: ConversationBufferMemory
    ) -> Dict[str, Any]:
        """
        處理 RAG Chain 模式的對話

        Args:
            message: 用戶訊息
            session_id: 會話 ID
            memory: 對話記憶

        Returns:
            對話結果字典
        """
        memory.output_key = "answer"

        # 創建 RAG Chain
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=memory,
            combine_docs_chain_kwargs={"prompt": self.rag_prompt},
            return_source_documents=True,
            verbose=True
        )

        # 執行 RAG Chain
        logger.info(f"🚀 [{session_id}] 開始執行 RAG Chain...")
        result = qa_chain.invoke({"question": message})
        logger.info(f"✅ [{session_id}] RAG Chain 執行完成")

        # 提取回覆和來源
        reply = result.get("answer", "抱歉，我無法回答這個問題。")
        sources = self._extract_rag_sources(result)

        return {
            "reply": reply,
            "sources": sources,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "thought_process": "使用 RAG Chain 模式，無 ReAct 思考過程。"
        }

    def _extract_final_answer(self, raw_output: str) -> str:
        """
        從 Agent 原始輸出中提取 Final Answer

        Args:
            raw_output: Agent 原始輸出字符串

        Returns:
            清理後的 Final Answer
        """
        if not raw_output:
            return ""

        # 尋找 Final Answer: 標記
        final_answer_marker = "Final Answer:"
        if final_answer_marker in raw_output:
            # 找到最後一個 Final Answer（避免重複）
            parts = raw_output.split(final_answer_marker)
            answer = parts[-1]

            # 強力去除開頭的所有空白字符和換行符
            answer = answer.lstrip()

            # 移除可能殘留的思考過程
            for marker in ["Thought:", "Action:", "Observation:"]:
                if marker in answer:
                    # 只取 Final Answer 到下一個標記之間的內容
                    answer = answer.split(marker)[0].rstrip()

            return answer

        # 如果沒有 Final Answer 標記，但內容看起來像回答
        if len(raw_output) > 30 and "Thought:" not in raw_output[:50]:
            return raw_output.strip()

        return ""

    def _is_valid_reply(self, reply: str, raw_output: str) -> bool:
        """
        驗證回覆是否有效

        Args:
            reply: 提取後的回覆
            raw_output: 原始輸出

        Returns:
            是否為有效回覆
        """
        if not reply:
            return False

        # 檢查是否仍包含思考過程標記
        invalid_markers = ["Thought:", "Action:", "Action Input:"]
        if any(marker in reply[:20] for marker in invalid_markers):
            return False

        # 檢查最小長度
        if len(reply) < 10:
            return False

        return True

    def _get_fallback_reply(self, raw_output: str, role: str) -> str:
        """
        獲取後備回覆

        Args:
            raw_output: 原始輸出
            role: 角色

        Returns:
            後備回覆字符串
        """
        # 如果原始輸出長度合理且不包含過多思考過程，使用原始輸出
        if len(raw_output) > 30 and raw_output.count("Thought:") <= 1:
            return raw_output.strip()

        # 否則返回友好的錯誤訊息
        if role == "staff":
            return "抱歉，系統暫時無法回應，請稍後再試。"
        else:
            return "哎呀，善寶好像有點累了，或是網路不太穩定，請稍後再試一次喔！"

    def _extract_agent_sources(self, result: Dict[str, Any]) -> List[str]:
        """
        從 Agent 執行結果中提取來源

        Args:
            result: Agent 執行結果

        Returns:
            來源列表
        """
        sources = []

        if "intermediate_steps" not in result:
            return sources

        for action, observation in result["intermediate_steps"]:
            tool_name = getattr(action, 'tool', '未知工具')

            # 只記錄知識庫相關工具
            if tool_name in ["搜尋知識庫", "查詢特定政策名稱"]:
                sources.append(tool_name)

        logger.info(
            f"📚 從 Agent 中間步驟提取到 {len(sources)} 個工具使用記錄"
        )

        return list(set(sources))  # 去重

    def _extract_rag_sources(self, result: Dict[str, Any]) -> List[str]:
        """
        從 RAG Chain 結果中提取來源

        Args:
            result: RAG Chain 執行結果

        Returns:
            文檔來源列表（僅檔名）
        """
        source_docs = result.get("source_documents", [])
        sources = [
            doc.metadata.get("source", "未知來源").split('/')[-1]
            for doc in source_docs
        ]
        return list(set(sources))  # 去重

    def _build_thought_process(
        self,
        raw_output: str,
        result: Dict[str, Any]
    ) -> str:
        """
        構建思考過程字符串（用於調試）

        Args:
            raw_output: Agent 原始輸出
            result: 執行結果

        Returns:
            思考過程字符串（限制長度）
        """
        if raw_output:
            # 限制長度避免過大
            max_length = 2000
            if len(raw_output) > max_length:
                return raw_output[:max_length] + "..."
            return raw_output

        if "error" in result:
            error_msg = str(result["error"])
            return f"Agent 執行錯誤: {error_msg[:1000]}..."

        return "Agent 未成功產生輸出。"

    def _build_error_response(
        self,
        session_id: str,
        role: str,
        error: Exception = None,
        include_error_detail: bool = False
    ) -> Dict[str, Any]:
        """
        構建錯誤響應

        Args:
            session_id: 會話 ID
            role: 角色
            error: 異常對象
            include_error_detail: 是否包含錯誤詳情

        Returns:
            錯誤響應字典
        """
        # 根據角色選擇錯誤訊息
        if role == "staff":
            reply = "抱歉，系統暫時無法回應，請稍後再試。"
        else:
            reply = "哎呀，善寶好像有點累了，或是網路不太穩定，請稍後再試一次喔！"

        # 構建思考過程（包含錯誤資訊）
        thought_process = "系統發生錯誤"
        if error and include_error_detail:
            error_type = type(error).__name__
            error_msg = str(error).replace('{', '{{').replace('}', '}}')
            thought_process = f"系統層級錯誤 ({error_type}): {error_msg}"

            # 在用戶可見的回覆中包含簡化的錯誤提示
            reply = f"抱歉，我在處理您的問題時遇到了一些困難 ({error_type})。請您換個方式再問一次，或聯繫管理員。"

        return {
            "reply": reply,
            "sources": [],
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "thought_process": thought_process
        }
