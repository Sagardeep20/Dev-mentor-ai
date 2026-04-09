import logging
from typing import Dict, List, Optional, Tuple
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import CHAT_MODEL
from rag import retrieve_context, ingest_project

logger = logging.getLogger("devmentor.agent")


class DevMentorAgent:
    """AI Agent for code analysis and mentoring using RAG + Groq."""

    def analyze_project(self, project_path: str, user_id: str = None) -> Dict:
        """Analyze/ingest a project into the RAG pipeline."""
        return ingest_project(project_path, user_id)

    def build_prompt(self, query: str, context: str, history: str = "") -> ChatPromptTemplate:
        """Build the prompt with context and history."""
        system_prompt = """You are DEVMENTOR, an expert AI coding mentor. Your role is to:

1. Analyze code and provide clear, educational explanations
2. Help developers understand their codebase
3. Identify issues, patterns, and improvement opportunities
4. Teach best practices and design patterns

Guidelines:
- Be helpful and pedagogical, not just correct
- Explain the "why" behind recommendations
- Use code examples when helpful
- When referring to code, mention the specific file/source
- If context is insufficient, say so clearly

Previous conversation history:
{history}

Relevant code context:
{context}"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{query}")
        ])

        return prompt.partial(
            context=context or "No relevant code context found.",
            history=history or "No previous conversation."
        )

    def query(self, user_query: str, project_path: Optional[str], groq_api_key: str, user_id: str = None, history: str = "") -> Dict:
        """Process a user query and return an answer with sources."""
        logger.info(f"query called. user_query='{user_query}', project_path='{project_path}', user_id='{user_id}'")

        if not project_path:
            return {
                "answer": "No project path provided.",
                "sources": [],
                "session_id": None
            }

        context, sources = retrieve_context(user_query, project_path=project_path, user_id=user_id, k=8)

        if not sources:
            return {
                "answer": "I don't have any code context to analyze. Please analyze your project first.",
                "sources": [],
                "session_id": None
            }

        llm = ChatGroq(api_key=groq_api_key, model=CHAT_MODEL, temperature=0.3, max_tokens=2048)
        prompt_template = self.build_prompt(user_query, context, history)
        chain = prompt_template | llm
        response = chain.invoke({"query": user_query})

        answer = response.content if hasattr(response, 'content') else str(response)

        return {
            "answer": answer,
            "sources": sources,
            "session_id": None
        }


agent = DevMentorAgent()
