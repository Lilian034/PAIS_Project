import os
import re
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from loguru import logger

# LangChain & Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain.agents import create_react_agent, Tool, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain.chains import LLMChain

from utils.db_helper import StaffDatabase
from prompts import PUBLIC_AGENT_PROMPT, STAFF_AGENT_PROMPT

load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123456")
COLLECTION_NAME = "pais_knowledge_base"

logger.add("logs/public_{time}.log", rotation="1 day", retention="30 days")

app = FastAPI(title="PAIS Public API", version="2.5.3")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is missing!")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.3, 
    max_output_tokens=2048,
    convert_system_message_to_human=True
)

embeddings = HuggingFaceEmbeddings(
    model_name="moka-ai/m3e-base",
    model_kwargs={'device': 'cpu'}
)

qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
try:
    qdrant_client.get_collection(COLLECTION_NAME)
except Exception:
    try:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
    except Exception:
        pass

vectorstore = Qdrant(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embeddings=embeddings
)

db = StaffDatabase()
memory_store: Dict[str, ConversationBufferMemory] = {}

def clean_text(text: str) -> str:
    if not text: return ""
    return re.sub(r'[\{\}]', '', text)

def get_memory(session_id: str) -> ConversationBufferMemory:
    if session_id not in memory_store:
        Path("chat_history").mkdir(exist_ok=True)
        history_file = f"chat_history/{session_id}.json"
        
        memory_store[session_id] = ConversationBufferMemory(
            chat_memory=FileChatMessageHistory(history_file),
            memory_key="chat_history",
            return_messages=True
        )
    return memory_store[session_id]

def verify_admin(authorization: Optional[str] = Header(None)):
    if not ADMIN_PASSWORD or authorization != f"Bearer {ADMIN_PASSWORD}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# --- Tools ---

def search_knowledge_base(query: str) -> str:
    safe_query = clean_text(query)
    logger.info(f"🔍 [工具搜尋] {safe_query}")
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(safe_query)
        if docs:
            contents = [clean_text(doc.page_content) for doc in docs]
            result = "\n\n".join(contents)
            return f"【資料庫查詢結果】:\n{result[:2500]}"
        return "資料庫中沒有找到相關資料。"
    except Exception as e:
        return f"搜尋發生錯誤: {clean_text(str(e))}"

public_tools = [
    Tool(
        name="KnowledgeSearch",
        func=search_knowledge_base,
        description="【必須使用】回答任何關於桃園市政、福利、補助、市長背景或新聞時，務必先使用此工具查詢。"
    )
]

staff_tools = [
    Tool(
        name="KnowledgeSearch",
        func=search_knowledge_base,
        description="事實查核工具。用於驗證文稿中的數據、政策名稱與專有名詞是否正確。"
    )
]

# --- Agents Setup ---

public_prompt_tmpl = PromptTemplate(
    template=PUBLIC_AGENT_PROMPT,
    input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"]
)
public_agent = create_react_agent(llm, public_tools, public_prompt_tmpl)
public_executor = AgentExecutor(agent=public_agent, tools=public_tools, verbose=True, handle_parsing_errors=True)

staff_prompt_tmpl = PromptTemplate(
    template=STAFF_AGENT_PROMPT,
    input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"]
)
staff_agent = create_react_agent(llm, staff_tools, staff_prompt_tmpl)
staff_executor = AgentExecutor(agent=staff_agent, tools=staff_tools, verbose=True, handle_parsing_errors=True)

# --- Models ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    role: str = "public"

class ChatResponse(BaseModel):
    reply: str
    session_id: str

class ContentGenRequest(BaseModel):
    topic: str
    style: str = "Formal"
    length: str = "Medium"

class IngestRequest(BaseModel):
    folder_path: str = "documents"

# --- API Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ok", "llm": "Gemini", "db": "Qdrant"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    sid = request.session_id or f"session_{int(datetime.now().timestamp())}"
    memory = get_memory(sid)
    try:
        history = memory.load_memory_variables({})["chat_history"]
        
        if request.role == "staff":
            logger.info(f"🛡️ [校稿模式] 處理請求: {sid}")
            executor = staff_executor
        else:
            logger.info(f"😊 [善寶模式] 處理請求: {sid}")
            executor = public_executor

        result = await executor.ainvoke({
            "input": clean_text(request.message),
            "chat_history": history
        })
        
        output = result.get("output", "系統忙碌中...")
        memory.save_context({"input": request.message}, {"output": output})
        return ChatResponse(reply=output, session_id=sid)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(reply="系統錯誤。", session_id=sid)

