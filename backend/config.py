import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Paths
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_data")
DEFAULT_PROJECT_PATH = Path(__file__).parent.parent

# Models
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")

# Ensure ChromaDB directory exists
Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
