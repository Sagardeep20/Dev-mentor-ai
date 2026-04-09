# DevMentor AI

AI-powered coding assistant with RAG for personalized code analysis. VS Code extension + FastAPI backend.

## Features

- Chat with your codebase
- Project analysis with vector embeddings
- Code explanation & suggestions
- Issue detection (bugs, security, anti-patterns)
- Learning quizzes from your code
- Multi-user support with data isolation

---

## How Database Works

**You don't need to set up anything!**

| Environment | Database | Auto-Configured |
|-------------|----------|------------------|
| Local Dev | SQLite | Yes - works out of the box |
| Production (Render) | PostgreSQL | Yes - provided by Render |

The code automatically:
- Uses SQLite when no database URL is set (local)
- Uses PostgreSQL when `DATABASE_URL` is provided (production)

---

## Local Setup (For Developers)

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure (copy and edit .env.example)
copy .env.example .env
# Add your GROQ_API_KEY in .env

# Start server
python main.py
```

Backend runs at `http://localhost:8000`

### 2. VS Code Extension

```bash
cd vscode-extension
npm install
npm run compile
```

**Test extension:**
1. VS Code → Run and Debug (Ctrl+Shift+D)
2. Select **Run Extension** → Press **F5**
3. A new VS Code window opens
4. Set backend URL if needed: `File → Preferences → Settings → devmentor.backendUrl`
5. Register with your Groq API key
6. Open a project folder and analyze it!

---

## Deploy Backend to Production

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "DevMentor AI"
git remote add origin https://github.com/YOUR_USERNAME/devmentor-ai.git
git push -u origin main
```

### 2. Deploy on Render

1. Go to [render.com](https://render.com/) → Sign up/Login
2. Click **New +** → **Blueprint**
3. Connect your GitHub repo
4. Select `backend/render.yaml`
5. Click **Apply Blueprint**
6. Add environment variable:
   - `GROQ_API_KEY` = your Groq API key (get at https://console.groq.com/)
7. Click **Create Resources**
8. Wait 2-3 minutes for deployment

**Done!** Your backend URL will be: `https://devmentor-api.onrender.com`

---

## For End Users

### Install Extension

1. Package the extension:
```bash
cd vscode-extension
npx vsce package
```

2. Install the generated `.vsix` file:
```bash
code --install-extension devmentor-ai-*.vsix
```

### Configure Backend URL

If using a custom backend (not local), set in VS Code settings:

```json
{
  "devmentor.backendUrl": "https://your-backend-url.onrender.com"
}
```

### First-Time Setup

1. Open VS Code with a project folder
2. Click **DevMentor AI** in sidebar
3. Click **Register** tab
4. Fill in:
   - Username, Email, Password
   - **Groq API Key** (get free at https://console.groq.com/keys)
5. Click Register → Save your API key!

### Start Using

1. Click **Analyze Project** to ingest your code
2. Chat with DevMentor about your codebase
3. Right-click code → **Explain This Code**
4. Right-click code → **Suggest Improvements**
5. Run commands from Command Palette (Ctrl+Shift+P)

---

## Architecture

```
User's VS Code
    │
    │ HTTPS + API Key
    ▼
┌─────────────────────────┐
│  FastAPI Backend        │
│  - Authentication       │
│  - User Data (PostgreSQL│
│  - Code Embeddings      │
│    (ChromaDB)           │
└─────────────────────────┘
    │
    │ Groq API
    ▼
┌─────────────────────────┐
│  Groq LLM               │
│  (User's own API key)   │
└─────────────────────────┘
```

**Data Isolation:** Each user's data is stored separately using their user ID.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | VS Code Extension (TypeScript) |
| Backend | FastAPI (Python) |
| Database | SQLite (local) / PostgreSQL (production) |
| Vector DB | ChromaDB |
| AI | Groq API (Llama 3.3 70B) |
| Embeddings | sentence-transformers |

---

## Project Structure

```
devmentor-ai/
├── backend/
│   ├── main.py           # FastAPI app
│   ├── agent.py          # AI agent
│   ├── rag.py            # Vector embeddings
│   ├── models.py         # Database models
│   ├── config.py         # Configuration
│   ├── database.py       # DB setup
│   ├── services/         # Business logic
│   ├── migrations/       # DB migrations
│   ├── render.yaml       # Production deployment
│   └── .env.example      # Environment template
│
└── vscode-extension/
    ├── src/
    │   ├── extension.ts  # Entry point
    │   ├── api-client.ts # API client
    │   └── webview/      # UI
    └── package.json
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register (with Groq API key) |
| POST | `/login` | Login |
| POST | `/analyze` | Ingest project |
| POST | `/query` | Ask about code |
| POST | `/explain` | Explain code |
| POST | `/quiz/start` | Start quiz |
| GET | `/history` | Chat history |
| GET | `/health` | Health check |

Full docs at `http://localhost:8000/docs`

---

## Troubleshooting

**"Could not connect to backend"**
- Check backend is running
- Verify `devmentor.backendUrl` in settings

**"Invalid API key"**
- Re-register or check stored API key

**"No project ingested"**
- Click **Analyze Project** first

**Groq API errors**
- Check your Groq API key at https://console.groq.com/keys

---

## License

MIT
