import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ==================== LangChain 核心 ====================
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, Docx2txtLoader, TextLoader
)
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# ==================== LangChain Agents ====================
from langchain.agents import AgentExecutor, create_react_agent, Tool
from langchain.prompts import PromptTemplate

# ==================== LangChain Memory ====================
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import FileChatMessageHistory

# ==================== LangChain Chains ====================
from langchain.chains import (
    ConversationalRetrievalChain,
    LLMChain
)

from dotenv import load_dotenv
from loguru import logger

# 載入環境變數
load_dotenv()

# ==================== 配置 ====================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123456")
COLLECTION_NAME = "pais_knowledge_base"

# 設定日誌
logger.add("logs/pais_{time}.log", rotation="1 day", retention="30 days")

# ==================== FastAPI 應用 ====================
app = FastAPI(
    title="PAIS - 政務分身智能系統 (LangChain Powered)",
    description="基於 LangChain 的市長聊天機器人 (Agents + Memory + RAG + Tools)",
    version="2.0.2" # 版本更新
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== LangChain 初始化 ====================

# Gemini LLM
llm = GoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.7,
    max_output_tokens=2048
)

# Embeddings (使用 moka-ai/m3e-base)
embeddings = HuggingFaceEmbeddings(
    model_name="moka-ai/m3e-base",
    model_kwargs={'device': 'cpu'}
)

# Qdrant 向量資料庫
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

try:
    qdrant_client.get_collection(COLLECTION_NAME)
    logger.info(f"✅ 集合 '{COLLECTION_NAME}' 已存在")
except Exception:
    logger.warning(f"⚠️ 集合 '{COLLECTION_NAME}' 不存在，嘗試建立...")
    try:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE) # 維度為 768
        )
        logger.info(f"✅ 已建立新集合 '{COLLECTION_NAME}'")
    except Exception as create_err:
        logger.error(f"❌ 建立集合 '{COLLECTION_NAME}' 失敗: {create_err}")
        # 如果無法建立集合，後續的 vectorstore 初始化可能會失敗

vectorstore = Qdrant(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embeddings=embeddings
)

# ==================== LangChain Memory 管理 ====================
memory_store: Dict[str, ConversationBufferMemory] = {}

def get_memory(session_id: str) -> ConversationBufferMemory:
    """取得或建立對話記憶"""
    if session_id not in memory_store:
        try:
            # 確保 chat_history 目錄存在
            Path("chat_history").mkdir(exist_ok=True)
            history_file = f"chat_history/{session_id}.json"
            message_history = FileChatMessageHistory(history_file)

            memory_store[session_id] = ConversationBufferMemory(
                chat_memory=message_history,
                memory_key="chat_history",
                return_messages=True
                # output_key 會在 chat 函數中動態設定
            )
            logger.info(f"🧠 建立新記憶: {session_id} (檔案: {history_file})")
        except Exception as mem_err:
            logger.error(f"❌ 建立記憶體失敗 ({session_id}): {mem_err}")
            # 返回一個臨時的記憶體以避免崩潰，但歷史記錄不會保存
            return ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            
    return memory_store[session_id]

# ==================== LangChain Tools ====================

def search_knowledge_base(query: str) -> str:
    """搜尋知識庫工具"""
    logger.info(f"🛠️ 使用工具 [搜尋知識庫]，查詢: {query}")
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(query) # 使用 invoke
        if docs:
            result = "\n\n".join([f"來源 {i+1} ({doc.metadata.get('source', '未知')[-30:]}):\n{doc.page_content}" for i, doc in enumerate(docs)])
            logger.info(f"✅ 工具 [搜尋知識庫] 找到 {len(docs)} 筆資料")
            return f"找到相關資料：\n{result}"
        else:
            logger.warning(f"⚠️ 工具 [搜尋知識庫] 未找到資料 for query: {query}")
            return "知識庫中找不到與此直接相關的資料。"
    except Exception as e:
        logger.error(f"❌ 工具 [搜尋知識庫] 執行錯誤: {e}", exc_info=True)
        return f"搜尋知識庫時發生錯誤: {str(e)}"

