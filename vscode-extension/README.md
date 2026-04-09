# DevMentor AI - VS Code Extension

AI-powered coding assistant with RAG for personalized code analysis.

## Quick Start

### Install Dependencies
```powershell
cd vscode-extension
npm install
```

### Compile TypeScript
```powershell
npm run compile
```

### Run Extension
1. Open VS Code
2. Press `Ctrl+Shift+D` to open Run and Debug
3. Select **"Run Extension"**
4. Press **F5**
5. A new VS Code window opens with the extension

### Package Extension (for distribution)
```powershell
npx vsce package
```

This creates `devmentor-ai-*.vsix` file.

### Install .vsix File
```powershell
code --install-extension devmentor-ai-*.vsix
```

## Configuration

### Backend URL
Set the backend URL in VS Code settings:

```json
{
  "devmentor.backendUrl": "http://localhost:8000"
}
```

For production:
```json
{
  "devmentor.backendUrl": "https://your-backend-url.onrender.com"
}
```

## Features

- **Chat with your code** - Ask questions about your codebase
- **Project analysis** - Analyze and ingest code for RAG
- **Code explanation** - Right-click code to explain it
- **Issue detection** - Find bugs, security issues, anti-patterns
- **Learning quizzes** - Test your knowledge
- **Learning plans** - Personalized learning paths

## First-Time Setup

1. Open VS Code with a project folder
2. Click **DevMentor AI** in the sidebar
3. Click **Register** tab
4. Enter:
   - Username, Email, Password
   - **Groq API Key** (get free at https://console.groq.com/keys)
5. Click Register
6. Click **Analyze Project**
7. Start chatting!

## Commands

Access via Command Palette (`Ctrl+Shift+P`):

- `DevMentor: Analyze Project` - Ingest project files
- `DevMentor: Explain This Code` - Explain selected code
- `DevMentor: Suggest Improvements` - Get improvement suggestions
- `DevMentor: Detect Issues` - Find bugs and issues
- `DevMentor: Start Learning Quiz` - Test your knowledge
- `DevMentor: Show Status` - View connection status
- `DevMentor: Clear Conversation` - Clear chat history

## Requirements

- VS Code 1.85.0 or higher
- Backend server running (local or remote)
- Groq API key (free at https://console.groq.com/keys)
