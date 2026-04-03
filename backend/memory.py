import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json
from config import CHROMA_DIR


class SessionMemory:
    """Manages session storage and conversation history."""

    def __init__(self):
        self.sessions_dir = Path(CHROMA_DIR) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_id: Optional[str] = None
        self.current_project: Optional[str] = None

    def _get_session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def _load_session(self, session_id: str) -> Dict:
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "project_path": "",
            "interactions": [],
            "stats": {
                "files_analyzed": 0,
                "questions_asked": 0,
                "issues_found": 0
            }
        }

    def _save_session(self, session_data: Dict):
        session_id = session_data["session_id"]
        session_file = self._get_session_file(session_id)
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

    def create_session(self, project_path: str) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())[:8]
        session_data = self._load_session(session_id)
        session_data["project_path"] = project_path
        session_data["created_at"] = datetime.now().isoformat()
        self._save_session(session_data)

        self.current_session_id = session_id
        self.current_project = project_path

        return session_id

    def get_or_create_session(self, project_path: str) -> str:
        """Get existing session or create new one."""
        if self.sessions_dir.exists():
            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    if data.get("project_path") == project_path:
                        self.current_session_id = data["session_id"]
                        self.current_project = project_path
                        return self.current_session_id
                except:
                    continue

        return self.create_session(project_path)

    def get_current_session_id(self) -> Optional[str]:
        return self.current_session_id

    def store_interaction(
        self,
        user_message: str,
        ai_response: str,
        sources: List[Dict],
        files_analyzed: int = 0
    ):
        """Store a Q&A interaction."""
        if not self.current_session_id:
            return

        session_data = self._load_session(self.current_session_id)

        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "ai_response": ai_response,
            "sources": sources,
            "files_analyzed": files_analyzed
        }

        session_data["interactions"].append(interaction)
        session_data["stats"]["questions_asked"] += 1
        if files_analyzed > 0:
            session_data["stats"]["files_analyzed"] = files_analyzed

        self._save_session(session_data)

    def get_conversation_history(self, limit: int = 20) -> List[Dict]:
        """Get recent conversation history."""
        if not self.current_session_id:
            return []

        session_data = self._load_session(self.current_session_id)
        interactions = session_data.get("interactions", [])

        return interactions[-limit:]

    def get_formatted_history(self, limit: int = 10) -> str:
        """Get history as formatted string for prompt injection."""
        interactions = self.get_conversation_history(limit)

        if not interactions:
            return ""

        parts = []
        for i, interaction in enumerate(interactions[-limit:], 1):
            parts.append(f"Previous Q{i}: {interaction['user_message']}")
            parts.append(f"Previous A{i}: {interaction['ai_response']}")

        return "\n".join(parts)

    def get_progress(self) -> Dict:
        """Get session progress stats."""
        if not self.current_session_id:
            return {
                "session_id": None,
                "files_analyzed": 0,
                "questions_asked": 0,
                "issues_found": 0
            }

        session_data = self._load_session(self.current_session_id)
        stats = session_data.get("stats", {})

        return {
            "session_id": self.current_session_id,
            "project_path": self.current_project,
            "files_analyzed": stats.get("files_analyzed", 0),
            "questions_asked": stats.get("questions_asked", 0),
            "issues_found": stats.get("issues_found", 0)
        }

    def increment_stat(self, stat_name: str, amount: int = 1):
        """Increment a session statistic."""
        if not self.current_session_id:
            return

        session_data = self._load_session(self.current_session_id)
        if stat_name in session_data["stats"]:
            session_data["stats"][stat_name] += amount
            self._save_session(session_data)


memory = SessionMemory()


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Session Memory")
    print("=" * 50)

    print("\n1. Creating session...")
    session_id = memory.get_or_create_session("/test/project")
    print(f"   Session ID: {session_id}")

    print("\n2. Storing interaction...")
    memory.store_interaction(
        user_message="What files exist?",
        ai_response="Found 5 Python files.",
        sources=[{"source": "test.py", "score": 0.9}],
        files_analyzed=5
    )
    print("   Interaction stored")

    print("\n3. Getting progress...")
    progress = memory.get_progress()
    print(f"   Progress: {progress}")

    print("\n4. Getting formatted history...")
    history = memory.get_formatted_history()
    print(f"   History:\n{history}")

    print("\n" + "=" * 50)
    print("Session Memory Test Complete!")
    print("=" * 50)
