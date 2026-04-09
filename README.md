# DevMentor AI

<div align="center">

![DevMentor AI](https://img.shields.io/badge/DevMentor-AI-purple?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?style=for-the-badge)
![VS Code](https://img.shields.io/badge/VS%20Code-Extension-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**AI-powered coding assistant with RAG for personalized code analysis**

[Features](#features) • [Architecture](#architecture) • [Tech Stack](#tech-stack) • [Quick Start](#quick-start) • [Setup Guide](#setup-guide) • [API Docs](#api-documentation) • [Deployment](#deployment)

</div>

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Tech Stack](#tech-stack)
5. [Quick Start](#quick-start)
6. [Setup Guide](#setup-guide)
   - [Backend Setup](#backend-setup)
   - [VS Code Extension Setup](#vs-code-extension-setup)
7. [Usage Guide](#usage-guide)
   - [For Developers](#for-developers)
   - [For End Users](#for-end-users)
8. [API Documentation](#api-documentation)
9. [Deployment](#deployment)
10. [Project Structure](#project-structure)
11. [Troubleshooting](#troubleshooting)
12. [Contributing](#contributing)
13. [License](#license)

---

## Overview

DevMentor AI is an intelligent coding assistant that lives directly in your VS Code editor. It uses **Retrieval-Augmented Generation (RAG)** to understand your codebase and provide context-aware responses to your coding questions.

Unlike generic AI assistants, DevMentor AI:
- **Knows your codebase** - Analyzes and indexes your project files
- **Provides context** - References specific files and code snippets
- **Teaches you** - Explains code, suggests improvements, generates quizzes
- **Secures your data** - Uses your own Groq API key (data never leaves your control)

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **💬 Codebase Chat** | Ask questions about your code and get contextual answers |
| **🔍 Project Analysis** | Automatic code indexing with vector embeddings |
| **📖 Code Explanation** | Right-click any code to get detailed explanations |
| **🐛 Issue Detection** | Find bugs, security issues, anti-patterns |
| **📝 Code Suggestions** | Get improvement suggestions for selected code |
| **❓ Learning Quizzes** | Test your knowledge with AI-generated quizzes |
| **📊 Ingestion Status** | Track what's been analyzed in your project |

### Key Capabilities

- **Context-Aware Responses** - Understands your project's structure and patterns
- **Source Attribution** - Shows which files the answers come from
- **Multi-Language Support** - Works with Python, JavaScript, TypeScript, C++, Java, Go, Rust, and 40+ languages
- **User Data Isolation** - Each user's data is stored separately
- **Persistent Chat History** - Conversations are saved and retrievable

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User's VS Code                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DevMentor AI Extension                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │
│  │  │   Webview   │  │ API Client   │  │  Command Palette     │  │   │
│  │  │   (HTML/JS) │  │ (TypeScript) │  │  Integration        │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    │ HTTPS + API Key                   │
│                                    ▼                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend Server                           │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      API Endpoints                                 │  │
│  │  /register  /login  /analyze  /query  /explain  /quiz  /history  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│         ┌─────────────────────────┼─────────────────────────┐        │
│         │                         │                         │        │
│         ▼                         ▼                         ▼        │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐    │
│  │  Database   │         │  ChromaDB   │         │   Redis     │    │
│  │  (SQLite/   │         │  (Vectors)  │         │  (Cache)    │    │
│  │  PostgreSQL)│         │             │         │             │    │
│  └─────────────┘         └─────────────┘         └─────────────┘    │
│                                                                         │
│         ┌─────────────────────────────────────────────────────┐       │
│         │                    AI Layer                           │       │
│         │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │       │
│         │  │ ChatGroq    │  │ Embeddings  │  │ LangChain  │  │       │
│         │  │ (Llama 3.3) │  │ (Transformer│  │ Orchestr.  │  │       │
│         │  └─────────────┘  └─────────────┘  └────────────┘  │       │
│         └─────────────────────────────────────────────────────┘       │
│                                    │                                    │
│                                    │ API Call                          │
│                                    ▼                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │     Groq Cloud API     │
                        │   (User's API Key)     │
                        └─────────────────────────┘
```

### Data Flow

```
1. USER ACTION
   User clicks "Analyze Project" in VS Code
         │
         ▼
2. FILE INGESTION
   Extension → Backend → File Parser → LangChain → ChromaDB
   (Scans all code files, splits into chunks, creates embeddings)
         │
         ▼
3. QUERY PROCESSING
   User asks question → Extension → Backend → RAG Retrieval
   (Finds relevant chunks from ChromaDB using embeddings)
         │
         ▼
4. AI RESPONSE
   Retrieved context + Question → Groq LLM → Formatted response
   (Generates contextual answer using retrieved code)
         │
         ▼
5. DISPLAY
   Response → Extension Webview → User
   (Shows answer with source file references)
```

### Security Model

```
┌────────────────────────────────────────────────────────────────┐
│                    Security Architecture                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   USER'S MACHINE          │        BACKEND SERVER             │
│   ───────────────────     │        ───────────────            │
│                           │                                    │
│   VS Code + Extension     │   FastAPI (authenticated)          │
│   │                       │         │                          │
│   │ API Key stored        │         │ User data isolated        │
│   │ in VS Code secure     │         │ by user_id               │
│   │ storage               │         │                          │
│   │                       │         ▼                         │
│   │                       │   ┌─────────────────┐            │
│   └───────────────────────┼──▶│  Database        │            │
│                           │   │  per-user tables │            │
│                           │   └─────────────────┘            │
│   ┌───────────────────┐   │                                  │
│   │ User's Groq Key   │   │   Backend NEVER sees user's      │
│   │ (stored locally)  │   │   Groq key (passed directly      │
│   └───────────────────┘   │   to Groq API)                   │
│                           │                                  │
└────────────────────────────────────────────────────────────────┘

Key Security Points:
✓ User's Groq API key never touches the backend server
✓ API key stored in VS Code secure storage
✓ JWT tokens for session management
✓ User data isolated by user_id in database
✓ Rate limiting on API endpoints
```

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11+ | Main backend language |
| **FastAPI** | 0.104+ | Web framework |
| **SQLAlchemy** | 2.0+ | ORM with async support |
| **Alembic** | latest | Database migrations |
| **Pydantic** | 2.0+ | Data validation |

### AI & Machine Learning

| Technology | Purpose |
|------------|---------|
| **LangChain** | LLM orchestration framework |
| **LangChain Groq** | Groq API integration |
| **HuggingFace Embeddings** | Sentence transformers |
| **ChromaDB** | Vector database for RAG |

### Database

| Environment | Database | Purpose |
|-------------|----------|---------|
| Local Dev | SQLite | Zero-setup development |
| Production | PostgreSQL | Scalable production DB |

### Frontend (Extension)

| Technology | Purpose |
|------------|---------|
| **TypeScript** | Extension logic |
| **VS Code API** | Extension framework |
| **HTML/CSS/JS** | Webview UI |

### Infrastructure

| Service | Purpose |
|---------|---------|
| **Render** | Cloud hosting |
| **GitHub** | Version control |

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ (for VS Code extension)
- VS Code 1.85+
- Groq API key (free at https://console.groq.com/keys)

### 5-Minute Setup

#### Step 1: Start Backend

```powershell
# Windows
cd backend
.\start.bat

# Mac/Linux
cd backend
chmod +x start.sh
./start.sh
```

#### Step 2: Start Extension

```powershell
cd vscode-extension
npm install
npm run compile
# Press F5 in VS Code
```

#### Step 3: Register & Use

1. Open VS Code with a project folder
2. Click **DevMentor AI** in sidebar
3. Click **Register** tab
4. Enter your Groq API key
5. Click **Analyze Project**
6. Start chatting!

---

## Setup Guide

### Backend Setup

#### Option A: Windows (Recommended)

```powershell
# Navigate to backend
cd backend

# Double-click or run:
.\start.bat

# This will:
# 1. Create virtual environment
# 2. Install dependencies
# 3. Create .env file
# 4. Start server
```

#### Option B: Manual Setup

```powershell
# Create virtual environment
cd backend
python -m venv venv
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

#### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Your Groq API key |
| `DATABASE_URL` | No | SQLite | Database connection |
| `CHROMA_DIR` | No | ./chroma_data | Vector DB directory |
| `JWT_SECRET` | No | auto-generated | JWT signing secret |

### VS Code Extension Setup

```powershell
# Navigate to extension directory
cd vscode-extension

# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Run extension (F5 in VS Code)
```

### Extension Configuration

Add to your VS Code `settings.json`:

```json
{
  "devmentor.backendUrl": "http://localhost:8000"
}
```

For production:

```json
{
  "devmentor.backendUrl": "https://your-backend.onrender.com"
}
```

---

## Usage Guide

### For Developers

#### Local Development

```powershell
# Terminal 1: Backend
cd backend
python main.py
# Server runs at http://localhost:8000

# Terminal 2: Extension
cd vscode-extension
npm run watch
# Auto-recompiles on changes
```

#### Testing

```powershell
# Backend tests
cd backend
pytest tests/

# Run specific test file
pytest tests/test_auth.py -v
```

#### Creating Migrations

```powershell
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### For End Users

#### Getting Started

1. **Install the Extension**
   
   Package and install the extension:
   ```powershell
   cd vscode-extension
   npx vsce package
   code --install-extension devmentor-ai-*.vsix
   ```

2. **Configure Backend**
   
   If not using local backend, set URL in VS Code settings:
   ```json
   {
     "devmentor.backendUrl": "https://your-backend.onrender.com"
   }
   ```

3. **Register Account**
   
   - Click DevMentor AI in sidebar
   - Click **Register** tab
   - Enter: Username, Email, Password
   - Enter your **Groq API Key** (get free at https://console.groq.com/keys)
   - Click **Register**

4. **Analyze Your Project**
   
   - Open a project folder in VS Code
   - Click **Analyze Project** button
   - Wait for indexing to complete (shows progress)

#### Feature Guide

##### Chat with Your Codebase

```
User: "How does the authentication work in this project?"
DevMentor: "Based on my analysis, authentication in your project works as follows:

[Source: backend/services/auth.py]
- Uses bcrypt for password hashing
- JWT tokens for session management
- API key authentication for extension access

[Source: backend/main.py]
- /register endpoint creates new user
- /login endpoint validates credentials..."
```

##### Code Explanation

1. Select code in editor
2. Right-click → **DevMentor: Explain This Code**
3. View explanation in chat panel

##### Issue Detection

1. Click **Issues** button
2. DevMentor scans for:
   - Security vulnerabilities
   - Bug-prone patterns
   - Anti-patterns
   - Performance issues
   - Style inconsistencies

##### Learning Quiz

1. Click **Quiz** button
2. Select difficulty (beginner/intermediate/advanced)
3. Answer questions generated from your code
4. View results and explanations

---

## API Documentation

### Base URL

| Environment | URL |
|-------------|-----|
| Local | `http://localhost:8000` |
| Production | `https://your-backend.onrender.com` |

### Authentication

All endpoints (except `/register`, `/login`, `/health`) require:

```
X-API-Key: your-api-key
```

Or Bearer token:

```
Authorization: Bearer your-api-key
```

### Endpoints

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user |
| POST | `/login` | Login user |

**Register Request:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepassword",
  "groq_api_key": "gsk_..."
}
```

**Login Request:**
```json
{
  "email": "john@example.com",
  "password": "securepassword"
}
```

#### Project Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Analyze project |
| GET | `/status` | Get ingestion status |
| POST | `/query` | Ask about code |
| GET | `/history` | Get chat history |

**Analyze Request:**
```json
{
  "project_path": "/path/to/project"
}
```

**Query Request:**
```json
{
  "query": "How does authentication work?",
  "project_path": "/path/to/project"
}
```

#### Code Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/explain` | Explain selected code |
| POST | `/suggest-improvements` | Get improvement suggestions |
| POST | `/analyze-issues` | Detect issues in code |

**Explain Request:**
```json
{
  "code": "def hello(): print('world')",
  "file_path": "hello.py",
  "language": "python",
  "project_path": "/path/to/project"
}
```

#### Quiz

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/quiz/start` | Start new quiz |
| GET | `/quiz/{id}/question` | Get next question |
| POST | `/quiz/{id}/answer` | Submit answer |
| GET | `/quiz/{id}/results` | Get quiz results |

**Start Quiz Request:**
```json
{
  "project_path": "/path/to/project",
  "num_questions": 5,
  "difficulty": "beginner",
  "topics": ["functions", "variables"]
}
```

#### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/me` | Get current user |

### Interactive API Docs

Visit `http://localhost:8000/docs` for Swagger UI documentation.

---

## Deployment

### Deploy Backend to Render

#### Prerequisites

- GitHub account
- Render account
- Groq API key

#### Steps

1. **Push to GitHub**
   ```powershell
   git add .
   git commit -m "Ready for deployment"
   git push -u origin main
   ```

2. **Connect to Render**
   - Go to https://render.com/
   - Click **"New +"** → **"Blueprint"**
   - Connect your GitHub repo

3. **Configure Blueprint**
   - Select `backend/render.yaml`
   - Click **"Apply Blueprint"**

4. **Set Environment Variables**
   - `GROQ_API_KEY`: Your Groq API key

5. **Deploy**
   - Click **"Create Resources"**
   - Wait 2-3 minutes
   - Your backend URL: `https://your-service.onrender.com`

#### Update Extension Settings

```json
{
  "devmentor.backendUrl": "https://your-backend.onrender.com"
}
```

### Package Extension for Distribution

```powershell
cd vscode-extension

# Package extension
npx vsce package

# This creates: devmentor-ai-0.1.0.vsix

# Install locally
code --install-extension devmentor-ai-0.1.0.vsix
```

### Publish to VS Code Marketplace

```powershell
# Login to VS Code publisher
npx vsce login your-publisher-name

# Publish
npx vsce publish
```

---

## Project Structure

```
devmentor-ai/
│
├── README.md                    # This file
├── .gitignore                  # Git ignore patterns
│
├── backend/                    # FastAPI backend
│   ├── main.py                # FastAPI application
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection
│   ├── models.py              # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   ├── agent.py               # AI agent logic
│   ├── rag.py                 # RAG pipeline
│   ├── file_parser.py         # Code file parsing
│   │
│   ├── services/              # Business logic
│   │   ├── auth.py            # Authentication
│   │   ├── explainer.py       # Code explanation
│   │   ├── issue_detector.py  # Issue detection
│   │   ├── quiz_generator.py  # Quiz generation
│   │   └── cache.py           # Redis caching
│   │
│   ├── migrations/            # Database migrations
│   │   ├── versions/          # Migration scripts
│   │   ├── env.py             # Alembic config
│   │   └── README             # Migration guide
│   │
│   ├── tests/                 # Unit tests
│   │   ├── test_auth.py
│   │   ├── test_rag.py
│   │   ├── test_quiz.py
│   │   └── conftest.py
│   │
│   ├── requirements.txt       # Python dependencies
│   ├── render.yaml            # Render deployment config
│   ├── alembic.ini           # Alembic configuration
│   ├── start.bat              # Windows startup script
│   ├── start.sh              # Unix startup script
│   ├── .env.example          # Environment template
│   └── README.md              # Backend-specific docs
│
└── vscode-extension/          # VS Code extension
    ├── src/
    │   ├── extension.ts       # Main entry point
    │   ├── api-client.ts      # API client
    │   └── webview/
    │       └── index.html     # Webview UI
    │
    ├── media/
    │   └── icon.svg          # Extension icon
    │
    ├── package.json           # Extension manifest
    ├── tsconfig.json          # TypeScript config
    ├── README.md              # Extension docs
    └── .vscode/               # VS Code configs
```

---

## Troubleshooting

### Common Issues

#### Backend Won't Start

```powershell
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check .env file exists
dir .env

# Check port not in use
netstat -ano | findstr :8000
```

#### Extension Can't Connect

1. Verify backend is running
2. Check `devmentor.backendUrl` in settings
3. Try `http://localhost:8000` (not `https`)

#### Quiz/Analysis Not Working

- Ensure project is analyzed first
- Check Groq API key is valid
- Verify internet connection

#### Database Errors

```powershell
# Delete and recreate database
del devmentor.db
python -c "from database import init_db; import asyncio; asyncio.run(init_db())"
```

### Error Messages

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `GROQ_API_KEY not set` | Add key to `.env` file |
| `Port 8000 in use` | Kill process or change port |
| `Connection refused` | Check backend is running |

### Get Help

- Check API docs: `http://localhost:8000/docs`
- View backend logs in terminal
- Check VS Code Developer Tools (Help → Toggle Developer Tools)

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

### Development Setup

```powershell
# Clone repository
git clone https://github.com/your-username/devmentor-ai.git
cd devmentor-ai

# Setup backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Setup extension
cd ../vscode-extension
npm install

# Run tests
cd ../backend
pytest tests/ -v
```

---

## License

MIT License - feel free to use, modify, and distribute.

---

<div align="center">

**Built with ❤️ for developers who love to learn**

[Back to Top](#devmentor-ai)

</div>