@app.post("/api/generate")
async def generate_content(req: ContentGenRequest, admin: bool = Depends(verify_admin)):
    try:
        context = search_knowledge_base(req.topic)
        gen_prompt = PromptTemplate(
            template="角色：市長文膽\n任務：撰寫 {length}、{style} 風格的文案。\n主題：{topic}\n參考資料：{context}\n內容：",
            input_variables=["topic", "style", "length", "context"]
        )
        chain = LLMChain(llm=llm, prompt=gen_prompt)
        result = await chain.ainvoke({
            "topic": req.topic, "style": req.style, 
            "length": req.length, "context": context
        })
        return {"content": result["text"].strip(), "context_used": "【資料庫查詢結果】" in context}
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest")
async def ingest_documents(req: IngestRequest, admin: bool = Depends(verify_admin)):
    folder = Path(req.folder_path)
    if not folder.exists(): raise HTTPException(404, "Folder not found")
    processed = 0
    for f in folder.rglob("*"):
        if f.suffix.lower() in ['.txt', '.pdf', '.docx']:
            try:
                if f.suffix == '.pdf': loader = PyPDFLoader(str(f))
                elif f.suffix == '.docx': loader = Docx2txtLoader(str(f))
                else: loader = TextLoader(str(f), encoding='utf-8')
                docs = loader.load()
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                splits = splitter.split_documents(docs)
                for doc in splits:
                    doc.metadata["source"] = f.name
                    doc.page_content = clean_text(doc.page_content)
                if splits:
                    vectorstore.add_documents(splits)
                    processed += 1
            except Exception as e:
                logger.warning(f"Skipped {f.name}: {e}")
    return {"message": "Ingest complete", "files_processed": processed}

@app.get("/api/documents")
async def list_documents(admin: bool = Depends(verify_admin)):
    docs = []
    base_path = Path("documents")
    if not base_path.exists(): base_path.mkdir(parents=True, exist_ok=True)
    
    for f in base_path.rglob("*"):
        if f.is_file() and f.suffix.lower() in ['.txt', '.pdf', '.docx']:
            # 【關鍵修正】計算相對路徑，去掉 documents/ 前綴
            # 這樣前端拿到的 path 就是 "sub/file.pdf" 而不是 "documents/sub/file.pdf"
            try:
                relative_path = f.relative_to(base_path)
            except ValueError:
                relative_path = f.name
                
            docs.append({
                "filename": f.name,
                "path": str(relative_path).replace("\\", "/"), 
                "size": f.stat().st_size,
                "uploaded_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "extension": f.suffix.lower()
            })
    return {"documents": docs, "total": len(docs)}

@app.delete("/api/documents/{file_path:path}")
async def delete_document(file_path: str, admin: bool = Depends(verify_admin)):
    """刪除文件 (支援多層目錄)"""
    # 安全檢查
    if ".." in file_path: 
        raise HTTPException(400, "Invalid path")
    
    # 【關鍵修正】防止路徑重複 (如果前端傳來 documents/file.pdf，我們去掉前面的 documents/)
    clean_path = file_path
    if clean_path.startswith("documents/") or clean_path.startswith("documents\\"):
        clean_path = clean_path[10:] # 去掉 "documents/"
        
    target = Path("documents") / clean_path
    
    logger.info(f"🗑️ 請求刪除: {file_path} -> 解析路徑: {target}")

    if target.exists():
        target.unlink()
        return {"message": "Deleted"}
    
    # 如果找不到，再試試看是否真的在根目錄
    target_retry = Path(file_path)
    if target_retry.exists() and str(target_retry).startswith("documents"):
         target_retry.unlink()
         return {"message": "Deleted"}

    raise HTTPException(404, f"File not found: {clean_path}")

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), admin: bool = Depends(verify_admin)):
    file_path = Path("documents") / file.filename
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    return {"filename": file.filename, "status": "Uploaded"}

@app.post("/api/visitor/increment")
async def visitor_increment():
    try: return db.increment_visitor_count()
    except Exception: return {"status": "error"}

@app.get("/api/visitor/stats")
async def get_visitor_stats():
    try: return db.get_visitor_stats() or {"count": 0}
    except Exception: return {"count": 0}

@app.on_event("startup")
async def startup():
    for d in ["chat_history", "logs", "documents"]: Path(d).mkdir(exist_ok=True)
    logger.info("PAIS System Started (Gemini + Dual Agents)")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)