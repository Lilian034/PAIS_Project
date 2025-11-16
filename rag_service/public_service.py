import os
import json
import re # 匯入正規表達式模組
import ssl
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

# 臨時繞過 SSL 證書驗證問題（用於網路環境有代理或防火牆的情況）
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header, Form
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

# 載入數據庫輔助類
from utils.db_helper import StaffDatabase

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
    version="2.0.6" # 版本更新
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

vectorstore = Qdrant(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embeddings=embeddings
)

# ==================== 訪客計數器數據庫 ====================
db = StaffDatabase()

# ==================== LangChain Memory 管理 ====================
memory_store: Dict[str, ConversationBufferMemory] = {}

def get_memory(session_id: str) -> ConversationBufferMemory:
    """取得或建立對話記憶"""
    if session_id not in memory_store:
        try:
            Path("chat_history").mkdir(exist_ok=True)
            history_file = f"chat_history/{session_id}.json"
            message_history = FileChatMessageHistory(history_file)

            memory_store[session_id] = ConversationBufferMemory(
                chat_memory=message_history,
                memory_key="chat_history",
                return_messages=True
            )
            logger.info(f"🧠 建立新記憶: {session_id} (檔案: {history_file})")
        except Exception as mem_err:
            logger.error(f"❌ 建立記憶體失敗 ({session_id}): {mem_err}")
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
            # 只取 page_content，避免 metadata 過長
            result = "\n\n".join([doc.page_content for doc in docs])
            logger.info(f"✅ 工具 [搜尋知識庫] 找到 {len(docs)} 筆資料")
            # 限制回傳給 Agent 的長度，避免 Prompt 過長
            max_obs_length = 1500 
            if len(result) > max_obs_length:
                 result = result[:max_obs_length] + "... (內容過長截斷)"
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
        docs = vectorstore.similarity_search(policy_name, k=1) # 只取最相關的 1 筆
        if docs:
            result = docs[0].page_content
            logger.info(f"✅ 工具 [查詢政策] 找到資料 for policy: {policy_name}")
            # 限制回傳給 Agent 的長度
            max_obs_length = 1500
            if len(result) > max_obs_length:
                 result = result[:max_obs_length] + "... (內容過長截斷)"
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

# --- 再次修正 Agent Prompt，強化 Final Answer 格式要求 ---
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
**工具名稱列表 (你不需要在回答中使用這個列表):**
{tool_names}

**你【必須嚴格】遵守以下的思考與回應格式 (ReAct 格式)：**
Question: 使用者提出的問題。
Thought: [你的思考過程，說明你打算做什麼]。
Action: [你選擇的工具名稱，例如：搜尋知識庫]。 **【只有在你需要使用工具時才寫這行和下一行】**
Action Input: [提供給工具的輸入，例如：桃園市社會住宅進度]。
Observation: [工具返回的結果。這會由系統自動填入]。
Thought: [檢視 Observation 後的思考，判斷是否需要再次使用工具，或可以直接回答]。
... (可以重複 Action/Action Input/Observation/Thought 流程) ...
Thought: 我現在已經有足夠的資訊，可以給出最終的答案了。 **【在給出最終答案前，必須有這句 Thought】**
Final Answer: [**這裡【直接】寫出**你最終要給使用者的【完整回覆內容】，**【只需要】**包含最終答案本身，**【絕對不要】**包含任何前面的 Thought, Action, Action Input, Observation 文字。回答要自然、完整，符合市長口吻。]

**【再次強調最終格式】：**
你的整個輸出流的【最後一部分】**必須**是：
Thought: 我現在已經有足夠的資訊，可以給出最終的答案了。
Final Answer: [市長口吻的完整回答內容...]

**【錯誤示範】(不要這樣做！)：**
Thought: 我需要查資料。
Action: 搜尋知識庫
Action Input: 交通
Observation: 找到資料...
Thought: 我知道了。
Final Answer: Thought: 我知道了。\n市民您好，交通政策是...  <--- **這是錯的！Final Answer 裡包含了 Thought！**

