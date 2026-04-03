import os
from typing import Dict, List, Optional, Tuple
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import GROQ_API_KEY, CHAT_MODEL
from rag import retrieve_context, ingest_project, check_ingestion_status
from memory import memory


class DevMentorAgent:
    """AI Agent for code analysis and mentoring using RAG + Groq."""

    def __init__(self):
        self.llm = None
        self._init_llm()

    def _init_llm(self):
        """Initialize Groq LLM."""
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in environment")

        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model=CHAT_MODEL,
            temperature=0.3,
            max_tokens=2048
        )

    def analyze_project(self, project_path: str) -> Dict:
        """Analyze/ingest a project into the RAG pipeline."""
        result = ingest_project(project_path)
        if result["status"] == "success":
            session_id = memory.get_or_create_session(project_path)
            memory.increment_stat("files_analyzed", result["files_found"])
        return result

    def get_context(self, query: str, k: int = 8) -> Tuple[str, List[Dict]]:
        """Retrieve relevant code context for a query."""
        return retrieve_context(query, k=k)

    def build_prompt(self, query: str, context: str, history: str = "") -> ChatPromptTemplate:
        """Build the prompt with context and history."""
        system_prompt = """You are DevMentor, an expert AI coding mentor. Your role is to:

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

    def query(self, user_query: str, project_path: Optional[str] = None) -> Dict:
        """Process a user query and return an answer with sources."""
        # Get or create session
        if project_path:
            memory.get_or_create_session(project_path)
        else:
            memory.get_or_create_session("")

        # Get conversation history
        history = memory.get_formatted_history(limit=10)

        # Retrieve relevant context
        context, sources = retrieve_context(user_query, k=8)

        # Check if we have context to work with
        if not sources:
            return {
                "answer": "I don't have any code context to analyze. Please analyze your project first using the /analyze command.",
                "sources": [],
                "session_id": memory.get_current_session_id()
            }

        # Build prompt and get LLM response
        prompt_template = self.build_prompt(user_query, context, history)
        chain = prompt_template | self.llm
        response = chain.invoke({"query": user_query})

        answer = response.content if hasattr(response, 'content') else str(response)

        # Store interaction in memory
        memory.store_interaction(
            user_message=user_query,
            ai_response=answer,
            sources=sources,
            files_analyzed=0
        )

        return {
            "answer": answer,
            "sources": sources,
            "session_id": memory.get_current_session_id()
        }

    def chat(self, message: str, project_path: Optional[str] = None) -> Dict:
        """Main chat interface - alias for query."""
        return self.query(message, project_path)


# Global agent instance
agent = DevMentorAgent()


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("DevMentor Agent Test")
    print("=" * 50)

    # Test query without ingestion
    print("\n1. Testing query without ingestion...")
    result = agent.query("What files exist in this project?")
    print(f"   Answer: {result['answer'][:200]}...")
    print(f"   Sources: {len(result['sources'])}")

    # Test with ingestion
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
        print(f"\n2. Analyzing project: {project_path}")
        analyze_result = agent.analyze_project(project_path)
        print(f"   Result: {analyze_result}")

        print("\n3. Testing query after ingestion...")
        result = agent.query("What is this project about?", project_path)
        print(f"   Answer: {result['answer'][:300]}...")
        print(f"   Sources: {len(result['sources'])}")

    print("\n" + "=" * 50)
    print("Agent Test Complete!")
    print("=" * 50)
