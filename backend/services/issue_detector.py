import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from config import CHAT_MODEL
from rag import retrieve_context
from models import Issue

logger = logging.getLogger("devmentor.issue_detector")

ISSUE_CATEGORIES = ["security", "bug", "anti_pattern", "performance", "style"]
SEVERITY_LEVELS = ["critical", "high", "medium", "low", "info"]


def get_llm(groq_api_key: str):
    """Get or create LLM instance with user's Groq key."""
    return ChatGroq(
        api_key=groq_api_key,
        model=CHAT_MODEL,
        temperature=0.1,
        max_tokens=4096
    )


def build_issue_analysis_prompt(context: str, scan_type: str = "all") -> str:
    """Build the issue detection prompt."""
    categories = ISSUE_CATEGORIES if scan_type == "all" else scan_type.split(",")

    categories_str = ", ".join(categories)

    return f"""You are DevMentor, an expert code reviewer. Analyze the following codebase for issues.

Return a JSON array of issues found:

{{
  "issues": [
    {{
      "file_path": "relative/path.py",
      "line_start": 42,
      "severity": "high|medium|low|critical",
      "category": "{categories_str}",
      "title": "Brief title",
      "description": "Detailed explanation of the issue",
      "suggested_fix": "How to fix it"
    }}
  ]
}}

Categories to check:
- security: SQL injection, XSS, hardcoded secrets, insecure crypto, path traversal
- bug: null checks missing, error handling, edge cases, race conditions
- anti_pattern: God class, tight coupling, circular dependencies, duplicated code
- performance: N+1 queries, inefficient loops, redundant operations, memory leaks
- style: naming conventions, code organization, missing documentation

Rules:
- Only report real issues, not style preferences
- line_start should be an approximate line number from the provided code
- severity should be critical/high/medium/low based on impact
- Return empty issues array if none found: {{"issues": []}}
- Maximum 20 issues

Code to analyze:
{context}"""


def parse_issues_from_response(response: str) -> List[Dict]:
    """Parse issues from LLM JSON response."""
    try:
        # Try to extract JSON from response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = response[start:end]
            data = json.loads(json_str)
            issues = data.get("issues", [])
            # Validate and sanitize issues
            validated = []
            for issue in issues:
                if all(k in issue for k in ["file_path", "severity", "category", "title", "description"]):
                    if issue["severity"] in SEVERITY_LEVELS and issue["category"] in ISSUE_CATEGORIES:
                        validated.append({
                            "file_path": issue["file_path"],
                            "line_start": issue.get("line_start"),
                            "line_end": issue.get("line_end"),
                            "severity": issue["severity"],
                            "category": issue["category"],
                            "title": issue["title"],
                            "description": issue["description"],
                            "suggested_fix": issue.get("suggested_fix")
                        })
            return validated
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse issues JSON: {e}")
    return []


async def analyze_issues(
    db: AsyncSession,
    project_id: uuid.UUID,
    session_id: Optional[uuid.UUID],
    project_path: str,
    scan_type: str = "all",
    groq_api_key: str = "",
    user_id: str = None
) -> Dict:
    """Analyze project for issues using LLM."""
    logger.info(f"Starting issue analysis for project {project_id}, scan_type={scan_type}, user_id={user_id}")

    # Get all code context from ChromaDB
    context, sources = retrieve_context("entire codebase", project_path=project_path, user_id=user_id, k=50)

    if not sources:
        return {
            "total_issues": 0,
            "issues_by_severity": {},
            "issues": [],
            "error": "No code context found. Please analyze project first."
        }

    # Build prompt and call LLM
    prompt = build_issue_analysis_prompt(context, scan_type)
    llm = get_llm(groq_api_key)
    response = llm.invoke(prompt)

    response_text = response.content if hasattr(response, 'content') else str(response)

    # Parse issues
    issues_data = parse_issues_from_response(response_text)

    # Clear old issues for this project (optional - comment out to keep history)
    result = await db.execute(
        select(Issue).where(Issue.project_id == project_id)
    )
    old_issues = result.scalars().all()
    for issue in old_issues:
        await db.delete(issue)

    # Store new issues
    stored_issues = []
    for issue_data in issues_data:
        issue = Issue(
            project_id=project_id,
            session_id=session_id,
            file_path=issue_data["file_path"],
            line_start=issue_data.get("line_start"),
            line_end=issue_data.get("line_end"),
            severity=issue_data["severity"],
            category=issue_data["category"],
            title=issue_data["title"],
            description=issue_data["description"],
            suggested_fix=issue_data.get("suggested_fix")
        )
        db.add(issue)
        stored_issues.append(issue)

    await db.commit()

    # Build response
    issues_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for issue in stored_issues:
        if issue.severity in issues_by_severity:
            issues_by_severity[issue.severity] += 1

    return {
        "total_issues": len(stored_issues),
        "issues_by_severity": issues_by_severity,
        "issues": stored_issues
    }


async def get_project_issues(
    db: AsyncSession,
    project_id: uuid.UUID
) -> Dict:
    """Get all stored issues for a project."""
    result = await db.execute(
        select(Issue)
        .where(Issue.project_id == project_id)
        .order_by(Issue.detected_at.desc())
    )
    issues = result.scalars().all()

    issues_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for issue in issues:
        if issue.severity in issues_by_severity:
            issues_by_severity[issue.severity] += 1

    last_scan = max((issue.detected_at for issue in issues), default=None)

    return {
        "total_issues": len(issues),
        "issues_by_severity": issues_by_severity,
        "issues": issues,
        "last_scan": last_scan
    }
