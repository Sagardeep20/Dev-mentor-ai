from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from agent import agent
from rag import check_ingestion_status
from memory import memory

app = FastAPI(
    title="DevMentor API",
    description="AI-powered code analysis and mentoring API",
    version="1.0.0"
)

# CORS for VS Code extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class AnalyzeRequest(BaseModel):
    project_path: str


class QueryRequest(BaseModel):
    query: str
    project_path: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    session_id: Optional[str]


class AnalyzeResponse(BaseModel):
    status: str
    files_found: int
    chunks_created: int
    session_id: str


class StatusResponse(BaseModel):
    ingested: bool
    chunks: int
    session_id: Optional[str]
    project_path: Optional[str]


class ProgressResponse(BaseModel):
    session_id: Optional[str]
    project_path: Optional[str]
    files_analyzed: int
    questions_asked: int
    issues_found: int


class HistoryResponse(BaseModel):
    history: List[Dict]


# Endpoints
@app.get("/")
async def root():
    return {"message": "DevMentor API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_project(request: AnalyzeRequest):
    """Analyze/ingest a project into the RAG pipeline."""
    try:
        result = agent.analyze_project(request.project_path)
        session_id = memory.get_or_create_session(request.project_path)
        return AnalyzeResponse(
            status=result["status"],
            files_found=result.get("files_found", 0),
            chunks_created=result.get("chunks_created", 0),
            session_id=session_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query_project(request: QueryRequest):
    """Query the project with a question."""
    try:
        result = agent.query(request.query, request.project_path)
        return QueryResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            session_id=result.get("session_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/status", response_model=StatusResponse)
async def get_status(project_path: Optional[str] = None):
    """Get RAG ingestion status and current session info."""
    status = check_ingestion_status()

    session_id = None
    session_project = None
    if project_path:
        session_id = memory.get_or_create_session(project_path)
        session_project = project_path
    else:
        session_id = memory.get_current_session_id()
        progress = memory.get_progress()
        session_project = progress.get("project_path")

    return StatusResponse(
        ingested=status.get("ingested", False),
        chunks=status.get("chunks", 0),
        session_id=session_id,
        project_path=session_project
    )


@app.get("/progress", response_model=ProgressResponse)
async def get_progress(project_path: Optional[str] = None):
    """Get session progress statistics."""
    if project_path:
        memory.get_or_create_session(project_path)

    progress = memory.get_progress()
    return ProgressResponse(
        session_id=progress.get("session_id"),
        project_path=progress.get("project_path"),
        files_analyzed=progress.get("files_analyzed", 0),
        questions_asked=progress.get("questions_asked", 0),
        issues_found=progress.get("issues_found", 0)
    )


@app.get("/history", response_model=HistoryResponse)
async def get_history(limit: int = 20, project_path: Optional[str] = None):
    """Get conversation history for the current session."""
    if project_path:
        memory.get_or_create_session(project_path)

    history = memory.get_conversation_history(limit=limit)
    return HistoryResponse(history=history)


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("DevMentor API Server")
    print("=" * 50)
    print("Starting server at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
