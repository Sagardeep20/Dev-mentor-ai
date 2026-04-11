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

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy |
| AI/ML | LangChain, Groq (Llama 3.3), HuggingFace Embeddings |
| Database | PostgreSQL (production), SQLite (development) |
| Vector Store | ChromaDB |
| Extension | TypeScript, VS Code API |
| Deployment | Render |

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- VS Code 1.85+
- Groq API key ([get free](https://console.groq.com/keys))

### Backend Setup

```bash
# Create virtual environment
cd backend
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
copy .env.example .env
# Add GROQ_API_KEY to .env

# Start server
python main.py
```

### VS Code Extension Setup

```bash
cd vscode-extension
npm install
npm run compile
# Press F5 to run extension in VS Code
```

---

## Usage

1. Open VS Code with a project folder
2. Click **DevMentor AI** in the sidebar
3. Register an account with your Groq API key
4. Click **Analyze Project** to index your code
5. Start asking questions!

---

## Project Structure

```
devmentor-ai/
├── backend/                    # FastAPI backend
│   ├── main.py               # Application entry point
│   ├── agent.py              # AI agent logic
│   ├── rag.py               # RAG pipeline
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   ├── models.py           # SQLAlchemy models
│   ├── services/           # Business logic
│   ├── migrations/         # Alembic migrations
│   └── tests/             # Unit tests
│
└── vscode-extension/         # VS Code extension
    ├── src/
    │   ├── extension.ts    # Main entry
    │   ├── api-client.ts # API client
    │   └── webview/    # Webview UI
    └── package.json       # Extension manifest
```

---

## Deployment

### Deploy to Render

1. Push code to GitHub
2. Connect repo to Render
3. Use `backend/render.yaml` as blueprint
4. Set `GROQ_API_KEY` environment variable
5. Deploy

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest backend/tests/`
5. Submit a pull request

---

## License

MIT License

---

## Acknowledgements

- [LangChain](https://langchain.dev/) - LLM orchestration
- [Groq](https://groq.com/) - Fast AI inference
- [ChromaDB](https://www.trychroma.com/) - Vector database