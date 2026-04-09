import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_groq import ChatGroq

from config import CHAT_MODEL
from rag import retrieve_context
from models import QuizSession, QuizQuestion, QuizAnswer

logger = logging.getLogger("devmentor.quiz_generator")

DIFFICULTY_LEVELS = ["beginner", "intermediate", "advanced"]
QUESTION_TYPES = ["multiple_choice", "true_false", "code_output"]


def get_llm(groq_api_key: str):
    """Get or create LLM instance with user's Groq key."""
    return ChatGroq(
        api_key=groq_api_key,
        model=CHAT_MODEL,
        temperature=0.7,
        max_tokens=4096
    )


def build_quiz_prompt(context: str, num_questions: int, difficulty: str, topics: List[str]) -> str:
    """Build the quiz generation prompt."""
    topics_str = ", ".join(topics) if topics else "general code understanding"

    return f"""You are DevMentor, an AI coding tutor. Generate {num_questions} quiz questions about this codebase at a {difficulty} level.

Topics to cover: {topics_str}

Return a JSON array:

{{
  "questions": [
    {{
      "question_text": "What does function X do?",
      "question_type": "multiple_choice",
      "code_context": "function x() {{ /* code */ }}",
      "options": ["A) Option A", "B) Option B", "C) Option C", "D) Option D"],
      "correct_answer": "B",
      "explanation": "The correct answer is B because...",
      "file_source": "relative/path.py"
    }}
  ]
}}

Rules:
- question_type must be: multiple_choice, true_false, or code_output
- For multiple_choice: provide exactly 4 options labeled A), B), C), D)
- For true_false: options should be ["True", "False"]
- For code_output: question_text should ask "What is the output of this code?" with code_context showing the code
- correct_answer should be the letter for multiple_choice (A/B/C/D), or "True"/"False" for true_false, or the expected output for code_output
- file_source should be the relative path to the source file
- Make questions educational and specific to the actual code in the context

Code to generate questions from:
{context}"""


def parse_questions_from_response(response: str) -> List[Dict]:
    """Parse questions from LLM JSON response."""
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = response[start:end]
            data = json.loads(json_str)
            questions = data.get("questions", [])
            validated = []
            for q in questions:
                if all(k in q for k in ["question_text", "question_type", "correct_answer"]):
                    if q["question_type"] in QUESTION_TYPES:
                        validated.append({
                            "question_text": q["question_text"],
                            "question_type": q["question_type"],
                            "code_context": q.get("code_context"),
                            "options": q.get("options", []),
                            "correct_answer": q["correct_answer"],
                            "explanation": q.get("explanation", ""),
                            "file_source": q.get("file_source")
                        })
            return validated
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse questions JSON: {e}")
    return []


async def generate_quiz(
    db: AsyncSession,
    session_id: uuid.UUID,
    project_path: str,
    num_questions: int = 5,
    difficulty: str = "beginner",
    topics: List[str] = None,
    groq_api_key: str = "",
    user_id: str = None
) -> Dict:
    """Generate a quiz for the project."""
    logger.info(f"Generating quiz: session={session_id}, num={num_questions}, difficulty={difficulty}, user_id={user_id}")

    topics = topics or []

    # Get context from RAG (with user_id for proper data isolation)
    context, sources = retrieve_context("codebase overview and structure", project_path=project_path, user_id=user_id, k=20)

    if not sources:
        return {
            "error": "No code context found. Please analyze project first."
        }

    # Generate questions using LLM
    prompt = build_quiz_prompt(context, num_questions, difficulty, topics)
    llm = get_llm(groq_api_key)
    response = llm.invoke(prompt)

    response_text = response.content if hasattr(response, 'content') else str(response)

    # Parse questions
    questions_data = parse_questions_from_response(response_text)

    if not questions_data:
        return {
            "error": "Failed to generate questions. Please try again."
        }

    # Create quiz session
    quiz_session = QuizSession(
        session_id=session_id,
        current_question_index=0,
        total_questions=len(questions_data),
        correct_answers=0,
        status="active"
    )
    db.add(quiz_session)
    await db.flush()

    # Create questions
    for q_data in questions_data:
        question = QuizQuestion(
            quiz_session_id=quiz_session.id,
            question_text=q_data["question_text"],
            question_type=q_data["question_type"],
            code_context=q_data.get("code_context"),
            options=q_data.get("options", []),
            correct_answer=q_data["correct_answer"],
            explanation=q_data.get("explanation", ""),
            file_source=q_data.get("file_source")
        )
        db.add(question)

    await db.commit()

    return {
        "quiz_session_id": quiz_session.id,
        "total_questions": len(questions_data),
        "status": "started"
    }