**【正確示範】：**
Thought: 我需要查資料。
Action: 搜尋知識庫
Action Input: 交通政策
Observation: 找到資料...
Thought: 我現在已經有足夠的資訊，可以給出最終的答案了。
Final Answer: 市民您好！桃園的交通建設是市府團隊非常重視的一環。根據我找到的資料...... <--- **這是對的！只有乾淨的回答。**

**對話記錄 (最近的對話)：**
{chat_history}

**開始！**

Question: {input}
Thought: {agent_scratchpad}"""

# 幕僚專用 Agent Prompt（資料校稿專用 - 不拟稿，只校對）
STAFF_AGENT_PROMPT = """你是市府幕僚的專業校對助理，專門協助文稿校對、資料核實和錯誤檢查。你的任務是根據提供的工具和對話記錄，提供專業、準確的校對意見。

**你的核心任務：**
1. **矯正專有詞翻譯錯誤** - 檢查專有名詞、地名、人名是否正確
2. **檢查專業知識轉譯** - 確認專業術語、政策名稱是否準確
3. **事實核實** - 使用知識庫工具核對數據、日期、政策內容
4. **語法檢查** - 指出語法錯誤、用詞不當
5. **風格建議** - 提供文字優化建議

**你的身份：**
- 專業校對助理，使用「我」自稱
- **不是拟稿人員**，不需要生成新內容
- **不要自稱善寶或市長**

**你的回答方式：**
當幕僚貼上文稿請你校對時，你應該：
1. 指出發現的錯誤（專有詞、翻譯、事實、語法）
2. 提供正確的版本或建議
3. 如需核實事實，使用知識庫工具查詢
4. 回答要清晰、有條理、易於理解

**範例說明：**
幕僚貼上：「市長今天到松山機場視察，共建設了50座社會住宅。」

✅ 正確的校對回應：
「我發現以下需要修正的地方：
1. 地名錯誤：應為『桃園國際機場』，不是松山機場
2. 數據需核實：讓我查詢知識庫...（使用工具）
   根據知識庫資料，桃園市規劃的社會住宅數量為 X 座，請確認此數字」

❌ 錯誤（開始拟稿）：
「我為您重新擬寫：各位市民朋友...」

**可用工具：**
{tools}
**工具名稱列表 (你不需要在回答中使用這個列表):**
{tool_names}

**你【必須嚴格】遵守以下的思考與回應格式 (ReAct 格式)：**
Question: 使用者提出的問題。
Thought: [你的思考過程，說明你打算做什麼]。
Action: [你選擇的工具名稱，例如：搜尋知識庫]。 **【只有在你需要使用工具時才寫這行和下一行】**
Action Input: [提供給工具的輸入]。
Observation: [工具返回的結果。這會由系統自動填入]。
Thought: [檢視 Observation 後的思考，判斷是否需要再次使用工具，或可以直接回答]。
... (可以重複 Action/Action Input/Observation/Thought 流程) ...
Thought: 我現在已經有足夠的資訊，可以給出最終的答案了。 **【在給出最終答案前，必須有這句 Thought】**
Final Answer: [**這裡【直接】寫出**你最終要給使用者的【完整回覆內容】，**【只需要】**包含最終答案本身，**【絕對不要】**包含任何前面的 Thought, Action, Action Input, Observation 文字。]

**對話記錄 (最近的對話)：**
{chat_history}

**開始！**

