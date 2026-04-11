# DevMentor AI

An intelligent AI-powered coding assistant that lives directly in your VS Code editor. DevMentor uses Retrieval-Augmented Generation (RAG) to understand your codebase and provide context-aware responses to your coding questions.

---

## Features

- **Codebase Chat** - Ask questions about your code and get contextual answers
- **Project Analysis** - Automatic code indexing with vector embeddings
- **Code Explanation** - Get detailed explanations for selected code
- **Issue Detection** - Find bugs, security issues, and anti-patterns
- **Code Suggestions** - Receive improvement suggestions
- **Learning Quizzes** - Test your knowledge with AI-generated quizzes
- **Source Attribution** - See which files your answers come from
- **Multi-Language Support** - Works with Python, JavaScript, TypeScript, C++, Java, Go, Rust, and more
- **User Data Isolation** - Each user's data is stored separately
- **Persistent Chat History** - Conversations are saved and retrievable

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, Alembic |
| AI/ML | LangChain, LangChain Groq, HuggingFace Embeddings |
| Database | PostgreSQL (production), SQLite (development) |
| Vector Store | ChromaDB |
| Caching | Redis |
| Extension | TypeScript, VS Code API, HTML/CSS/JS |
| Authentication | JWT, bcrypt |
| Deployment | Render |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User's VS Code                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                 DevMentor AI Extension                  │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │    │
│  │  │   Webview   │  │ API Client  │  │ Command Palette│  │    │
│  │  └─────────────┘  └─────────────┘  └────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                    │                            │
│                                    │ HTTPS + API Key             │
│                                    ▼                            │
└─────────────────────────────────────────────────────────────────┘
                                     │
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend Server                        │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐      │
│  │                     API Endpoints                         │      │
│  │  /register  /login  /analyze  /query  /explain  /quiz   │      │
│  └───────────────────────────────────────────────────────────┘      │
│                                    │                            │
│         ┌──────────────────────────┼──────────────────────────┐ │
│         ▼                          ▼                          ▼     │
│  ┌─────────────┐          ┌─────────────┐          ┌────────────┐  │
│  │  Database   │          │  ChromaDB  │          │   Redis   │  │
│  │  (SQLite/   │          │  (Vectors) │          │  (Cache)  │  │
│  │  PostgreSQL)│          │            │          │           │  │
│  └─────────────┘          └─────────────┘          └───────────┘  │
│                                    │                            │
│                                    ▼                            │
│         ┌────────────────────────────────────────────────┐       │
│         │               AI Layer                          │       │
│         │  ┌─────────────┐  ┌────────────────────────┐  │       │
│         │  │  ChatGroq   │  │    LangChain          │  │       │
│         │  │ (Llama 3.3)│  │   Orchestration      │  │       │
│         │  └─────────────┘  └────────────────────────┘  │       │
│         └────────────────────────────────────────────────┘       │
│                                    │                            │
│                                    ▼                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │   Groq Cloud API    │
                   └─────────────────────┘
```

### How It Works

1. **Analyze** - User clicks "Analyze Project" → Extension scans code files → Creates embeddings → Stores in ChromaDB
2. **Query** - User asks question → Backend retrieves relevant code chunks → Sends to Groq LLM
3. **Response** - LLM generates contextual answer → Returns with source file references

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- VS Code 1.85+
- Groq API key ([get free](https://console.groq.com/keys))

### Backend Setup (Windows)

```powershell
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
copy .env.example .env

# Edit .env and add your Groq API key
# GROQ_API_KEY=your-key-here

# Start server
python main.py
```

### Backend Setup (Mac/Linux)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY to .env
python main.py
```

### VS Code Extension Setup

```bash
cd vscode-extension
npm install
npm run compile
# Press F5 in VS Code to run extension
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Your Groq API key |
| `DATABASE_URL` | No | SQLite | Database connection |
| `CHROMA_DIR` | No | ./chroma_data | Vector DB directory |
| `JWT_SECRET` | No | auto-generated | JWT signing secret |

---

## Usage

### Getting Started

1. Open VS Code with a project folder
2. Click **DevMentor AI** in the sidebar
3. Click **Register** tab
4. Enter: Username, Email, Password, Groq API Key
5. Click **Register**
6. Click **Analyze Project** to index your code
7. Start asking questions!

### Example Conversation

```
User: "How does authentication work in this project?"

DevMentor: "Based on my analysis of your codebase:

[Source: backend/services/auth.py]
- Uses bcrypt for password hashing
- JWT tokens for session management
- API key authentication for extension access

