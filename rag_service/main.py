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
    version="2.0.0"
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
    model="gemini-pro",
    google_api_key=GEMINI_API_KEY,
    temperature=0.7,
    max_output_tokens=2048
)

# Gemini Embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GEMINI_API_KEY
)

# 使用本地 HuggingFace Embeddings（免費，不需要 API）
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    model_kwargs={'device': 'cpu'}
)

# Qdrant 向量資料庫
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

try:
    qdrant_client.get_collection(COLLECTION_NAME)
    logger.info(f"✅ 集合 '{COLLECTION_NAME}' 已存在")
except Exception:
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
    logger.info(f"✅ 已建立新集合 '{COLLECTION_NAME}'")

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
        message_history = FileChatMessageHistory(f"chat_history/{session_id}.json")
        memory_store[session_id] = ConversationBufferMemory(
            chat_memory=message_history,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        logger.info(f"🧠 建立新記憶: {session_id}")
    return memory_store[session_id]

# ==================== LangChain Tools ====================

def search_knowledge_base(query: str) -> str:
    """搜尋知識庫工具"""
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.get_relevant_documents(query)
        if docs:
            result = "\n\n".join([doc.page_content for doc in docs])
            return f"找到相關資料：\n{result}"
        return "未找到相關資料"
    except Exception as e:
        return f"搜尋錯誤: {str(e)}"

def get_policy_info(policy_name: str) -> str:
    """取得政策資訊工具"""
    try:
        docs = vectorstore.similarity_search(policy_name, k=2)
        if docs:
            return f"政策資訊：{docs[0].page_content}"
        return f"未找到 '{policy_name}' 相關政策"
    except Exception as e:
        return f"查詢錯誤: {str(e)}"

def save_generated_content(content: str, topic: str) -> str:
    """儲存生成內容工具"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_content/{timestamp}_{topic[:20]}.txt"
        Path("generated_content").mkdir(exist_ok=True)
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        return f"✅ 內容已儲存至: {filename}"
    except Exception as e:
        return f"儲存失敗: {str(e)}"

# 定義 Agent 工具
tools = [
    Tool(
        name="搜尋知識庫",
        func=search_knowledge_base,
        description="當需要查詢市長的政策、理念、過往發言時使用。輸入：問題或關鍵字"
    ),
    Tool(
        name="查詢政策",
        func=get_policy_info,
        description="查詢特定政策的詳細資訊。輸入：政策名稱"
    ),
    Tool(
        name="儲存內容",
        func=save_generated_content,
        description="儲存生成的文案內容。輸入：內容文字,主題"
    )
]

# ==================== LangChain Agent 定義 ====================

AGENT_PROMPT = """你是市長的智能 AI 助理「善寶」，負責與民眾互動。

你的職責：
1. 使用市長親切、專業的語氣回答問題
2. 根據知識庫提供準確資訊
3. 保持對話的連貫性和記憶
4. 適時使用幽默感拉近距離

你可以使用以下工具：
{tools}

工具名稱：{tool_names}

使用格式：
Question: 輸入的問題
Thought: 思考如何回答
Action: 選擇使用的工具
Action Input: 工具的輸入
Observation: 工具的輸出
... (重複 Thought/Action/Observation 直到有答案)
Thought: 我現在知道最終答案了
Final Answer: 最終回答

對話記錄：
{chat_history}

開始！

Question: {input}
Thought: {agent_scratchpad}"""

agent_prompt = PromptTemplate(
    template=AGENT_PROMPT,
    input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"]
)

agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=agent_prompt
)

# ==================== Pydantic 模型 ====================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    use_agent: bool = True

class ChatResponse(BaseModel):
    reply: str
    sources: Optional[List[str]] = []
    session_id: str
    timestamp: str
    thought_process: Optional[str] = None

class ContentGenerationRequest(BaseModel):
    topic: str
    style: str = "正式"
    length: str = "中"
    context: Optional[str] = None

class IngestRequest(BaseModel):
    folder_path: str = "documents"

# ==================== 工具函數 ====================

def verify_admin(authorization: Optional[str] = Header(None)):
    """驗證管理員權限"""
    if authorization != f"Bearer {ADMIN_PASSWORD}":
        raise HTTPException(status_code=401, detail="未授權")
    return True

def load_document(file_path: str):
    """載入文件"""
    file_extension = Path(file_path).suffix.lower()
    
    try:
        if file_extension == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_extension in [".docx", ".doc"]:
            loader = Docx2txtLoader(file_path)
        elif file_extension == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
        else:
            logger.warning(f"不支援的檔案類型: {file_extension}")
            return []
        
        documents = loader.load()
        logger.info(f"✅ 載入: {file_path} ({len(documents)} 文件)")
        return documents
    except Exception as e:
        logger.error(f"❌ 載入失敗 {file_path}: {str(e)}")
        return []

# ==================== Prompt 模板 ====================

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
        "version": "2.0.0",
        "framework": "LangChain (Agents + Memory + RAG + Tools)",
        "status": "🟢 運行中"
    }

@app.get("/health")
async def health_check():
    """健康檢查"""
    try:
        qdrant_client.get_collections()
        return {
            "status": "healthy",
            "qdrant": "✅ connected",
            "llm": "✅ Gemini Pro",
            "agents": "✅ active"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    對話 API (LangChain Agent + Memory)
    """
    try:
        logger.info(f"💬 [{request.session_id}] 問題: {request.message}")
        
        memory = get_memory(request.session_id)
        
        if request.use_agent:
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=memory,
                verbose=True,
                max_iterations=3,
                handle_parsing_errors=True
            )
            
            result = agent_executor.invoke({"input": request.message})
            reply = result["output"]
            thought_process = result.get("intermediate_steps", "")
            sources = []
            
        else:
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
                memory=memory,
                combine_docs_chain_kwargs={"prompt": RAG_PROMPT},
                return_source_documents=True
            )
            
            result = qa_chain({"question": request.message})
            reply = result["answer"]
            thought_process = None
            sources = [doc.metadata.get("source", "未知") 
                      for doc in result.get("source_documents", [])]
        
        logger.info(f"✅ 回答: {reply[:100]}...")
        
        return ChatResponse(
            reply=reply,
            sources=sources,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            thought_process=str(thought_process) if thought_process else None
        )
        
    except Exception as e:
        logger.error(f"❌ 對話錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"處理失敗: {str(e)}")

@app.post("/api/generate")
async def generate_content(
    request: ContentGenerationRequest,
    admin: bool = Depends(verify_admin)
):
    """文案生成 API"""
    try:
        logger.info(f"✍️ 生成文案: {request.topic}")
        
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        relevant_docs = retriever.get_relevant_documents(request.topic)
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        content_chain = LLMChain(
            llm=llm,
            prompt=CONTENT_PROMPT,
            verbose=True
        )
        
        result = content_chain.invoke({
            "topic": request.topic,
            "style": request.style,
            "length": request.length,
            "context": context if context else "（無相關背景資料）"
        })
        
        generated_content = result["text"]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"generated_content/{timestamp}_{request.topic[:20]}.txt"
        Path("generated_content").mkdir(exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"主題: {request.topic}\n")
            f.write(f"風格: {request.style}\n")
            f.write(f"篇幅: {request.length}\n")
            f.write(f"時間: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(generated_content)
        
        logger.info(f"✅ 文案已儲存: {output_file}")
        
        return {
            "content": generated_content,
            "file_path": output_file,
            "sources": [doc.metadata.get("source", "未知") for doc in relevant_docs],
            "context_used": len(relevant_docs)
        }
        
    except Exception as e:
        logger.error(f"❌ 生成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成失敗: {str(e)}")

@app.post("/api/ingest")
async def ingest_documents(
    request: IngestRequest,
    admin: bool = Depends(verify_admin)
):
    """知識庫上傳 API"""
    try:
        folder_path = Path(request.folder_path)
        if not folder_path.exists():
            raise HTTPException(status_code=404, detail="資料夾不存在")
        
        supported_extensions = [".pdf", ".docx", ".doc", ".txt"]
        files = [f for f in folder_path.rglob("*") 
                if f.suffix.lower() in supported_extensions]
        
        if not files:
            return {"message": "資料夾中沒有支援的檔案", "processed": 0}
        
        logger.info(f"📚 開始處理 {len(files)} 個檔案")
        
        all_documents = []
        for file_path in files:
            docs = load_document(str(file_path))
            for doc in docs:
                doc.metadata["source"] = str(file_path)
                doc.metadata["uploaded_at"] = datetime.now().isoformat()
            all_documents.extend(docs)
        
        if not all_documents:
            return {"message": "無法載入任何文件", "processed": 0}
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
            length_function=len
        )
        splits = text_splitter.split_documents(all_documents)
        
        logger.info(f"📄 分割完成: {len(splits)} 個片段")
        
        vectorstore.add_documents(splits)
        
        logger.info(f"✅ 向量化完成")
        
        return {
            "message": "✅ 知識庫更新成功",
            "files_processed": len(files),
            "chunks_created": len(splits),
            "collection": COLLECTION_NAME
        }
        
    except Exception as e:
        logger.error(f"❌ 上傳失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    admin: bool = Depends(verify_admin)
):
    """單個檔案上傳"""
    try:
        file_path = Path("documents") / file.filename
        file_path.parent.mkdir(exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"📤 上傳: {file.filename}")
        
        docs = load_document(str(file_path))
        for doc in docs:
            doc.metadata["source"] = str(file_path)
        
        if docs:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(docs)
            vectorstore.add_documents(splits)
            
            return {
                "message": "✅ 檔案上傳並處理成功",
                "filename": file.filename,
                "chunks": len(splits)
            }
        else:
            return {
                "message": "檔案已上傳但無法處理",
                "filename": file.filename
            }
            
    except Exception as e:
        logger.error(f"❌ 上傳失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")

@app.get("/api/memory/{session_id}")
async def get_memory_history(session_id: str):
    """取得對話記憶"""
    try:
        memory = get_memory(session_id)
        history = memory.load_memory_variables({})
        
        return {
            "session_id": session_id,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memory/{session_id}")
async def clear_memory(session_id: str, admin: bool = Depends(verify_admin)):
    """清除對話記憶"""
    try:
        if session_id in memory_store:
            memory_store[session_id].clear()
            del memory_store[session_id]
            
            history_file = Path(f"chat_history/{session_id}.json")
            if history_file.exists():
                history_file.unlink()
            
            logger.info(f"🗑️ 已清除記憶: {session_id}")
            
        return {"message": f"✅ 已清除 {session_id} 的記憶"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """系統統計"""
    try:
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        
        return {
            "collection_name": COLLECTION_NAME,
            "total_vectors": collection_info.vectors_count,
            "active_sessions": len(memory_store),
            "framework": "LangChain",
            "components": {
                "agents": "✅ ReAct Agent",
                "memory": "✅ ConversationBufferMemory",
                "rag": "✅ ConversationalRetrievalChain",
                "tools": len(tools)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 PAIS 系統啟動 (LangChain Powered)")
    logger.info(f"📍 Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
    logger.info(f"📚 集合: {COLLECTION_NAME}")
    logger.info(f"🤖 Agents: {len(tools)} 工具")
    logger.info(f"🧠 Memory: ConversationBufferMemory")
    
    Path("chat_history").mkdir(exist_ok=True)
    Path("generated_content").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("⏹ PAIS 系統關閉")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)