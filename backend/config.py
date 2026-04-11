import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment detection
IS_PRODUCTION = (
    os.getenv("RENDER", "false").lower() == "true" or 
    os.getenv("NODE_ENV") == "production" or
    os.getenv("DYNO") is not None  # Heroku
)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY and not IS_PRODUCTION:
    print("WARNING: GROQ_API_KEY not set. Some features may not work.")

# Paths
CHROMA_DIR = os.getenv("CHROMA_DIR", "/tmp/chroma_data" if IS_PRODUCTION else "./chroma_data")
DEFAULT_PROJECT_PATH = Path(__file__).parent.parent

# Models
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")

# Ensure ChromaDB directory exists
Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)

# Database - auto-detect based on environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    if IS_PRODUCTION:
        raise ValueError("DATABASE_URL is required in production. Set it in your hosting environment.")
    DATABASE_URL = "sqlite+aiosqlite:///./devmentor.db"
    if not IS_PRODUCTION:
        print("INFO: Using SQLite for local development. Set DATABASE_URL for production.")

DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "5"))
DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))

# Redis (for caching) - optional, gracefully degrades if not available
REDIS_URL = os.getenv("REDIS_URL")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    if IS_PRODUCTION:
        raise ValueError("JWT_SECRET is required in production. Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    JWT_SECRET = secrets.token_urlsafe(32)
    print("WARNING: JWT_SECRET not set. Using auto-generated secret (not secure for production).")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Rate Limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if not IS_PRODUCTION else "WARNING")
