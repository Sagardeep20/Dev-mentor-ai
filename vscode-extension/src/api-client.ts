export interface ApiClientConfig {
    baseUrl: string;
    apiKey: string;
}

interface QueryResponse { answer: string; sources: Array<{ file: string; code: string }>; session_id: string; }
interface AnalyzeResponse { status: string; files_found: number; chunks_created: number; session_id: string; }
interface HistoryItem { query?: string; response?: string; user_message?: string; ai_response?: string; }
interface HistoryResponse { history: HistoryItem[]; }
interface StatusResponse { ingested: boolean; chunks: number; session_id: string; project_path: string; }
interface ExplainResponse { explanation: string; language: string; cached: boolean; }
interface Issue { id: string; file_path: string; line_start: number; severity: string; category: string; title: string; description: string; suggested_fix?: string; }
interface AnalyzeIssuesResponse { total_issues: number; issues_by_severity: Record<string, number>; issues: Issue[]; }
interface QuizSession { quiz_session_id: string; total_questions: number; status: string; }
interface QuizQuestion { question_index: number; question_id: string; question_text: string; question_type: string; code_context?: string; options: string[]; }
interface QuizAnswerResult { correct: boolean; correct_answer: string; explanation?: string; next_question_available: boolean; current_index: number; }
interface QuizResults { quiz_session_id: string; total_questions: number; correct_answers: number; score_percentage: number; status: string; completed_at?: string; }

export class ApiClient {
    private baseUrl: string;
    private apiKey: string;

    constructor(config: ApiClientConfig) {
        this.baseUrl = config.baseUrl;
        this.apiKey = config.apiKey;
    }

    setApiKey(apiKey: string) {
        this.apiKey = apiKey;
    }

    private headers(): Record<string, string> {
        return {
            'Content-Type': 'application/json',
            'X-API-Key': this.apiKey
        };
    }

    async checkBackend(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch {
            return false;
        }
    }