def get_policy_info(policy_name: str) -> str:
    """取得特定政策資訊工具"""
    logger.info(f"🛠️ 使用工具 [查詢政策]，政策名稱: {policy_name}")
    try:
        # 使用 similarity_search 可能更適合直接找特定名稱
        docs = vectorstore.similarity_search(policy_name, k=2)
        if docs:
            result = f"來源 ({docs[0].metadata.get('source', '未知')[-30:]}):\n{docs[0].page_content}"
            logger.info(f"✅ 工具 [查詢政策] 找到資料 for policy: {policy_name}")
            return f"關於 '{policy_name}' 的資訊：{result}"
        else:
            logger.warning(f"⚠️ 工具 [查詢政策] 未找到資料 for policy: {policy_name}")
            return f"知識庫中找不到名為 '{policy_name}' 的特定政策資訊。"
    except Exception as e:
        logger.error(f"❌ 工具 [查詢政策] 執行錯誤: {e}", exc_info=True)
        return f"查詢政策 '{policy_name}' 時發生錯誤: {str(e)}"

# 定義 Agent 工具
tools = [
    Tool(
        name="搜尋知識庫",
        func=search_knowledge_base,
        description="當你需要回答關於市長的**政策、理念、施政報告、公開發言、個人背景**或**桃園市政相關問題**時使用。**輸入：** 具體的問題或清晰的關鍵字詞組 (例如：'桃園市的交通政策有哪些？', '市長對於青年就業的看法', '說明社會住宅的進度')。**不要**只輸入模糊的單詞。"
    ),
    Tool(
        name="查詢特定政策名稱",
        func=get_policy_info,
        description="當使用者**明確**提到一個**具體的政策名稱**，而你需要查找該政策的詳細內容時使用。**輸入：** 完整的政策名稱 (例如：'五歲幼兒教育助學金', '國中小免費營養午餐')。如果只是問某個領域的政策 (如 '交通政策')，請使用「搜尋知識庫」。"
    ),
]

# ==================== LangChain Agent 定義 ====================

# --- 修正 Agent Prompt ---
AGENT_PROMPT = """你是桃園市長張善政的 AI 分身「善寶」，一個親切、專業、略帶幽默感的 AI 助理。你的任務是根據提供的工具和對話記錄，以市長的口吻回答市民的問題。

**你的回答風格：**
1.  **語氣：** 親切、專業、有耐心，偶爾帶點輕鬆幽默，就像市長本人一樣。
2.  **開頭：** 可以用 "嗨！"、"你好！" 或 "市民您好" 開頭，但避免每次都一樣。
3.  **自稱：** 使用「我」或「善寶」。
4.  **內容：** 優先使用工具從知識庫查找**準確**資訊。如果找不到，**誠實告知**找不到具體細節，但可以提供一般性說明或建議洽詢市府。
5.  **簡潔：** 回答要抓住重點，避免過於冗長。
6.  **安全：** 避開敏感政治話題或人身攻擊 (例如選舉、批評特定人物)。如果遇到，使用固定回應：“這個問題比較敏感，建議您關注桃園市政府官方網站的正式資訊，或直接撥打 1999 市民專線詢問。我們很樂意為您服務！😊”

**可用工具：**
{tools}

**使用工具的思考流程 (ReAct 格式)：**
Question: 使用者提出的問題。
Thought: 仔細分析問題。判斷是否需要使用工具？
    * 如果是**簡單問候** (例如：你好、你是誰)，或**常識性問題**，或者涉及**敏感話題**，**不需要**使用工具，可以直接思考 Final Answer。
    * 如果是關於**市政、政策、市長理念/發言/背景**的問題，**需要**使用工具。選擇最適合的工具 (搜尋知識庫 或 查詢特定政策名稱)。決定 Action Input (要查詢的關鍵字或政策名稱)。
Action: 選擇的工具名稱 (例如：搜尋知識庫)。
Action Input: 提供給工具的輸入 (例如：桃園市社會住宅進度)。
Observation: 工具返回的結果 (可能是找到的資料，或 "找不到資料" 的訊息)。
Thought: 檢視 Observation。
    * 如果找到滿意的資料，根據資料和對話記錄，以市長口吻組織 Final Answer。
    * 如果工具返回 "找不到資料" 或資料不相關，**不要**再次嘗試**相同**的查詢。思考是否可以用**不同**的關鍵字再試一次「搜尋知識庫」(最多嘗試 1-2 次不同的關鍵字)。如果還是找不到，就在 Final Answer 中**誠實說明**找不到具體細節，並提供一般性建議。**絕對不要**幻想或編造答案。
    * 如果工具返回錯誤訊息，也在 Final Answer 中說明查詢時遇到問題。
Final Answer: [**這裡直接寫出**你最終要給使用者的完整回覆，用市長的口吻，**不要包含** "Final Answer:" 這個標籤本身。]

**重要：** 即使你知道答案，如果問題涉及市政或政策細節，**也應該優先使用工具**確認資訊的準確性。除非是像「你是誰」這種基本自我介紹。

**對話記錄 (最近的對話)：**
{chat_history}

**開始！**

Question: {input}
Thought: {agent_scratchpad}"""