Question: {input}
Thought: {agent_scratchpad}"""


agent_prompt = PromptTemplate(
    template=AGENT_PROMPT,
    input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"]
)

staff_agent_prompt = PromptTemplate(
    template=STAFF_AGENT_PROMPT,
    input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"]
)

# 創建 Agent（公眾版 - 善寶）
try:
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=agent_prompt
    )
    logger.info("✅ ReAct Agent (公眾版) 創建成功")
except Exception as agent_create_err:
    try:
        logger.error(f"❌ 創建 Agent 失敗: {str(agent_create_err)}", exc_info=True)
    except Exception as log_err:
        logger.error(f"❌ 創建 Agent 失敗，且 Logger 也發生錯誤: {log_err}")
    agent = None

# 創建 Staff Agent（幕僚版）
try:
    staff_agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=staff_agent_prompt
    )
    logger.info("✅ ReAct Agent (幕僚版) 創建成功")
except Exception as staff_agent_create_err:
    try:
        logger.error(f"❌ 創建 Staff Agent 失敗: {str(staff_agent_create_err)}", exc_info=True)
    except Exception as log_err:
        logger.error(f"❌ 創建 Staff Agent 失敗，且 Logger 也發生錯誤: {log_err}")
    staff_agent = None

# ==================== Pydantic 模型 ====================
# (保持不變)
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    use_agent: bool = True
    role: str = "public"  # "public" 或 "staff"，決定 AI 的身份

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

class VisitorStatsResponse(BaseModel):
    month: str
    count: int
    last_reset: str

# ==================== 工具函數 ====================
# (保持不變)
def verify_admin(authorization: Optional[str] = Header(None)):
    """驗證管理員權限"""
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
            try:
                import docx2txt # 檢查是否安裝
                loader = Docx2txtLoader(file_path)
            except ImportError:
                logger.error("❌ 缺少 'docx2txt' 模組，無法讀取 .docx 文件。請執行 'pip install docx2txt'")
                return []
        elif file_extension == ".txt":
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                loader.load()[0].page_content[:10]
            except UnicodeDecodeError:
                logger.warning(f"⚠️ 使用 UTF-8 讀取 {file_path} 失敗，嘗試系統預設編碼...")
                loader = TextLoader(file_path) # 使用系統預設
            except Exception as txt_err:
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

# --- 新增：清理 Agent 輸出的函數 ---
def extract_final_answer(agent_output: str) -> str:
    """從 Agent 的原始輸出中提取 Final Answer 部分"""
    if not agent_output: # 檢查空字串
        return ""

    logger.debug(f"原始 Agent 輸出 (前 500 字): {agent_output[:500]}...")

    # 使用 re.IGNORECASE (或 re.I) 忽略大小寫
    # 尋找最後一個 "Final Answer:"
    matches = list(re.finditer(r"Final Answer:\s*(.*)", agent_output, re.DOTALL | re.IGNORECASE))

    if matches:
        # 取最後一個匹配項之後的所有內容
        last_match = matches[-1]
        final_answer = agent_output[last_match.end(1):].strip() # 從 group(1) 結束後開始取
        # 如果 group(1) 本身就是答案 (沒有後續內容)
        if not final_answer and last_match.group(1):
            final_answer = last_match.group(1).strip()

        logger.debug(f"提取到的 Final Answer (前 200 字): {final_answer[:200]}...")

        # 再次檢查是否仍然包含 "Thought:" 或 "Action:" (LLM 可能不完全遵守)
        # 這裡的邏輯保持不變，嘗試做二次清理
        if "Thought:" in final_answer[:20] or "Action:" in final_answer[:20]:
             logger.warning("⚠️ Final Answer 中可能仍包含 Agent 思考過程，嘗試再次清理...")
             last_thought_match = list(re.finditer(r"Thought:", final_answer, re.IGNORECASE))
             last_action_match = list(re.finditer(r"Action:", final_answer, re.IGNORECASE))
             last_obs_match = list(re.finditer(r"Observation:", final_answer, re.IGNORECASE))

             last_marker_pos = -1
             if last_thought_match: last_marker_pos = max(last_marker_pos, last_thought_match[-1].start())
             if last_action_match: last_marker_pos = max(last_marker_pos, last_action_match[-1].start())
             if last_obs_match: last_marker_pos = max(last_marker_pos, last_obs_match[-1].start())

             if last_marker_pos != -1:
                  next_newline = final_answer.find('\n', last_marker_pos)
                  if next_newline != -1:
                       cleaned_answer = final_answer[next_newline:].strip()
                       if cleaned_answer:
                            logger.debug(f"二次清理後的 Answer (前 200 字): {cleaned_answer[:200]}...")
                            return cleaned_answer
                       else:
                            logger.warning("⚠️ 二次清理後答案為空，返回原始提取內容")
                            return final_answer
                  else:
                       return final_answer
             else:
                  return final_answer
        else: # 沒有包含其他標記，是乾淨的
             return final_answer
    else:
        # 如果找不到 "Final Answer:"
        logger.warning("⚠️ 未在 Agent 輸出中找到 'Final Answer:' 標記。")
        # 檢查是否 LLM 把答案直接放在最後一個 "Thought:" 之後
        thought_matches = list(re.finditer(r"Thought:(.*)", agent_output, re.IGNORECASE))
        if thought_matches:
            last_thought_content = thought_matches[-1].group(1).strip()
            # 檢查最後一個 Thought 後面是否緊接著 Action 或 Observation
            remaining_text = agent_output[thought_matches[-1].end():]
            if "Action:" not in remaining_text and "Observation:" not in remaining_text and len(last_thought_content) > 30: # 簡單判斷
                 logger.warning("⚠️ 嘗試使用最後一個 'Thought:' 後的內容作為答案。")
                 return last_thought_content

        logger.warning("⚠️ 無法可靠提取答案，返回原始輸出 (可能不完整或包含思考)。")
        return agent_output.strip() # 直接返回原始輸出


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
    return {
        "system": "PAIS 政務分身智能系統",
        "version": app.version,
        "framework": "LangChain (Agents + Memory + RAG + Tools)",
        "status": "🟢 運行中"
    }

@app.get("/health")
async def health_check():
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

    llm_ok = True # 暫時假設 LLM 正常

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
    支援不同角色：public (善寶) 或 staff (幕僚助理)
    """
    # 根據角色設置不同的預設錯誤訊息
    if request.role == "staff":
        reply: str = "抱歉，系統暫時無法回應，請稍後再試。"
    else:
        reply: str = "哎呀，善寶好像有點累了，或是網路不太穩定，請稍後再試一次喔！"

    sources: List[str] = []
    thought_process_str: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    session_id = request.session_id or "default"
    raw_agent_output: Optional[str] = None # 用於儲存 Agent 原始輸出

    try:
        logger.info(f"💬 [{session_id}] 收到問題 (角色: {request.role}): {request.message}")

        memory = get_memory(session_id)

        if request.use_agent:
            memory.output_key = "output"

            # 根據角色選擇預先創建的 agent
            if request.role == "staff":
                if not staff_agent:
                    logger.error(f"❌ Staff Agent 未成功初始化，無法處理幕僚請求 ({session_id})")
                    raise HTTPException(status_code=500, detail="幕僚系統 Agent 元件啟動失敗，請稍後再試。")
                current_agent = staff_agent
                logger.info(f"🎭 使用幕僚助理模式")
            else:
                if not agent:
                    logger.error(f"❌ Agent 未成功初始化，無法處理公眾請求 ({session_id})")
                    raise HTTPException(status_code=500, detail="系統 Agent 元件啟動失敗，請稍後再試。")
                current_agent = agent
                logger.info(f"🎭 使用善寶模式")

            agent_executor = AgentExecutor(
                agent=current_agent,
                tools=tools,
                memory=memory,
                verbose=True,
                max_iterations=5,
                handle_parsing_errors=True, # 讓 Agent 嘗試自我修正格式錯誤
            )

            logger.info(f"🚀 [{session_id}] 開始執行 Agent...")
            try:
                result = agent_executor.invoke({"input": request.message})
                raw_agent_output = result.get("output") # 取得原始輸出

                if raw_agent_output:
                     # --- 加入後處理：提取乾淨的 Final Answer ---
                     reply = extract_final_answer(raw_agent_output)
                     # 如果清理後是空的，或還是包含思考過程 (清理失敗)
                     if not reply or "Thought:" in reply[:20] or "Action:" in reply[:20]:
                         logger.warning(f"⚠️ 清理後 Final Answer 為空或仍包含思考，使用預設錯誤回覆 ({session_id})")
                         # 檢查原始輸出是否就是答案 (適用於 Agent 沒找到 Final Answer: 但直接回答)
                         # 並且原始輸出長度大於一定值，避免只是簡單的 "OK" 或錯誤訊息
                         if len(raw_agent_output) > 30 and "Thought:" not in raw_agent_output[:50]:
                              reply = raw_agent_output # 假設原始輸出就是答案
                         else:
                              reply = "抱歉，我好像有點詞窮了，可以換個方式問嗎？" # 維持預設錯誤
                else:
                     logger.warning(f"⚠️ Agent 執行結果中缺少 'output' ({session_id})")
                     # reply 會保持為預設錯誤訊息

            except Exception as agent_exec_err:
                 logger.error(f"❌ AgentExecutor.invoke 執行失敗 ({session_id}): {agent_exec_err}", exc_info=True)
                 reply = f"抱歉，我在處理您的問題時遇到了一些困難 ({type(agent_exec_err).__name__})。請您換個方式再問一次，或聯繫管理員。"
                 result = {"error": str(agent_exec_err)} # 記錄錯誤

            logger.info(f"✅ [{session_id}] Agent 執行完成 (或捕捉到錯誤)")

            # --- 思考過程改用原始輸出 ---
            if raw_agent_output:
                # 限制長度，避免傳給前端的資料過大
                thought_process_str = raw_agent_output[:2000] + ("..." if len(raw_agent_output) > 2000 else "")
            elif "error" in result:
                 thought_process_str = f"Agent 執行錯誤: {result['error'][:1000]}..."
            else:
                 thought_process_str = "Agent 未成功產生輸出。"

            # 從 Agent 的中間步驟提取工具使用記錄作為來源
            sources = []
            if "intermediate_steps" in result:
                for action, observation in result["intermediate_steps"]:
                    tool_name = action.tool if hasattr(action, 'tool') else '未知工具'
                    # 如果使用了知識庫工具，標記為來源
                    if tool_name in ["搜尋知識庫", "查詢特定政策名稱"]:
                        sources.append(f"{tool_name}")
                logger.info(f"📚 [{session_id}] 從 Agent 中間步驟提取到 {len(sources)} 個工具使用記錄")

            # 如果 sources 為空但有成功回覆，表示可能沒有使用工具
            if not sources and reply and reply != "抱歉，我好像有點詞窮了，可以換個方式問嗎？":
                sources = []  # 保持為空，表示未使用知識庫

        else: # 使用 RAG Chain
            memory.output_key = "answer"
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
                memory=memory,
                combine_docs_chain_kwargs={"prompt": RAG_PROMPT},
                return_source_documents=True,
                verbose=True
            )

            logger.info(f"🚀 [{session_id}] 開始執行 RAG Chain...")
            result = qa_chain.invoke({"question": request.message})
            logger.info(f"✅ [{session_id}] RAG Chain 執行完成")

            reply = result.get("answer", reply)
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
            thought_process=thought_process_str
        )

    # 主 try 區塊的 except
    except Exception as e:
        error_msg = str(e).replace('{', '{{').replace('}', '}}')  # 轉義大括號避免格式化錯誤
        logger.error(f"❌ 對話處理中發生未預期錯誤 ({session_id}): {error_msg}", exc_info=True)
        error_thought_process = f"系統層級錯誤: {error_msg}"
        if result and isinstance(result, dict):
            error_thought_process += f"\n最後的 Agent/Chain 結果: {str(result)[:500]}..."

        return ChatResponse(
            reply=reply,
            sources=[],
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            thought_process=error_thought_process
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
        if request.context:
             logger.info(f"🔍 使用指定 context 進行生成")
             context = request.context
        else:
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

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = "".join(c if c.isalnum() else "_" for c in request.topic[:20])
            output_file = Path("generated_content") / f"{timestamp}_{safe_topic}.txt"
            output_file.parent.mkdir(exist_ok=True)

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
            file_path_str = None

        return {
            "content": generated_content,
            "file_path": file_path_str,
            "sources": [
                 doc.metadata.get("source", "未知來源").split('/')[-1]
                 for doc in relevant_docs
            ],
            "context_used": len(relevant_docs) > 0
        }

    except HTTPException as http_exc:
        raise http_exc
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
                    relative_path = file_path.relative_to(Path.cwd())
                    doc.metadata["source"] = str(relative_path).replace("\\", "/")
                    doc.metadata["uploaded_at"] = datetime.now().isoformat()
                    doc.metadata["filename"] = file_path.name

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    separators=["\n\n", "\n", "。", "！", "？", "，", "、", " ", ""],
                    length_function=len,
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

        batch_size = 100
        for i in range(0, total_chunks_created, batch_size):
            batch = all_splits[i:i + batch_size]
            try:
                vectorstore.add_documents(batch)
                logger.info(f"✍️ 已寫入 {len(batch)} 個片段 (總進度: {min(i + batch_size, total_chunks_created)} / {total_chunks_created})")
            except Exception as add_doc_err:
                 logger.error(f"❌ 寫入片段 {i} 到 {i+batch_size} 時失敗: {add_doc_err}", exc_info=True)
                 errors.append(f"部分資料寫入失敗: {add_doc_err}")

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
    folder: str = Form(""),
    admin: bool = Depends(verify_admin)
):
    """單個檔案上傳並直接加入知識庫"""
    try:
        # 建立上傳目標資料夾
        upload_folder = Path("documents")
        if folder and folder.strip():
            # 清理資料夾路徑，防止路徑遍歷攻擊
            clean_folder = folder.strip().replace("..", "").replace("\\", "/")
            upload_folder = upload_folder / clean_folder

        upload_folder.mkdir(parents=True, exist_ok=True)
        file_path = upload_folder / Path(file.filename).name

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
            # 確保 file_path 是絕對路徑，然後計算相對於工作目錄的路徑
            abs_file_path = file_path.resolve()
            abs_cwd = Path.cwd().resolve()
            try:
                relative_path = abs_file_path.relative_to(abs_cwd)
            except ValueError:
                # 如果無法計算相對路徑，直接使用檔案路徑
                relative_path = file_path

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