async def get_current_question(
    db: AsyncSession,
    quiz_session_id: uuid.UUID
) -> Optional[Dict]:
    """Get the current question in a quiz session."""
    result = await db.execute(
        select(QuizSession).where(QuizSession.id == quiz_session_id)
    )
    quiz_session = result.scalar_one_or_none()

    if not quiz_session:
        return None

    if quiz_session.status != "active":
        return {"status": quiz_session.status, "completed": True}

    # Get questions for this quiz
    questions_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_session_id == quiz_session_id)
        .order_by(QuizQuestion.created_at)
    )
    questions = questions_result.scalars().all()

    if quiz_session.current_question_index >= len(questions):
        quiz_session.status = "completed"
        quiz_session.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "completed", "completed": True}

    current_q = questions[quiz_session.current_question_index]

    return {
        "question_index": quiz_session.current_question_index,
        "question_id": current_q.id,
        "question_text": current_q.question_text,
        "question_type": current_q.question_type,
        "code_context": current_q.code_context,
        "options": current_q.options or [],
        "status": "active",
        "completed": False
    }


async def submit_answer(
    db: AsyncSession,
    quiz_session_id: uuid.UUID,
    question_id: uuid.UUID,
    answer: str
) -> Dict:
    """Submit an answer to a quiz question."""
    result = await db.execute(
        select(QuizSession).where(QuizSession.id == quiz_session_id)
    )
    quiz_session = result.scalar_one_or_none()

    if not quiz_session or quiz_session.status != "active":
        return {"error": "Quiz not found or already completed"}

    # Get the question
    q_result = await db.execute(
        select(QuizQuestion).where(QuizQuestion.id == question_id)
    )
    question = q_result.scalar_one_or_none()

    if not question:
        return {"error": "Question not found"}

    # Check if answer is correct
    is_correct = answer.strip().upper() == question.correct_answer.strip().upper()

    # Store answer
    quiz_answer = QuizAnswer(
        question_id=question_id,
        selected_answer=answer,
        is_correct=is_correct
    )
    db.add(quiz_answer)

    if is_correct:
        quiz_session.correct_answers += 1

    quiz_session.current_question_index += 1

    # Check if quiz is complete
    questions_result = await db.execute(
        select(QuizQuestion).where(QuizQuestion.quiz_session_id == quiz_session_id)
    )
    total_questions = len(questions_result.scalars().all())

    if quiz_session.current_question_index >= total_questions:
        quiz_session.status = "completed"
        quiz_session.completed_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "next_question_available": quiz_session.current_question_index < total_questions,
        "current_index": quiz_session.current_question_index
    }


async def get_quiz_results(
    db: AsyncSession,
    quiz_session_id: uuid.UUID
) -> Optional[Dict]:
    """Get final quiz results."""
    result = await db.execute(
        select(QuizSession).where(QuizSession.id == quiz_session_id)
    )
    quiz_session = result.scalar_one_or_none()

    if not quiz_session:
        return None

    score_pct = 0.0
    if quiz_session.total_questions > 0:
        score_pct = round((quiz_session.correct_answers / quiz_session.total_questions) * 100, 1)

    return {
        "quiz_session_id": quiz_session.id,
        "total_questions": quiz_session.total_questions,
        "correct_answers": quiz_session.correct_answers,
        "score_percentage": score_pct,
        "status": quiz_session.status,
        "completed_at": quiz_session.completed_at
    }