agent_prompt = PromptTemplate(
    template=AGENT_PROMPT,
    # --- 修正：移除 'tool_names' ---
    input_variables=["input", "chat_history", "agent_scratchpad", "tools"]
)

# 創建 Agent
try:
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=agent_prompt
    )
    logger.info("✅ ReAct Agent 創建成功")
except Exception as agent_create_err:
    logger.error(f"❌ 創建 Agent 失敗: {agent_create_err}", exc_info=True)
    agent = None # 標記 Agent 創建失敗

# ==================== Pydantic 模型 ====================
# (保持不變)
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    use_agent: bool = True

class ChatResponse(BaseModel):
    reply: str
    sources: Optional[List[str]] = []
    session_id: str
    timestamp: str
    thought_process: Optional[str] = None # 改為字串以容納錯誤訊息或步驟

class ContentGenerationRequest(BaseModel):
    topic: str
    style: str = "正式"
    length: str = "中"
    context: Optional[str] = None

class IngestRequest(BaseModel):
    folder_path: str = "documents"

# ==================== 工具函數 ====================
# (保持不變)
def verify_admin(authorization: Optional[str] = Header(None)):
    """驗證管理員權限"""
    # 實際應用應使用更安全的驗證方式
    if not ADMIN_PASSWORD or authorization != f"Bearer {ADMIN_PASSWORD}":
        logger.warning(f"🚫 管理員權限驗證失敗: {authorization}")
        raise HTTPException(status_code=401, detail="未授權或未設定管理員密碼")
    return True

def load_document(file_path: str):
    """載入文件"""
    file_extension = Path(file_path).suffix.lower()
    loader = None
    try:
        if file_extension == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_extension in [".docx", ".doc"]:
            # 確保已安裝 python-docx 和 docx2txt
            try:
                import docx2txt # 檢查是否安裝
                loader = Docx2txtLoader(file_path)
            except ImportError:
                logger.error("❌ 缺少 'docx2txt' 模組，無法讀取 .docx 文件。請執行 'pip install docx2txt'")
                return []
        elif file_extension == ".txt":
            # 嘗試用 utf-8 開啟，失敗則嘗試系統預設編碼
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                # 嘗試讀取一小部分以觸發可能的解碼錯誤
                loader.load()[0].page_content[:10]
            except UnicodeDecodeError:
                logger.warning(f"⚠️ 使用 UTF-8 讀取 {file_path} 失敗，嘗試系統預設編碼...")
                loader = TextLoader(file_path) # 使用系統預設
            except Exception as txt_err: # 捕捉其他可能的讀取錯誤
                 logger.error(f"❌ 讀取 TXT 文件 {file_path} 時發生非預期的錯誤: {txt_err}")
                 return []

        else:
            logger.warning(f"⚠️ 不支援的檔案類型: {file_extension} ({file_path})")
            return []

        if loader:
            documents = loader.load()
            logger.info(f"✅ 成功載入: {file_path} ({len(documents)} 段)")
            return documents
        else:
            return []
    except Exception as e:
        logger.error(f"❌ 載入文件 {file_path} 失敗: {e}", exc_info=True)
        return []

# ==================== Prompt 模板 ====================
# (保持不變)
RAG_PROMPT = PromptTemplate(
    template="""你是市長的 AI 助理，請根據以下資料回答問題。

相關資料：
{context}

對話記錄：
{chat_history}

問題：{question}

回答時請：
- 使用市長親切、專業的語氣
- 如果資料中沒有答案，請誠實告知
- 保持簡潔明瞭
- 適時使用輕鬆的語氣

回答：""",
    input_variables=["context", "chat_history", "question"]
)