[Source: backend/main.py]
- /register endpoint creates new user
- /login endpoint validates credentials..."
```

---

## API Documentation

### Base URL

| Environment | URL |
|------------|-----|
| Local | http://localhost:8000 |
| Production | https://your-backend.onrender.com |

### Authentication

All endpoints (except `/register`, `/login`, `/health`) require:

```
X-API-Key: your-api-key
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user |
| POST | `/login` | Login user |
| POST | `/analyze` | Analyze project |
| POST | `/query` | Ask about code |
| GET | `/status` | Get ingestion status |
| POST | `/explain` | Explain selected code |
| POST | `/analyze-issues` | Detect issues |
| POST | `/quiz/start` | Start new quiz |
| GET | `/me` | Get current user |

### Interactive API Docs

Visit `http://localhost:8000/docs` for Swagger UI.

---

## Project Structure

```
devmentor-ai/
├── README.md                    # This file
├── .gitignore                  # Git ignore patterns
│
├── backend/                    # FastAPI backend
│   ├── main.py               # FastAPI application
│   ├── config.py             # Configuration management
│   ├── database.py           # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py            # Pydantic schemas
│   ├── agent.py             # AI agent logic
│   ├── rag.py              # RAG pipeline
│   ├── file_parser.py       # Code file parsing
│   │
│   ├── services/           # Business logic
│   │   ├── auth.py       # Authentication
│   │   ├── explainer.py  # Code explanation
│   │   ├── issue_detector.py  # Issue detection
│   │   ├── quiz_generator.py  # Quiz generation
│   │   └── cache.py     # Redis caching
│   │
│   ├── migrations/        # Database migrations
│   │   └── versions/    # Migration scripts
│   │
│   ├── tests/            # Unit tests
│   │   ├── test_auth.py
│   │   ├── test_rag.py
│   │   └── test_quiz.py
│   │
│   ├── requirements.txt   # Python dependencies
│   ├── render.yaml      # Render deployment config
│   ├── alembic.ini      # Alembic configuration
│   ├── start.bat       # Windows startup
│   ├── start.sh       # Unix startup
│   └── .env.example   # Environment template
│
└── vscode-extension/    # VS Code extension
    ├── src/
    │   ├── extension.ts   # Main entry point
    │   ├── api-client.ts  # API client
    │   └── webview/
    │       └── index.html  # Webview UI
    │
    ├── package.json    # Extension manifest
    ├── tsconfig.json  # TypeScript config
    └── .vscode/    # VS Code configs
```

---

## Testing

```bash
cd backend
pytest tests/ -v

# Run specific test
pytest tests/test_auth.py -v
```

---

## Deployment

### Deploy to Render

1. Push code to GitHub:
```bash
git add .
git commit -m "Ready for deployment"
git push -u origin main
```

2. Connect to Render:
   - Go to https://render.com/
   - Click **New +** → **Blueprint**
   - Connect your GitHub repo

3. Configure Blueprint:
   - Select `backend/render.yaml`
   - Click **Apply Blueprint**

4. Set Environment Variables:
   - `GROQ_API_KEY`: Your Groq API key

5. Deploy:
   - Click **Create Resources**
   - Wait 2-3 minutes
   - Your backend URL: `https://your-service.onrender.com`

### Update Extension for Production

In VS Code settings.json:
```json
{
  "devmentor.backendUrl": "https://your-backend.onrender.com"
}
```

---

## Security

- User's Groq API key is stored securely in the database
- JWT tokens for session management
- User data isolation by user_id
- Rate limiting on API endpoints
- Passwords hashed with bcrypt

---

## Troubleshooting

### Backend Won't Start

```powershell
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt

# Check .env file exists
dir .env
```

### Extension Can't Connect

1. Verify backend is running
2. Check `devmentor.backendUrl` in settings
3. Use `http://localhost:8000` (not `https`) locally

### Database Errors

```powershell
# Delete and recreate
del devmentor.db
python -c "from database import init_db; import asyncio; asyncio.run(init_db())"
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

### Development Setup

```bash
git clone https://github.com/your-username/devmentor-ai.git
cd devmentor-ai

# Backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Extension
cd ../vscode-extension
npm install

# Test
cd ../backend
pytest tests/ -v
```

---

## License

MIT License

---

## Acknowledgements

- [LangChain](https://langchain.dev/) - LLM orchestration framework
- [Groq](https://groq.com/) - Fast AI inference
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework