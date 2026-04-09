import hashlib
import logging
from typing import Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config import CHAT_MODEL
from rag import retrieve_context
from services.cache import cache

logger = logging.getLogger("devmentor.explainer")


def get_llm(groq_api_key: str):
    """Get or create LLM instance with user's Groq key."""
    return ChatGroq(
        api_key=groq_api_key,
        model=CHAT_MODEL,
        temperature=0.3,
        max_tokens=1024
    )


def hash_code(code: str) -> str:
    """Generate SHA256 hash of code for caching."""
    return hashlib.sha256(code.encode()).hexdigest()


def build_explain_prompt(code: str, language: str) -> str:
    """Build the explanation prompt."""
    return f"""You are DevMentor, an expert coding mentor. Explain this {language} code clearly and concisely:

```{language}
{code}
```

Focus on:
- What the code does (one sentence)
- How it works
- Any notable patterns, potential issues, or improvement opportunities

Keep the explanation concise but informative. Maximum 3-4 sentences."""


async def get_cached_explanation(db, project_id: str, code_hash: str) -> Optional[str]:
    """Check if explanation is cached in database."""
    from sqlalchemy import select
    from models import CodeExplanation

    result = await db.execute(
        select(CodeExplanation).where(
            CodeExplanation.project_id == project_id,
            CodeExplanation.code_hash == code_hash
        )
    )
    cached = result.scalar_one_or_none()
    return cached.explanation if cached else None


async def cache_explanation(db, project_id: str, file_path: str, code_hash: str, explanation: str, language: str):
    """Store explanation in cache."""
    from models import CodeExplanation

    cached = CodeExplanation(
        project_id=project_id,
        file_path=file_path,
        code_hash=code_hash,
        explanation=explanation,
        language=language
    )
    db.add(cached)
    await db.commit()


async def explain_code(
    db,
    code: str,
    file_path: str,
    language: str,
    project_id: str,
    project_path: str,
    groq_api_key: str,
    user_id: str = None
) -> Dict:
    """Explain selected code using LLM with caching."""
    code_hash = hash_code(code)

    # Check Redis cache first
    redis_cached = await cache.get_explanation(code_hash, project_id)
    if redis_cached:
        logger.info(f"Redis cache hit for explanation: {code_hash[:12]}")
        return {
            "explanation": redis_cached,
            "language": language,
            "cached": True
        }

    # Check DB cache second
    cached = await get_cached_explanation(db, project_id, code_hash)
    if cached:
        # Promote to Redis cache
        await cache.set_explanation(code_hash, project_id, cached, language)
        return {
            "explanation": cached,
            "language": language,
            "cached": True
        }

    # Get relevant context from RAG
    context, sources = retrieve_context(f"Context for {file_path}: {code[:200]}", project_path=project_path, user_id=user_id, k=4)

    # Build prompt
    prompt = build_explain_prompt(code, language)
    if context and context != "No project ingested yet. Please analyze your project first.":
        prompt = f"Context from the codebase:\n{context}\n\n---\n\n{prompt}"

    # Call LLM
    llm = get_llm(groq_api_key)
    response = llm.invoke(prompt)
    explanation = response.content if hasattr(response, 'content') else str(response)

    # Cache in both Redis and DB
    await cache.set_explanation(code_hash, project_id, explanation, language)
    await cache_explanation(db, project_id, file_path, code_hash, explanation, language)

    return {
        "explanation": explanation,
        "language": language,
        "cached": False
    }
