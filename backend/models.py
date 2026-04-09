import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    groq_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects: Mapped[List["Project"]] = relationship("Project", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_api_key", "api_key", unique=True),
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="projects")
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="project", cascade="all, delete-orphan")
    code_explanations: Mapped[List["CodeExplanation"]] = relationship("CodeExplanation", back_populates="project", cascade="all, delete-orphan")
    issues: Mapped[List["Issue"]] = relationship("Issue", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "path", name="uq_user_project_path"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict)

    project: Mapped["Project"] = relationship("Project", back_populates="sessions")
    interactions: Mapped[List["Interaction"]] = relationship("Interaction", back_populates="session", cascade="all, delete-orphan")
    quiz_sessions: Mapped[List["QuizSession"]] = relationship("QuizSession", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_sessions_project_id", "project_id"),
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    ai_response: Mapped[str] = mapped_column(Text, nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(50), default="query")
    sources: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    files_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="interactions")

    __table_args__ = (
        Index("idx_interactions_session_id", "session_id"),
        Index("idx_interactions_created_at", "created_at"),
    )


class CodeExplanation(Base):
    __tablename__ = "code_explanations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="code_explanations")

    __table_args__ = (
        Index("idx_code_explanations_project_hash", "project_id", "code_hash", unique=True),
    )


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="issues")

    __table_args__ = (
        Index("idx_issues_project_id", "project_id"),
        Index("idx_issues_severity", "severity"),
    )


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="quiz_sessions")
    questions: Mapped[List["QuizQuestion"]] = relationship("QuizQuestion", back_populates="quiz_session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_quiz_sessions_session_id", "session_id"),
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)
    code_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    options: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_source: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    quiz_session: Mapped["QuizSession"] = relationship("QuizSession", back_populates="questions")
    answers: Mapped[List["QuizAnswer"]] = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    selected_answer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    question: Mapped["QuizQuestion"] = relationship("QuizQuestion", back_populates="answers")
