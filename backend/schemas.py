from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============ Auth Schemas ============

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=6)
    groq_api_key: str = Field(..., min_length=10)


class RegisterResponse(BaseModel):
    user_id: UUID
    username: str
    email: str
    api_key: str
    message: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user_id: UUID
    username: str
    api_key: str
    message: str


class ApiKeyResponse(BaseModel):
    api_key: str
    message: str


# ============ User/Project Schemas ============

class UserBase(BaseModel):
    username: str
    email: str


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    last_active_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    name: str
    path: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    last_analyzed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============ Session Schemas ============

class SessionResponse(BaseModel):
    id: UUID
    project_id: UUID
    created_at: datetime
    last_active_at: datetime
    metadata: Optional[dict] = {}

    model_config = ConfigDict(from_attributes=True)


# ============ Interaction Schemas ============

class InteractionBase(BaseModel):
    user_message: str
    ai_response: str
    interaction_type: str = "query"
    sources: List[dict] = []
    files_analyzed: int = 0


class InteractionCreate(InteractionBase):
    session_id: UUID


class InteractionResponse(InteractionBase):
    id: UUID
    session_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Explain Schemas ============

class ExplainRequest(BaseModel):
    code: str
    file_path: str
    language: str
    project_path: str


class ExplainResponse(BaseModel):
    explanation: str
    language: str
    cached: bool = False


# ============ Issue Schemas ============

class IssueBase(BaseModel):
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    severity: str
    category: str
    title: str
    description: str
    suggested_fix: Optional[str] = None


class IssueCreate(IssueBase):
    project_id: UUID
    session_id: Optional[UUID] = None


class IssueResponse(IssueBase):
    id: UUID
    project_id: UUID
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalyzeRequest(BaseModel):
    project_path: str


class AnalyzeIssuesRequest(BaseModel):
    project_path: str
    file_path: Optional[str] = None
    scan_type: str = "all"


class AnalyzeIssuesResponse(BaseModel):
    total_issues: int
    issues_by_severity: dict
    issues: List[IssueResponse]


class IssuesResponse(BaseModel):
    total_issues: int
    issues_by_severity: dict
    issues: List[IssueResponse]
    last_scan: Optional[datetime] = None


# ============ Quiz Schemas ============

class QuizStartRequest(BaseModel):
    project_path: str
    num_questions: int = Field(default=5, ge=3, le=20)
    difficulty: str = "beginner"
    topics: List[str] = []


class QuizStartResponse(BaseModel):
    quiz_session_id: UUID
    total_questions: int
    status: str


class QuizQuestionResponse(BaseModel):
    question_index: int
    question_id: UUID
    question_text: str
    question_type: str
    code_context: Optional[str] = None
    options: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class QuizAnswerRequest(BaseModel):
    question_id: UUID
    answer: str


class QuizAnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    explanation: Optional[str] = None
    next_question_available: bool
    current_index: int


class QuizResultsResponse(BaseModel):
    quiz_session_id: UUID
    total_questions: int
    correct_answers: int
    score_percentage: float
    status: str
    completed_at: Optional[datetime] = None


# ============ History/Progress Schemas ============

class HistoryItem(BaseModel):
    timestamp: datetime
    user_message: str
    ai_response: str
    sources: List[dict] = []
    interaction_type: str = "query"


class HistoryResponse(BaseModel):
    history: List[HistoryItem]


class ProgressResponse(BaseModel):
    session_id: Optional[UUID] = None
    project_path: Optional[str] = None
    files_analyzed: int = 0
    questions_asked: int = 0
    issues_found: int = 0


# ============ Status Schemas ============

class StatusResponse(BaseModel):
    ingested: bool
    chunks: int
    session_id: Optional[UUID] = None
    project_path: Optional[str] = None


# ============ Generic Schemas ============

class AnalyzeResponse(BaseModel):
    status: str
    files_found: int
    chunks_created: int
    session_id: UUID


class QueryRequest(BaseModel):
    query: str
    project_path: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    session_id: Optional[UUID] = None
