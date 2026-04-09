import logging
import uuid
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from database import get_db, init_db, close_db
from models import User, Project, Session as DBSession, Interaction, Issue
from schemas import (
    RegisterRequest, RegisterResponse, LoginRequest, LoginResponse, ApiKeyResponse,
    AnalyzeRequest, AnalyzeIssuesRequest, AnalyzeIssuesResponse, AnalyzeResponse, QueryRequest, QueryResponse,
    ExplainRequest, ExplainResponse,
    IssuesResponse, IssueResponse,
    QuizStartRequest, QuizStartResponse, QuizQuestionResponse, QuizAnswerRequest, QuizAnswerResponse, QuizResultsResponse,
    ProgressResponse, HistoryResponse, HistoryItem, StatusResponse,
)
from agent import agent
from rag import check_ingestion_status, retrieve_context
from services.explainer import explain_code
from services.issue_detector import analyze_issues, get_project_issues
from services.quiz_generator import generate_quiz, get_current_question, submit_answer, get_quiz_results
from services.auth import create_user, authenticate_user, get_user_by_api_key, regenerate_api_key, create_jwt_token, get_user_by_jwt
from config import RATE_LIMIT_PER_MINUTE, CHAT_MODEL, GROQ_API_KEY, IS_PRODUCTION, LOG_LEVEL
from langchain_groq import ChatGroq

def get_user_groq_key(user: User) -> str:
    """Get user's Groq API key, fallback to global if not set."""
    return user.groq_api_key if user.groq_api_key else GROQ_API_KEY

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger("devmentor")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Running without database - some features may not work")
    yield
    from services.cache import close_redis
    await close_redis()
    await close_db()
    logger.info("All connections closed")


app = FastAPI(
    title="DevMentor API",
    description="AI-powered code analysis and mentoring API",
    version="1.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler - prevents leaking stack traces in production."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    if IS_PRODUCTION:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred"}
        )
    else:
        raise exc

# CORS configuration
if IS_PRODUCTION:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://marketplace.visualstudio.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["vscode-file://*", "http://localhost:*", "http://127.0.0.1:*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ============ Authentication Dependency ============

