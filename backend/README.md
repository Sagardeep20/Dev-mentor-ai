# DevMentor AI - Backend

FastAPI backend for the DevMentor AI VS Code extension.

## Quick Start

### Windows
```powershell
# Option 1: Double-click start.bat
start.bat

# Option 2: Manual
cd backend
.\venv\Scripts\activate
python main.py
```

### Mac/Linux
```bash
chmod +x start.sh
./start.sh
```

## Manual Setup

### 1. Create Virtual Environment
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment
```powershell
copy .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 4. Run Server
```powershell
python main.py
```

## Get Groq API Key

1. Go to https://console.groq.com/keys
2. Create account (free)
3. Generate new API key
4. Add to `.env` file

## Server URLs

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API Root |
| http://localhost:8000/docs | Swagger Documentation |
| http://localhost:8000/health | Health Check |

## Database

- **Local**: SQLite (automatic, no setup)
- **Production**: PostgreSQL (set DATABASE_URL)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| GROQ_API_KEY | Yes | - | Groq API key |
| DATABASE_URL | No | SQLite | Database connection string |
| CHROMA_DIR | No | ./chroma_data | Vector database directory |
| JWT_SECRET | No | auto | JWT signing secret |

## Troubleshooting

### "Module not found" errors
```powershell
pip install -r requirements.txt
```

### "GROQ_API_KEY not set" warning
Edit `.env` file and add your Groq API key.

### Database errors
Delete `devmentor.db` and restart - it will recreate automatically.

### Port 8000 in use
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual number)
taskkill /PID <PID> /F
```