    async checkApiKey(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/me`, {
                headers: this.headers()
            });
            return response.ok;
        } catch {
            return false;
        }
    }

    async register(username: string, email: string, password: string, groqApiKey: string): Promise<{ api_key: string; message: string; error?: string }> {
        try {
            const response = await fetch(`${this.baseUrl}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password, groq_api_key: groqApiKey })
            });

            const data = await response.json();
            if (!response.ok) {
                return { api_key: '', message: '', error: data.detail || 'Registration failed' };
            }
            return { api_key: data.api_key, message: data.message };
        } catch (error: any) {
            return { api_key: '', message: '', error: 'Could not connect to backend' };
        }
    }

    async login(email: string, password: string): Promise<{ api_key: string; message: string; error?: string }> {
        try {
            const response = await fetch(`${this.baseUrl}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            if (!response.ok) {
                return { api_key: '', message: '', error: data.detail || 'Login failed' };
            }
            return { api_key: data.api_key, message: data.message };
        } catch (error: any) {
            return { api_key: '', message: '', error: 'Could not connect to backend' };
        }
    }

    async ask(query: string, projectPath: string): Promise<{ answer: string; sources: QueryResponse['sources'], error?: string }> {
        try {
            const response = await fetch(`${this.baseUrl}/query`, {
                method: 'POST',
                headers: this.headers(),
                body: JSON.stringify({ query, project_path: projectPath })
            });

            if (response.status === 401 || response.status === 422) {
                return { answer: '', sources: [], error: 'Authentication failed. Please login again.' };
            }
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json() as QueryResponse;
            return { answer: data.answer || 'No response', sources: data.sources || [] };
        } catch (error) {
            console.error('DevMentor API error:', error);
            return { answer: 'Error: Could not connect to DevMentor backend.', sources: [] };
        }
    }

    async analyze(projectPath: string): Promise<{ status: string; files_found: number; chunks_created: number; error?: string }> {
        try {
            const response = await fetch(`${this.baseUrl}/analyze`, {
                method: 'POST',
                headers: this.headers(),
                body: JSON.stringify({ project_path: projectPath })
            });

            if (response.status === 401 || response.status === 422) {
                return { status: 'error', files_found: 0, chunks_created: 0, error: 'Authentication failed. Please login again.' };
            }
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json() as AnalyzeResponse;
            return data;
        } catch (error: any) {
            console.error('DevMentor analyze error:', error);
            return { status: 'error', files_found: 0, chunks_created: 0, error: error.message || 'Connection failed' };
        }
    }

    async explainCode(code: string, filePath: string, language: string, projectPath: string): Promise<ExplainResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/explain`, {
                method: 'POST',
                headers: this.headers(),
                body: JSON.stringify({ code, file_path: filePath, language, project_path: projectPath })
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json() as ExplainResponse;
        } catch (error) {
            console.error('DevMentor explain error:', error);
            return { explanation: 'Error: Could not explain code.', language, cached: false };
        }
    }

    async suggestImprovements(code: string, filePath: string, language: string, projectPath: string): Promise<{ suggestions: string; language: string }> {
        try {
            const response = await fetch(`${this.baseUrl}/suggest-improvements`, {
                method: 'POST',
                headers: this.headers(),
                body: JSON.stringify({ code, file_path: filePath, language, project_path: projectPath })
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('DevMentor suggest improvements error:', error);
            return { suggestions: 'Error: Could not generate suggestions.', language };
        }
    }

    async analyzeIssues(projectPath: string, scanType: string = 'all'): Promise<AnalyzeIssuesResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/analyze-issues`, {
                method: 'POST',
                headers: this.headers(),
                body: JSON.stringify({ project_path: projectPath, scan_type: scanType })
            });

            if (response.status === 401 || response.status === 422) {
                throw new Error('Authentication failed. Please login again.');
            }
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json() as AnalyzeIssuesResponse;
        } catch (error) {
            console.error('DevMentor analyze issues error:', error);
            return { total_issues: 0, issues_by_severity: {}, issues: [] };
        }
    }

    async getIssues(projectPath: string): Promise<AnalyzeIssuesResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/issues/${encodeURIComponent(projectPath)}`, {
                headers: this.headers()
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json() as AnalyzeIssuesResponse;
        } catch (error) {
            console.error('DevMentor get issues error:', error);
            return { total_issues: 0, issues_by_severity: {}, issues: [] };
        }
    }

    async generateLearningPlan(projectPath: string): Promise<{ plan: string; sources: Array<any> }> {
        try {
            const response = await fetch(`${this.baseUrl}/learning-plan`, {
                method: 'POST',
                headers: this.headers(),
                body: JSON.stringify({ query: 'Generate a learning plan', project_path: projectPath })
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('DevMentor learning plan error:', error);
            return { plan: 'Error: Could not generate learning plan.', sources: [] };
        }
    }

    async startQuiz(projectPath: string, numQuestions: number = 5, difficulty: string = 'beginner'): Promise<QuizSession> {
        try {
            const response = await fetch(`${this.baseUrl}/quiz/start`, {
                method: 'POST',
                headers: this.headers(),
                body: JSON.stringify({ project_path: projectPath, num_questions: numQuestions, difficulty })
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json() as QuizSession;
        } catch (error) {
            console.error('DevMentor start quiz error:', error);
            return { quiz_session_id: '', total_questions: 0, status: 'error' };
        }
    }

    async getQuizQuestion(quizSessionId: string): Promise<QuizQuestion> {
        try {
            const response = await fetch(`${this.baseUrl}/quiz/${quizSessionId}/question`, {
                headers: this.headers()
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json() as QuizQuestion;
        } catch (error) {
            console.error('DevMentor get question error:', error);
            throw error;
        }
    }

    async submitQuizAnswer(quizSessionId: string, questionId: string, answer: string): Promise<QuizAnswerResult> {
        try {
            const response = await fetch(`${this.baseUrl}/quiz/${quizSessionId}/answer`, {
                method: 'POST',
                headers: this.headers(),
                body: JSON.stringify({ question_id: questionId, answer })
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json() as QuizAnswerResult;
        } catch (error) {
            console.error('DevMentor submit answer error:', error);
            throw error;
        }
    }

    async getQuizResults(quizSessionId: string): Promise<QuizResults> {
        try {
            const response = await fetch(`${this.baseUrl}/quiz/${quizSessionId}/results`, {
                headers: this.headers()
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json() as QuizResults;
        } catch (error) {
            console.error('DevMentor get results error:', error);
            throw error;
        }
    }

    async getStatus(projectPath?: string): Promise<StatusResponse> {
        try {
            const url = projectPath ? `${this.baseUrl}/status?project_path=${encodeURIComponent(projectPath)}` : `${this.baseUrl}/status`;
            const response = await fetch(url, { headers: this.headers() });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json() as StatusResponse;
            return data;
        } catch (error) {
            console.error('DevMentor status error:', error);
            return { ingested: false, chunks: 0, session_id: '', project_path: '' };
        }
    }

    async getHistory(projectPath?: string): Promise<HistoryItem[]> {
        try {
            const url = projectPath ? `${this.baseUrl}/history?project_path=${encodeURIComponent(projectPath)}` : `${this.baseUrl}/history`;
            const response = await fetch(url, { headers: this.headers() });
            if (response.status === 401 || response.status === 422) {
                throw new Error('Authentication failed. Please login again.');
            }
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json() as HistoryResponse;
            return data.history;
        } catch (error) {
            console.error('DevMentor history error:', error);
            return [];
        }
    }

    async clearHistory(projectPath?: string): Promise<void> {
        try {
            const url = projectPath ? `${this.baseUrl}/history?project_path=${encodeURIComponent(projectPath)}` : `${this.baseUrl}/history`;
            await fetch(url, { method: 'DELETE', headers: this.headers() });
        } catch (error) {
            console.error('DevMentor clear history error:', error);
        }
    }
}
