import os
import shutil
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaLLM

OLLAMA_MODEL = "llama3"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TEMP_DIR = "temp_docs"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VECTOR_STORE = None

try:
    requests.get("http://localhost:11434")
    print("Ollama running")
except:
    print("Ollama not running")

embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

llm = OllamaLLM(
    model=OLLAMA_MODEL,
    temperature=0.2
)

os.makedirs(TEMP_DIR, exist_ok=True)


class QueryRequest(BaseModel):
    question: str


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    global VECTOR_STORE

    temp_path = os.path.join(TEMP_DIR, file.filename)

    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        ext = os.path.splitext(file.filename)[1].lower()

        if ext == ".pdf":
            loader = PyMuPDFLoader(temp_path)
        elif ext == ".docx":
            loader = Docx2txtLoader(temp_path)
        elif ext in [".txt", ".md"]:
            loader = TextLoader(temp_path)
        else:
            raise HTTPException(400, "Unsupported file")

        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

        chunks = splitter.split_documents(docs)

        if VECTOR_STORE is None:
            VECTOR_STORE = FAISS.from_documents(chunks, embeddings)
        else:
            VECTOR_STORE.add_documents(chunks)

        return {"message": f"Processed {len(chunks)} chunks"}

    except Exception as e:
        raise HTTPException(500, str(e))

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/query")
async def query(request: QueryRequest):
    global VECTOR_STORE

    if VECTOR_STORE is None:
        raise HTTPException(400, "Upload document first")

    try:
        docs = VECTOR_STORE.similarity_search(request.question, k=6)

        docs = sorted(docs, key=lambda x: len(x.page_content), reverse=True)

        context = "\n\n".join([d.page_content for d in docs])
        context = context[:5000]

        prompt = f"""
You are a highly accurate AI assistant specialized in answering questions from documents.

Instructions:
- Use ONLY the provided context
- Do NOT guess or hallucinate
- If the answer is not clearly present, say: "Not found in document"
- Provide structured, well-explained answers

Context:
{context}

Question: {request.question}

Answer:
"""

        answer = ""
        for chunk in llm.stream(prompt):
            answer += chunk

        sources = list({
            d.metadata.get("source", "Unknown")
            for d in docs
        })

        return {
            "answer": answer,
            "sources": sources
        }

    except Exception:
        return {
            "answer": "Error processing request",
            "sources": []
        }