CONTENT_PROMPT = PromptTemplate(
    template="""你是市長的專屬文案生成助理。

任務：生成 {style} 風格、{length} 篇幅的文案

主題：{topic}

參考資料：
{context}

要求：
- 完全模仿市長的語氣和用詞習慣
- 風格：{style}（正式/輕鬆/幽默）
- 篇幅：{length}（短=50-100字，中=150-300字，長=400-600字）
- 內容必須基於知識庫資訊
- 避免虛假內容

文案內容：""",
    input_variables=["topic", "style", "length", "context"]
)

# ==================== API 端點 ====================

@app.get("/")
async def root():
    # ... (保持不變)
    return {
        "system": "PAIS 政務分身智能系統",
        "version": app.version,
        "framework": "LangChain (Agents + Memory + RAG + Tools)",
        "status": "🟢 運行中"
    }

@app.get("/health")
async def health_check():
    # ... (保持不變)
    qdrant_ok = False
    llm_ok = False
    agent_ok = agent is not None
    error_msg = ""
    try:
        qdrant_client.get_collections()
        qdrant_ok = True
    except Exception as e:
        error_msg += f"Qdrant 連接失敗: {e}; "
        logger.error(f"❌ 健康檢查 - Qdrant 連接失敗: {e}")

    # 暫時假設 LLM 正常，避免 API Key 消耗
    llm_ok = True


    status = "healthy" if qdrant_ok and llm_ok and agent_ok else "unhealthy"

    return {
        "status": status,
        "qdrant": "✅ connected" if qdrant_ok else "❌ disconnected",
        "llm": "✅ assumed ok" if llm_ok else "❌ failed test",
        "agents": "✅ active" if agent_ok else "❌ failed to create",
        "error": error_msg if error_msg else None
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    對話 API (LangChain Agent + Memory 或 RAG Chain)
    """
    reply: str = "哎呀，善寶好像有點累了，或是網路不太穩定，請稍後再試一次喔！"
    sources: List[str] = []
    thought_process_str: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    session_id = request.session_id or "default"

    try:
        logger.info(f"💬 [{session_id}] 收到問題: {request.message}")

        if not agent and request.use_agent:
             logger.error(f"❌ Agent 未成功初始化，無法處理 Agent 請求 ({session_id})")
             raise HTTPException(status_code=500, detail="系統 Agent 元件啟動失敗，請稍後再試。")

        memory = get_memory(session_id)

        if request.use_agent:
            # --- 為 Agent 動態設定 output_key ---
            memory.output_key = "output"

            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=memory,
                verbose=True, # 保留詳細日誌以供除錯
                # --- 增加 Agent 執行次數 ---
                max_iterations=5, # 從 3 增加到 5
                handle_parsing_errors=True, # 繼續處理可能的 LLM 格式錯誤
            )

            logger.info(f"🚀 [{session_id}] 開始執行 Agent...")
            result = agent_executor.invoke({"input": request.message})
            logger.info(f"✅ [{session_id}] Agent 執行完成")

            # Agent 的回覆固定在 'output'
            reply = result.get("output", reply) # 使用 get 並提供預設值

            # 嘗試提取思考過程 (注意：intermediate_steps 可能很長)
            intermediate_steps = result.get("intermediate_steps")
            if intermediate_steps:
                 # 轉換為較易讀的字串格式，只取部分關鍵資訊
                 try:
                     thought_process_str = "\n---\n".join([
                         f"Thought: {step[0].log.strip()}\nAction: {step[0].tool}({step[0].tool_input})\nObservation: {str(step[1])[:200]}..." # 限制 Observation 長度
                         for step in intermediate_steps
                     ])
                 except Exception as fmt_err:
                     logger.warning(f"⚠️ 無法格式化 intermediate_steps: {fmt_err}")
                     thought_process_str = str(intermediate_steps)[:1000] + "..." # 截斷原始字串
            else:
                 thought_process_str = "Agent 未使用工具或無中間步驟記錄。"

            # Agent 目前不直接回傳 sources，但可以從思考過程中提取
            sources = [] # 暫時不處理

        else: # 使用 RAG Chain
            # --- 為 RAG 鏈動態設定 output_key ---
            memory.output_key = "answer"

            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
                memory=memory,
                combine_docs_chain_kwargs={"prompt": RAG_PROMPT},
                return_source_documents=True,
                verbose=True # RAG Chain 也開啟詳細日誌
            )

            logger.info(f"🚀 [{session_id}] 開始執行 RAG Chain...")
            result = qa_chain.invoke({"question": request.message})
            logger.info(f"✅ [{session_id}] RAG Chain 執行完成")

            reply = result.get("answer", reply) # RAG chain 的回覆在 'answer'
            thought_process_str = "使用 RAG Chain 模式，無 ReAct 思考過程。"
            sources = [
                doc.metadata.get("source", "未知來源").split('/')[-1] # 只取檔名
                for doc in result.get("source_documents", [])
            ]

        logger.info(f"🤖 [{session_id}] 最終回覆 (前100字): {reply[:100]}...")

        return ChatResponse(
            reply=reply,
            sources=list(set(sources)), # 去重
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            thought_process=thought_process_str # 回傳思考過程字串
        )

    except Exception as e:
        # 增加 exc_info=True 來獲取更詳細的錯誤堆疊
        logger.error(f"❌ 對話處理失敗 ({session_id}): {e}", exc_info=True)

        # 錯誤時也嘗試記錄最後的 result (如果有的話)
        error_thought_process = f"錯誤: {str(e)}"
        if result:
            error_thought_process += f"\n最後的 Agent/Chain 結果: {str(result)[:500]}..."

        # 'reply' 已經有預設的錯誤訊息了
        return ChatResponse(
            reply=reply, # 回傳預設的錯誤訊息
            sources=[],
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            thought_process=error_thought_process # 回傳錯誤詳情
        )

# --- /api/generate 保持不變 ---
@app.post("/api/generate")
async def generate_content(
    request: ContentGenerationRequest,
    admin: bool = Depends(verify_admin)
):
    """文案生成 API"""
    try:
        logger.info(f"✍️ 開始生成文案: 主題='{request.topic}', 風格='{request.style}', 長度='{request.length}'")

        context = "（無特別指定的參考資料）"
        relevant_docs = []
        if request.context: # 如果前端有指定特定來源（未來可擴充）
             logger.info(f"🔍 使用指定 context 進行生成")
             context = request.context
        else: # 預設從向量庫找相關資料
            try:
                retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
                logger.info(f"🔍 從知識庫搜尋主題 '{request.topic}' 的參考資料...")
                relevant_docs = retriever.invoke(request.topic) # 使用 invoke
                if relevant_docs:
                    context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
                    logger.info(f"✅ 找到 {len(relevant_docs)} 筆參考資料")
                else:
                    logger.warning(f"⚠️ 未找到主題 '{request.topic}' 的相關參考資料")
            except Exception as search_err:
                 logger.error(f"❌ 搜尋參考資料時失敗: {search_err}")

        content_chain = LLMChain(
            llm=llm,
            prompt=CONTENT_PROMPT,
            verbose=True
        )

        logger.info(f"🚀 開始調用 LLM 生成文案...")
        result = content_chain.invoke({
            "topic": request.topic,
            "style": request.style,
            "length": request.length,
            "context": context
        })

        generated_content = result.get("text", "").strip()

        if not generated_content:
             logger.error("❌ LLM 返回了空的文案內容")
             raise HTTPException(status_code=500, detail="文案生成失敗：模型未返回有效內容")

        logger.info(f"✅ 文案生成成功 (長度: {len(generated_content)})")

        # --- 自動儲存生成的文案 ---
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 清理 topic 作為檔名一部分
            safe_topic = "".join(c if c.isalnum() else "_" for c in request.topic[:20])
            output_file = Path("generated_content") / f"{timestamp}_{safe_topic}.txt"
            output_file.parent.mkdir(exist_ok=True) # 確保目錄存在

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"主題: {request.topic}\n")
                f.write(f"風格: {request.style}\n")
                f.write(f"篇幅: {request.length}\n")
                f.write(f"時間: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                f.write(generated_content)
            logger.info(f"💾 文案已自動儲存至: {output_file}")
            file_path_str = str(output_file)
        except Exception as save_err:
            logger.error(f"❌ 自動儲存文案失敗: {save_err}")
            file_path_str = None # 儲存失敗

        return {
            "content": generated_content,
            "file_path": file_path_str, # 回傳儲存路徑
            "sources": [
                 doc.metadata.get("source", "未知來源").split('/')[-1] # 只取檔名
                 for doc in relevant_docs # 使用前面搜尋到的 docs
            ],
            "context_used": len(relevant_docs) > 0 # 是否使用了知識庫 context
        }

    except HTTPException as http_exc:
        raise http_exc # 把 HTTP 錯誤直接拋出
    except Exception as e:
        logger.error(f"❌ 文案生成過程中發生未預期錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文案生成失敗: {str(e)}")


# --- /api/ingest, /api/upload 保持不變 ---
@app.post("/api/ingest")
async def ingest_documents(
    request: IngestRequest,
    admin: bool = Depends(verify_admin)
):
    """知識庫上傳 API (處理指定資料夾內所有支援文件)"""
    processed_files_count = 0
    total_chunks_created = 0
    errors = []

    try:
        folder_path = Path(request.folder_path)
        if not folder_path.exists() or not folder_path.is_dir():
            logger.error(f"❌ Ingest - 資料夾不存在或不是有效目錄: {folder_path}")
            raise HTTPException(status_code=404, detail=f"資料夾 '{folder_path}' 不存在")

        supported_extensions = [".pdf", ".docx", ".doc", ".txt"]
        logger.info(f"📚 開始處理資料夾: {folder_path}")

        # 使用 rglob 遞迴搜尋
        files_to_process = [f for f in folder_path.rglob("*")
                            if f.is_file() and f.suffix.lower() in supported_extensions]

        if not files_to_process:
            logger.warning(f"⚠️ 資料夾 '{folder_path}' 中沒有找到支援的檔案 ({supported_extensions})")
            return {"message": "資料夾中沒有找到支援的檔案", "processed": 0, "chunks_created": 0}

        logger.info(f"🔍 找到 {len(files_to_process)} 個支援的檔案，開始載入與分割...")

        all_splits = []
        for file_path in files_to_process:
            logger.debug(f"⏳ 處理檔案: {file_path}")
            docs = load_document(str(file_path))
            if docs:
                for doc in docs:
                    # 標準化 source 路徑
                    relative_path = file_path.relative_to(Path.cwd()) # 相對於目前工作目錄的路徑
                    doc.metadata["source"] = str(relative_path).replace("\\", "/") # 統一使用 /
                    doc.metadata["uploaded_at"] = datetime.now().isoformat()
                    doc.metadata["filename"] = file_path.name

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    separators=["\n\n", "\n", "。", "！", "？", "，", "、", " ", ""], # 加入中文標點
                    length_function=len,
                    # add_start_index = True # 可選，增加起始索引元數據
                )
                splits = text_splitter.split_documents(docs)
                logger.info(f"📄 檔案 {file_path.name} 分割成 {len(splits)} 個片段")
                all_splits.extend(splits)
                processed_files_count += 1
            else:
                 logger.warning(f"⚠️ 檔案 {file_path} 載入失敗或無內容，已跳過")
                 errors.append(f"無法處理檔案: {file_path.name}")


        if not all_splits:
            logger.error("❌ 無法從任何檔案中成功分割出片段")
            return {"message": "無法成功處理任何文件內容", "processed": processed_files_count, "chunks_created": 0, "errors": errors}

        total_chunks_created = len(all_splits)
        logger.info(f"✅ 文件分割完成: 共 {processed_files_count} 個檔案, {total_chunks_created} 個片段。準備寫入向量資料庫...")

        # 分批寫入 Qdrant，避免一次傳輸過大 payload
        batch_size = 100
        for i in range(0, total_chunks_created, batch_size):
            batch = all_splits[i:i + batch_size]
            try:
                vectorstore.add_documents(batch)
                logger.info(f"✍️ 已寫入 {len(batch)} 個片段 (總進度: {min(i + batch_size, total_chunks_created)} / {total_chunks_created})")
            except Exception as add_doc_err:
                 logger.error(f"❌ 寫入片段 {i} 到 {i+batch_size} 時失敗: {add_doc_err}", exc_info=True)
                 errors.append(f"部分資料寫入失敗: {add_doc_err}")
                 # raise HTTPException(status_code=500, detail=f"部分資料寫入向量資料庫失敗: {add_doc_err}") # 中斷

        logger.info(f"✅ 所有片段已成功寫入向量資料庫 '{COLLECTION_NAME}'")

        return {
            "message": "✅ 知識庫更新成功" + (f" (部分檔案處理失敗，請查看日誌)" if errors else ""),
            "files_processed": processed_files_count,
            "chunks_created": total_chunks_created,
            "collection": COLLECTION_NAME,
            "errors": errors if errors else None
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"❌ 知識庫上傳過程中發生未預期錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"知識庫處理失敗: {str(e)}")

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    admin: bool = Depends(verify_admin)
):
    """單個檔案上傳並直接加入知識庫"""
    try:
        # --- 儲存上傳的檔案 ---
        upload_folder = Path("documents")
        upload_folder.mkdir(exist_ok=True)
        file_path = upload_folder / Path(file.filename).name

        # 檢查檔名衝突，如果存在則加上 timestamp
        if file_path.exists():
             timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
             file_path = upload_folder / f"{file_path.stem}_{timestamp}{file_path.suffix}"

        logger.info(f"📤 接收到檔案上傳: {file.filename}, 儲存至: {file_path}")

        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            logger.info(f"💾 檔案儲存成功: {file_path}")
        except Exception as save_err:
             logger.error(f"❌ 儲存上傳檔案失敗 ({file.filename}): {save_err}", exc_info=True)
             raise HTTPException(status_code=500, detail=f"儲存檔案失敗: {save_err}")

        # --- 處理檔案並加入知識庫 (類似 ingest) ---
        logger.info(f"📚 開始處理單一檔案: {file_path}")
        docs = load_document(str(file_path))

        if not docs:
            logger.warning(f"⚠️ 檔案 {file_path} 載入失敗或無內容，無法加入知識庫")
            return {
                "message": "檔案已成功上傳，但無法讀取內容或內容為空，未加入知識庫。",
                "filename": file.filename,
                "chunks": 0,
                "error": "Failed to load or empty document"
            }

        for doc in docs:
            relative_path = file_path.relative_to(Path.cwd())
            doc.metadata["source"] = str(relative_path).replace("\\", "/")
            doc.metadata["uploaded_at"] = datetime.now().isoformat()
            doc.metadata["filename"] = file_path.name

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "！", "？", "，", "、", " ", ""],
            length_function=len
        )
        splits = text_splitter.split_documents(docs)
        total_chunks = len(splits)
        logger.info(f"📄 檔案 {file_path.name} 分割成 {total_chunks} 個片段")

        if not splits:
             logger.warning(f"⚠️ 檔案 {file_path.name} 分割後無片段，無法加入知識庫")
             return {
                "message": "檔案已成功上傳，但分割後無有效內容，未加入知識庫。",
                "filename": file.filename,
                "chunks": 0,
                "error": "No chunks generated after splitting"
            }

        try:
            vectorstore.add_documents(splits)
            logger.info(f"✅ 檔案 {file_path.name} 的片段已成功加入向量資料庫")
            return {
                "message": "✅ 檔案上傳並成功加入知識庫",
                "filename": file.filename,
                "chunks": total_chunks
            }
        except Exception as add_doc_err:
            logger.error(f"❌ 將檔案 {file_path.name} 加入向量資料庫時失敗: {add_doc_err}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"加入知識庫失敗: {add_doc_err}")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"❌ 處理檔案上傳時發生未預期錯誤 ({file.filename}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"檔案上傳處理失敗: {str(e)}")


# --- 其他 API 保持不變 ---
@app.get("/api/memory/{session_id}")
async def get_memory_history(session_id: str):
    """取得指定 session 的對話記憶"""
    try:
        if session_id not in memory_store:
            history_file = Path(f"chat_history/{session_id}.json")
            if not history_file.exists():
                logger.warning(f"⚠️ 請求記憶體歷史，但 session '{session_id}' 不存在 (記憶體與檔案皆無)")
                raise HTTPException(status_code=404, detail="找不到此對話記錄")
            else:
                 get_memory(session_id)

        memory = memory_store[session_id]
        history_data = memory.load_memory_variables({})
        messages = history_data.get("chat_history", [])
        formatted_history = []
        for msg in messages:
            msg_type = "user" if msg.type == "human" else "ai" if msg.type == "ai" else "system"
            formatted_history.append({
                "type": msg_type,
                "content": msg.content
            })

        logger.info(f"✅ 成功取得 session '{session_id}' 的對話歷史 ({len(formatted_history)} 條)")
        return {
            "session_id": session_id,
            "history": formatted_history
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"❌ 取得對話歷史失敗 ({session_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"無法取得對話記錄: {str(e)}")

@app.delete("/api/memory/{session_id}")
async def clear_memory(session_id: str, admin: bool = Depends(verify_admin)):
    """清除指定 session 的對話記憶 (記憶體與檔案)"""
    try:
        deleted_from_memory = False
        deleted_from_file = False

        if session_id in memory_store:
            try:
                memory_store[session_id].clear()
                del memory_store[session_id]
                deleted_from_memory = True
                logger.info(f"🗑️ 已從記憶體中清除 session: {session_id}")
            except Exception as mem_clear_err:
                 logger.error(f"❌ 清除記憶體中 session '{session_id}' 失敗: {mem_clear_err}")

        history_file = Path(f"chat_history/{session_id}.json")
        if history_file.exists():
            try:
                history_file.unlink()
                deleted_from_file = True
                logger.info(f"🗑️ 已刪除對話歷史檔案: {history_file}")
            except OSError as file_del_err:
                logger.error(f"❌ 刪除對話歷史檔案 '{history_file}' 失敗: {file_del_err}")

        if deleted_from_memory or deleted_from_file:
            return {"message": f"✅ 已清除 {session_id} 的對話記憶" + (" (部分失敗，請查看日誌)" if not (deleted_from_memory and deleted_from_file) else "")}
        else:
            logger.warning(f"⚠️ 嘗試清除 session '{session_id}'，但記憶體與檔案皆不存在或刪除失敗")
            raise HTTPException(status_code=404, detail="找不到或無法清除指定的對話記錄")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"❌ 清除對話記憶時發生未預期錯誤 ({session_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清除記憶失敗: {str(e)}")


@app.get("/api/stats")
async def get_stats():
    """取得系統統計資訊"""
    try:
        vector_count = -1
        try:
            collection_info = qdrant_client.get_collection(COLLECTION_NAME)
            vector_count = collection_info.vectors_count
        except Exception as q_err:
             logger.error(f"❌ 無法從 Qdrant 取得集合資訊: {q_err}")

        return {
            "collection_name": COLLECTION_NAME,
            "total_vectors": vector_count,
            "active_memory_sessions": len(memory_store),
            "total_history_files": len(list(Path("chat_history").glob("*.json"))),
            "framework": "LangChain",
            "llm_model": llm.model,
            "embedding_model": embeddings.model_name,
            "vector_db": "Qdrant",
            "components": {
                "agents": "✅ ReAct Agent" if agent else "❌ Agent Failed",
                "memory": "✅ ConversationBufferMemory + FileChatMessageHistory",
                "rag": "✅ ConversationalRetrievalChain",
                "tools": len(tools)
            }
        }
    except Exception as e:
        logger.error(f"❌ 取得系統統計時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"無法取得系統統計: {str(e)}")

# --- 啟動與關閉事件保持不變 ---
@app.on_event("startup")
async def startup_event():
    # 確保所有需要的目錄都存在
    Path("chat_history").mkdir(exist_ok=True)
    Path("generated_content").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("documents").mkdir(exist_ok=True)

    logger.info("="*50)
    logger.info("🚀 PAIS 系統啟動 (LangChain Powered)")
    logger.info(f" FastAPI 版本: {app.version}")
    logger.info(f"📍 Qdrant Host: {QDRANT_HOST}:{QDRANT_PORT}")
    logger.info(f"📚 Qdrant 集合: {COLLECTION_NAME}")
    logger.info(f"🧠 LLM 模型: {llm.model}")
    logger.info(f"🔡 Embedding 模型: {embeddings.model_name} (維度: 768)")
    logger.info(f"🤖 Agent 狀態: {'✅ 已啟用' if agent else '❌ 啟動失敗'}")
    logger.info(f"🛠️ Agent 工具數量: {len(tools)}")
    logger.info(f"💾 Memory 類型: ConversationBufferMemory + FileChatMessageHistory")
    logger.info("="*50)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("="*50)
    logger.info("⏹ PAIS 系統正在關閉...")
    # 可以在這裡加入資源清理的程式碼，例如關閉資料庫連接
    logger.info("="*50)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)