@app.get("/api/documents")
async def list_documents(admin: bool = Depends(verify_admin)):
    """列出知識庫中的所有文檔"""
    try:
        docs_dir = Path("documents")
        if not docs_dir.exists():
            return {"documents": []}

        documents = []

        # 遍歷所有文件（包括子目錄）
        for file_path in docs_dir.rglob("*"):
            if file_path.is_file():
                try:
                    stat_info = file_path.stat()
                    relative_path = file_path.relative_to(docs_dir)

                    documents.append({
                        "filename": file_path.name,
                        "path": str(relative_path).replace("\\", "/"),
                        "full_path": str(file_path),
                        "size": stat_info.st_size,
                        "uploaded_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        "extension": file_path.suffix
                    })
                except Exception as file_err:
                    logger.warning(f"⚠️ 無法讀取文件資訊: {file_path}, 錯誤: {file_err}")
                    continue

        # 按上傳時間排序（新到舊）
        documents.sort(key=lambda x: x["uploaded_at"], reverse=True)

        logger.info(f"📂 列出文檔列表，共 {len(documents)} 個文件")
        return {
            "documents": documents,
            "total": len(documents)
        }
    except Exception as e:
        logger.error(f"❌ 列出文檔失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列出文檔失敗: {str(e)}")


@app.get("/api/documents/{file_path:path}/download")
async def download_document(file_path: str):
    """下載知識庫中的文檔（不需要密碼驗證，方便下載）"""
    try:
        from fastapi.responses import FileResponse

        docs_dir = Path("documents")
        target_file = docs_dir / file_path

        # 安全檢查：確保文件在 documents 目錄內
        try:
            target_file = target_file.resolve()
            docs_dir = docs_dir.resolve()
            if not str(target_file).startswith(str(docs_dir)):
                raise HTTPException(status_code=400, detail="不允許訪問此路徑")
        except Exception:
            raise HTTPException(status_code=400, detail="無效的文件路徑")

        if not target_file.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        if not target_file.is_file():
            raise HTTPException(status_code=400, detail="只能下載文件")

        logger.info(f"📥 下載文檔: {file_path}")

        return FileResponse(
            path=str(target_file),
            filename=target_file.name,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 下載文檔失敗 ({file_path}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下載文檔失敗: {str(e)}")


@app.delete("/api/documents/{file_path:path}")
async def delete_document(file_path: str, admin: bool = Depends(verify_admin)):
    """刪除知識庫中的文檔"""
    try:
        docs_dir = Path("documents")
        target_file = docs_dir / file_path

        # 安全檢查：確保文件在 documents 目錄內
        try:
            target_file = target_file.resolve()
            docs_dir = docs_dir.resolve()
            if not str(target_file).startswith(str(docs_dir)):
                raise HTTPException(status_code=400, detail="不允許訪問此路徑")
        except Exception:
            raise HTTPException(status_code=400, detail="無效的文件路徑")

        if not target_file.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        if not target_file.is_file():
            raise HTTPException(status_code=400, detail="只能刪除文件，不能刪除目錄")

        # 刪除文件
        filename = target_file.name
        target_file.unlink()
        logger.info(f"🗑️ 已刪除文檔: {file_path}")

        return {
            "message": f"✅ 已刪除文檔: {filename}",
            "filename": filename
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 刪除文檔失敗 ({file_path}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"刪除文檔失敗: {str(e)}")


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


# ==================== 訪客計數器 API ====================

@app.post("/api/visitor/increment", response_model=VisitorStatsResponse)
async def increment_visitor():
    """增加訪客計數"""
    try:
        stats = db.increment_visitor_count()
        return VisitorStatsResponse(
            month=stats['month'],
            count=stats['count'],
            last_reset=stats['last_reset']
        )
    except Exception as e:
        logger.error(f"❌ 增加訪客計數時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"無法增加訪客計數: {str(e)}")


@app.get("/api/visitor/stats", response_model=VisitorStatsResponse)
async def get_visitor_stats(month: Optional[str] = None):
    """取得訪客統計"""
    try:
        stats = db.get_visitor_stats(month)
        if stats:
            return VisitorStatsResponse(
                month=stats['month'],
                count=stats['count'],
                last_reset=stats['last_reset']
            )
        else:
            # 如果沒有數據，返回當月初始值
            from datetime import datetime
            current_month = month or datetime.now().strftime("%Y-%m")
            return VisitorStatsResponse(
                month=current_month,
                count=0,
                last_reset=datetime.now().isoformat()
            )
    except Exception as e:
        logger.error(f"❌ 取得訪客統計時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"無法取得訪客統計: {str(e)}")


@app.get("/api/visitor/total")
async def get_total_visitors():
    """取得總瀏覽數（所有月份累計）"""
    try:
        all_stats = db.get_all_visitor_stats(limit=999)  # 取得所有歷史記錄
        total = sum(stat['count'] for stat in all_stats)
        return {"total": total, "months_count": len(all_stats)}
    except Exception as e:
        logger.error(f"❌ 取得總瀏覽數時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"無法取得總瀏覽數: {str(e)}")


# --- 啟動與關閉事件保持不變 ---
@app.on_event("startup")
async def startup_event():
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
    logger.info("="*50)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)