async def get_current_user(
    x_api_key: str = Header(..., description="Your API key"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from API key."""
    user = await get_user_by_api_key(db, x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


async def get_current_user_jwt(
    authorization: str = Header(..., description="Bearer JWT token"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    user = await get_user_by_jwt(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT token")
    return user


# ============ Helper Functions ============

async def get_or_create_project(db: AsyncSession, user_id: uuid.UUID, project_path: str) -> Project:
    """Get or create a project for a user."""
    result = await db.execute(
        select(Project).where(Project.user_id == user_id, Project.path == project_path)
    )
    project = result.scalar_one_or_none()
    if not project:
        name = project_path.split("/")[-1] or project_path.split("\\")[-1] or "Project"
        project = Project(user_id=user_id, name=name, path=project_path)
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


async def get_or_create_db_session(db: AsyncSession, project_id: uuid.UUID) -> DBSession:
    """Get or create a database session for a project."""
    result = await db.execute(
        select(DBSession).where(DBSession.project_id == project_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        session = DBSession(project_id=project_id)
        db.add(session)
        await db.commit()
        await db.refresh(session)
    else:
        session.last_active_at = datetime.now(timezone.utc)
        await db.commit()
    return session


# ============ Auth Endpoints ============

@app.post("/register", response_model=RegisterResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
async def register(request: Request, request_body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    try:
        user = await create_user(db, request_body.username, request_body.email, request_body.password, request_body.groq_api_key)
        return RegisterResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            api_key=user.api_key,
            message="Registration successful. Save your API key - it won't be shown again."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/login", response_model=LoginResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
async def login(request: Request, request_body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get API key."""
    user = await authenticate_user(db, request_body.email, request_body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginResponse(
        user_id=user.id,
        username=user.username,
        api_key=user.api_key,
        message="Login successful"
    )


@app.post("/login/jwt", response_model=dict)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
async def login_jwt(request: Request, request_body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get JWT token (alternative to API key)."""
    user = await authenticate_user(db, request_body.email, request_body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "username": user.username
    }


@app.post("/regenerate-key", response_model=ApiKeyResponse)
async def regenerate_key(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Regenerate API key for current user."""
    new_key = await regenerate_api_key(db, user.id)
    if not new_key:
        raise HTTPException(status_code=404, detail="User not found")
    return ApiKeyResponse(
        api_key=new_key,
        message="API key regenerated. Old key is now invalid."
    )


@app.get("/me", response_model=dict)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat()
    }


# ============ Project Endpoints ============

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_project(
    request: AnalyzeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze/ingest a project into the RAG pipeline."""
    try:
        project = await get_or_create_project(db, user.id, request.project_path)
        result = await asyncio.to_thread(agent.analyze_project, request.project_path, str(user.id))
        project.last_analyzed_at = datetime.now(timezone.utc)
        await db.commit()
        db_session = await get_or_create_db_session(db, project.id)
        return AnalyzeResponse(
            status=result["status"],
            files_found=result.get("files_found", 0),
            chunks_created=result.get("chunks_created", 0),
            session_id=db_session.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query_project(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query the project with a question."""
    logger.info(f"POST /query: query='{request.query}', project_path='{request.project_path}'")
    try:
        project = await get_or_create_project(db, user.id, request.project_path or "")
        db_session = await get_or_create_db_session(db, project.id)

        result = await asyncio.to_thread(agent.query, request.query, request.project_path, get_user_groq_key(user), str(user.id))

        interaction = Interaction(
            session_id=db_session.id,
            user_message=request.query,
            ai_response=result["answer"],
            interaction_type="query",
            sources=result.get("sources", []),
            files_analyzed=0
        )
        db.add(interaction)
        await db.commit()

        return QueryResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            session_id=db_session.id
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


async def generate_stream_response(query: str, project_path: Optional[str], groq_api_key: str, user_id: str = None):
    """Generator for SSE streaming of AI responses."""
    import asyncio

    yield {"event": "status", "data": "thinking"}

    context, sources = retrieve_context(query, project_path=project_path, user_id=user_id, k=8)

    if not sources:
        yield {"event": "error", "data": "No project context found. Please analyze your project first."}
        return

    llm = ChatGroq(api_key=groq_api_key, model=CHAT_MODEL, temperature=0.3, max_tokens=2048)
    prompt_template = agent.build_prompt(query, context, "")
    chain = prompt_template | llm

    full_response = ""
    try:
        response = chain.invoke({"query": query})
        answer = response.content if hasattr(response, 'content') else str(response)

        yield {"event": "sources", "data": sources}

        for i in range(0, len(answer), 50):
            chunk = answer[i:i+50]
            full_response += chunk
            yield {"event": "chunk", "data": chunk}
            await asyncio.sleep(0.01)

        yield {"event": "done", "data": full_response}
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield {"event": "error", "data": str(e)}


@app.get("/query/stream")
async def query_stream(
    query: str = Query(..., description="Question to ask"),
    project_path: Optional[str] = Query(None, description="Project path"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query the project with streaming response via SSE."""
    logger.info(f"GET /query/stream: query='{query}', project_path='{project_path}'")

    project = await get_or_create_project(db, user.id, project_path or "")
    db_session = await get_or_create_db_session(db, project.id)

    async def event_generator():
        async for event in generate_stream_response(query, project_path, get_user_groq_key(user), str(user.id)):
            if event["event"] == "status":
                yield {"event": "status", "data": "thinking"}
            elif event["event"] == "sources":
                yield {"event": "sources", "data": event["data"]}
            elif event["event"] == "chunk":
                yield {"event": "message", "data": event["data"]}
            elif event["event"] == "done":
                # Save interaction when done
                interaction = Interaction(
                    session_id=db_session.id,
                    user_message=query,
                    ai_response=event["data"],
                    interaction_type="query_stream",
                    sources=[],
                    files_analyzed=0
                )
                db.add(interaction)
                await db.commit()
                yield {"event": "done", "data": ""}
            elif event["event"] == "error":
                yield {"event": "error", "data": event["data"]}

    return EventSourceResponse(event_generator())


@app.get("/status", response_model=StatusResponse)
async def get_status(
    project_path: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get RAG ingestion status for user's project."""
    status = check_ingestion_status(project_path, str(user.id))

    session_id = None
    proj_path = None
    db_session = None
    if project_path:
        try:
            project = await get_or_create_project(db, user.id, project_path)
            db_session = await get_or_create_db_session(db, project.id)
            session_id = db_session.id
            proj_path = project_path
        except Exception:
            pass

    return StatusResponse(
        ingested=status.get("ingested", False),
        chunks=status.get("chunks", 0),
        session_id=session_id,
        project_path=proj_path
    )


@app.get("/progress", response_model=ProgressResponse)
async def get_progress(
    project_path: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get session progress statistics."""
    session_id = None
    proj_path = None
    db_session = None
    if project_path:
        try:
            project = await get_or_create_project(db, user.id, project_path)
            db_session = await get_or_create_db_session(db, project.id)

            result = await db.execute(
                select(Interaction).where(Interaction.session_id == db_session.id)
            )
            interactions = result.scalars().all()
            questions_asked = len(interactions)

            issues_result = await db.execute(
                select(Issue).where(Issue.project_id == project.id)
            )
            issues_count = issues_result.scalars().count()
        except Exception:
            questions_asked = 0
            issues_count = 0
    else:
        questions_asked = 0
        issues_count = 0

    return ProgressResponse(
        session_id=db_session.id if db_session else None,
        project_path=project_path,
        files_analyzed=0,
        questions_asked=questions_asked,
        issues_found=issues_count
    )


@app.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = 20,
    project_path: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for user's project session."""
    if project_path:
        project = await get_or_create_project(db, user.id, project_path)
        db_session = await get_or_create_db_session(db, project.id)

        result = await db.execute(
            select(Interaction)
            .where(Interaction.session_id == db_session.id)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
        )
        interactions = result.scalars().all()
        history = [
            HistoryItem(
                timestamp=i.created_at,
                user_message=i.user_message,
                ai_response=i.ai_response,
                sources=i.sources or [],
                interaction_type=i.interaction_type
            )
            for i in reversed(interactions)
        ]
    else:
        history = []

    return HistoryResponse(history=history)


@app.delete("/history")
async def clear_history(
    project_path: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clear conversation history for user's project session."""
    if project_path:
        project = await get_or_create_project(db, user.id, project_path)
        db_session = await get_or_create_db_session(db, project.id)

        result = await db.execute(
            select(Interaction).where(Interaction.session_id == db_session.id)
        )
        interactions = result.scalars().all()
        for interaction in interactions:
            await db.delete(interaction)
        await db.commit()

    return {"message": "Conversation history cleared"}


# ============ Learning Plan Endpoint ============

@app.post("/learning-plan", response_model=dict)
async def generate_learning_plan(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a personalized learning plan for the project's tech stack."""
    logger.info(f"POST /learning-plan: project_path='{request.project_path}'")
    try:
        project = await get_or_create_project(db, user.id, request.project_path or "")
        db_session = await get_or_create_db_session(db, project.id)

        context, sources = retrieve_context("tech stack frameworks libraries dependencies architecture", project_path=request.project_path, user_id=str(user.id), k=15)

        prompt = f"""You are DevMentor, an expert coding mentor. Analyze this codebase and create a personalized learning plan.

Based on the code context below, identify:
1. The tech stack used (languages, frameworks, libraries, tools)
2. Key architectural patterns
3. A structured learning path from beginner to advanced

Format the response as:

## Tech Stack Identified
- List each technology with a brief description

## Learning Path

### Phase 1: Foundations (Week 1-2)
- Topics to learn first
- Resources and practice exercises

### Phase 2: Core Concepts (Week 3-4)
- Deeper topics
- Hands-on project ideas

### Phase 3: Advanced Topics (Week 5-6)
- Advanced patterns
- Best practices
- Real-world project suggestions

### Phase 4: Mastery (Week 7+)
- Expert-level topics
- Contribution opportunities

## Recommended Resources
- Links to docs, tutorials, courses

Code context:
{context}"""

        result = await asyncio.to_thread(agent.query, prompt, request.project_path, get_user_groq_key(user))

        interaction = Interaction(
            session_id=db_session.id,
            user_message="Generate a learning plan for this project",
            ai_response=result["answer"],
            interaction_type="learning_plan",
            sources=result.get("sources", []),
            files_analyzed=0
        )
        db.add(interaction)
        await db.commit()

        return {"plan": result["answer"], "sources": result.get("sources", [])}
    except Exception as e:
        logger.error(f"Learning plan generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Learning plan generation failed: {str(e)}")


# ============ Suggest Improvements Endpoint ============

@app.post("/suggest-improvements", response_model=dict)
async def suggest_improvements(
    request: ExplainRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Suggest improvements for selected code."""
    logger.info(f"POST /suggest-improvements: file_path='{request.file_path}'")
    try:
        project = await get_or_create_project(db, user.id, request.project_path)

        context, sources = retrieve_context(f"Context for {request.file_path}", project_path=request.project_path, user_id=str(user.id), k=5)

        prompt = f"""You are DevMentor, an expert code reviewer. Analyze this {request.language} code and suggest improvements.

```{request.language}
{request.code}
```

Provide suggestions for:
1. **Code Quality** - Readability, naming, organization
2. **Performance** - Efficiency, optimization opportunities
3. **Security** - Potential vulnerabilities
4. **Best Practices** - Design patterns, idiomatic code
5. **Maintainability** - How to make it easier to maintain

For each suggestion, provide:
- What the issue is
- Why it matters
- The improved code example

Be specific and actionable. Only suggest real improvements, not style preferences.
"""

        if context and context != "No project ingested yet. Please analyze your project first.":
            prompt = f"Codebase context:\n{context}\n\n---\n\n{prompt}"

        from langchain_groq import ChatGroq as ChatGroqAlias
        llm = ChatGroqAlias(api_key=get_user_groq_key(user), model=CHAT_MODEL, temperature=0.3, max_tokens=2048)
        response = llm.invoke(prompt)
        explanation = response.content if hasattr(response, 'content') else str(response)

        return {"suggestions": explanation, "language": request.language}
    except Exception as e:
        logger.error(f"Suggest improvements failed: {e}")
        raise HTTPException(status_code=500, detail=f"Suggest improvements failed: {str(e)}")


# ============ Explain Endpoint ============

@app.post("/explain", response_model=ExplainResponse)
async def explain_code_endpoint(
    request: ExplainRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Explain selected code inline."""
    logger.info(f"POST /explain: file_path='{request.file_path}', language='{request.language}'")
    try:
        project = await get_or_create_project(db, user.id, request.project_path)

        result = await explain_code(
            db=db,
            code=request.code,
            file_path=request.file_path,
            language=request.language,
            project_id=str(project.id),
            project_path=request.project_path,
            groq_api_key=get_user_groq_key(user),
            user_id=str(user.id)
        )

        return ExplainResponse(**result)
    except Exception as e:
        logger.error(f"Explain failed: {e}")
        raise HTTPException(status_code=500, detail=f"Explain failed: {str(e)}")


# ============ Issue Detection Endpoints ============

@app.post("/analyze-issues", response_model=AnalyzeIssuesResponse)
async def analyze_issues_endpoint(
    request: AnalyzeIssuesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze project for issues (bugs, security, anti-patterns)."""
    logger.info(f"POST /analyze-issues: project_path='{request.project_path}', scan_type='{request.scan_type}'")
    try:
        project = await get_or_create_project(db, user.id, request.project_path)
        db_session = await get_or_create_db_session(db, project.id)

        result = await analyze_issues(
            db=db,
            project_id=project.id,
            session_id=db_session.id,
            project_path=request.project_path,
            scan_type=request.scan_type,
            groq_api_key=get_user_groq_key(user),
            user_id=str(user.id)
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return AnalyzeIssuesResponse(
            total_issues=result["total_issues"],
            issues_by_severity=result["issues_by_severity"],
            issues=[IssueResponse(
                id=i.id,
                project_id=i.project_id,
                file_path=i.file_path,
                line_start=i.line_start,
                line_end=i.line_end,
                severity=i.severity,
                category=i.category,
                title=i.title,
                description=i.description,
                suggested_fix=i.suggested_fix,
                detected_at=i.detected_at
            ) for i in result["issues"]]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Issue analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Issue analysis failed: {str(e)}")


@app.get("/issues/{project_path:path}", response_model=IssuesResponse)
async def get_issues(
    project_path: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get stored issues for user's project."""
    try:
        project = await get_or_create_project(db, user.id, project_path)
        result = await get_project_issues(db, project.id)

        return IssuesResponse(
            total_issues=result["total_issues"],
            issues_by_severity=result["issues_by_severity"],
            issues=[IssueResponse(
                id=i.id,
                project_id=i.project_id,
                file_path=i.file_path,
                line_start=i.line_start,
                line_end=i.line_end,
                severity=i.severity,
                category=i.category,
                title=i.title,
                description=i.description,
                suggested_fix=i.suggested_fix,
                detected_at=i.detected_at
            ) for i in result["issues"]],
            last_scan=result.get("last_scan")
        )
    except Exception as e:
        logger.error(f"Get issues failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get issues failed: {str(e)}")


# ============ Quiz Endpoints ============

@app.post("/quiz/start", response_model=QuizStartResponse)
async def start_quiz(
    request: QuizStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new quiz session."""
    logger.info(f"POST /quiz/start: project_path='{request.project_path}', num={request.num_questions}")
    try:
        project = await get_or_create_project(db, user.id, request.project_path)
        db_session = await get_or_create_db_session(db, project.id)

        result = await generate_quiz(
            db=db,
            session_id=db_session.id,
            project_path=request.project_path,
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            topics=request.topics,
            groq_api_key=get_user_groq_key(user),
            user_id=str(user.id)
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return QuizStartResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start quiz failed: {e}")
        raise HTTPException(status_code=500, detail=f"Start quiz failed: {str(e)}")


@app.get("/quiz/{quiz_session_id}/question", response_model=QuizQuestionResponse)
async def get_question(
    quiz_session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current question in a quiz."""
    try:
        result = await get_current_question(db, quiz_session_id)

        if not result:
            raise HTTPException(status_code=404, detail="Quiz not found")

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        if result.get("completed"):
            return QuizQuestionResponse(
                question_index=result.get("question_index", 0),
                question_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                question_text="Quiz completed!",
                question_type="multiple_choice",
                code_context=None,
                options=[]
            )

        return QuizQuestionResponse(
            question_index=result["question_index"],
            question_id=result["question_id"],
            question_text=result["question_text"],
            question_type=result["question_type"],
            code_context=result.get("code_context"),
            options=result.get("options", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get question failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get question failed: {str(e)}")


@app.post("/quiz/{quiz_session_id}/answer", response_model=QuizAnswerResponse)
async def submit_quiz_answer(
    quiz_session_id: uuid.UUID,
    request: QuizAnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit an answer to a quiz question."""
    try:
        result = await submit_answer(
            db=db,
            quiz_session_id=quiz_session_id,
            question_id=request.question_id,
            answer=request.answer
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return QuizAnswerResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Submit answer failed: {e}")
        raise HTTPException(status_code=500, detail=f"Submit answer failed: {str(e)}")


@app.get("/quiz/{quiz_session_id}/results", response_model=QuizResultsResponse)
async def get_results(
    quiz_session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get final quiz results."""
    try:
        result = await get_quiz_results(db, quiz_session_id)

        if not result:
            raise HTTPException(status_code=404, detail="Quiz not found")

        return QuizResultsResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get results failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get results failed: {str(e)}")


# ============ Health Check ============

@app.get("/")
async def root():
    return {"message": "DevMentor API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ============ Main ============

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("DevMentor API Server")
    print("=" * 50)
    print("Starting server at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
