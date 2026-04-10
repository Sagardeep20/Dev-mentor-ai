import * as vscode from 'vscode';
import * as fs from 'fs';
import { ApiClient } from './api-client';

let apiClient: ApiClient | null = null;
let activated = false;

function getBackendUrl(): string {
	const config = vscode.workspace.getConfiguration('devmentor');
	return config.get<string>('backendUrl', 'http://localhost:8000');
}

async function getApiKey(context: vscode.ExtensionContext): Promise<string | undefined> {
	return context.secrets.get('devmentor-api-key');
}

async function setApiKey(context: vscode.ExtensionContext, key: string): Promise<void> {
	await context.secrets.store('devmentor-api-key', key);
}

async function clearApiKey(context: vscode.ExtensionContext): Promise<void> {
	await context.secrets.delete('devmentor-api-key');
}

function initApiClient(baseUrl: string, apiKey: string): ApiClient {
	apiClient = new ApiClient({ baseUrl, apiKey });
	return apiClient;
}

export function activate(context: vscode.ExtensionContext) {
	if (activated) {
		console.log('DevMentor already activated, skipping');
		return;
	}
	activated = true;
	console.log('DevMentor activating...');
	
	const provider = new DevMentorViewProvider(context);
	context.subscriptions.push(
		vscode.window.registerWebviewViewProvider('devmentor.main', provider)
	);

	context.subscriptions.push(
		vscode.commands.registerCommand('devmentor.analyzeProject', async () => {
			const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
			if (!workspacePath) {
				vscode.window.showWarningMessage('No project folder open.');
				return;
			}
			const client = await getAuthenticatedClient(context);
			if (!client) return;
			const result = await client.analyze(workspacePath);
			vscode.window.showInformationMessage(`Analysis complete: ${result.files_found} files found.`);
		}),

		vscode.commands.registerCommand('devmentor.explainSelection', async () => {
			const client = await getAuthenticatedClient(context);
			if (!client) return;

			const editor = vscode.window.activeTextEditor;
			if (!editor) {
				vscode.window.showWarningMessage('No active file.');
				return;
			}
			const selection = editor.selection;
			if (selection.isEmpty) {
				vscode.window.showWarningMessage('No code selected.');
				return;
			}
			const selectedText = editor.document.getText(selection);
			const filePath = editor.document.uri.fsPath;
			const language = editor.document.languageId;
			const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';

			const result = await client.explainCode(selectedText, filePath, language, workspacePath);
			const panel = vscode.window.createWebviewPanel(
				'devmentor.explain',
				'DevMentor - Code Explanation',
				vscode.ViewColumn.One,
				{ enableScripts: true }
			);
			panel.webview.html = `<!DOCTYPE html>
<html><body style="background:#1e1e1e;color:#d4d4d4;font-family:system-ui;padding:20px;line-height:1.6">
<h2 style="color:#6366f1">DevMentor Explanation</h2>
<p style="white-space:pre-wrap">${result.explanation.replace(/\n/g, '<br>')}</p>
<p style="color:#8b949e;font-size:12px">Language: ${result.language}${result.cached ? ' (cached)' : ''}</p>
</body></html>`;
		}),

		vscode.commands.registerCommand('devmentor.suggestImprovements', async () => {
			const client = await getAuthenticatedClient(context);
			if (!client) return;

			const editor = vscode.window.activeTextEditor;
			if (!editor) {
				vscode.window.showWarningMessage('No active file.');
				return;
			}
			const selection = editor.selection;
			if (selection.isEmpty) {
				vscode.window.showWarningMessage('No code selected.');
				return;
			}
			const selectedText = editor.document.getText(selection);
			const filePath = editor.document.uri.fsPath;
			const language = editor.document.languageId;
			const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';

			vscode.window.withProgress({
				location: vscode.ProgressLocation.Notification,
				title: 'DevMentor: Analyzing code for improvements...'
			}, async () => {
				const result = await client.suggestImprovements(selectedText, filePath, language, workspacePath);
				const panel = vscode.window.createWebviewPanel(
					'devmentor.suggestions',
					'DevMentor - Suggestions',
					vscode.ViewColumn.One,
					{ enableScripts: true }
				);
				panel.webview.html = `<!DOCTYPE html>
<html><body style="background:#1e1e1e;color:#d4d4d4;font-family:system-ui;padding:20px;line-height:1.6">
<h2 style="color:#6366f1">DevMentor Suggestions</h2>
<p style="white-space:pre-wrap">${result.suggestions.replace(/\n/g, '<br>')}</p>
</body></html>`;
			});
		}),

		vscode.commands.registerCommand('devmentor.analyzeIssues', async () => {
			const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
			if (!workspacePath) {
				vscode.window.showWarningMessage('No project folder open.');
				return;
			}
			const client = await getAuthenticatedClient(context);
			if (!client) return;
			vscode.window.withProgress({
				location: vscode.ProgressLocation.Notification,
				title: 'DevMentor: Scanning for issues...'
			}, async () => {
				const result = await client.analyzeIssues(workspacePath);
				if (result.total_issues > 0) {
					vscode.window.showInformationMessage(`Found ${result.total_issues} issues: ${result.issues_by_severity.critical || 0} critical, ${result.issues_by_severity.high || 0} high`);
				} else {
					vscode.window.showInformationMessage('No issues found!');
				}
			});
		}),

		vscode.commands.registerCommand('devmentor.startQuiz', async () => {
			const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
			if (!workspacePath) {
				vscode.window.showWarningMessage('No project folder open.');
				return;
			}
			const client = await getAuthenticatedClient(context);
			if (!client) return;
			const result = await client.startQuiz(workspacePath, 5, 'beginner');
			if (result.quiz_session_id) {
				vscode.window.showInformationMessage(`Quiz started with ${result.total_questions} questions! Check the DevMentor sidebar.`);
			} else {
				vscode.window.showErrorMessage('Failed to start quiz. Analyze your project first.');
			}
		}),

		vscode.commands.registerCommand('devmentor.clearHistory', async () => {
			vscode.window.showInformationMessage('Conversation cleared.');
		}),

		vscode.commands.registerCommand('devmentor.showStatus', async () => {
			const client = await getAuthenticatedClient(context);
			if (!client) return;
			const status = await client.getStatus();
			vscode.window.showInformationMessage(
				`DevMentor: ${status.ingested ? 'Project ingested' : 'No project ingested'} | Chunks: ${status.chunks}`
			);
		})
	);
}

async function getAuthenticatedClient(context: vscode.ExtensionContext): Promise<ApiClient | null> {
	const apiKey = await getApiKey(context);
	if (!apiKey) {
		vscode.window.showWarningMessage('Please login to DevMentor first.');
		return null;
	}
	return initApiClient(getBackendUrl(), apiKey);
}

export function deactivate() {}

class DevMentorViewProvider implements vscode.WebviewViewProvider {
	private context: vscode.ExtensionContext;
	private view: vscode.WebviewView | null = null;

	constructor(context: vscode.ExtensionContext) {
		this.context = context;
	}

	async resolveWebviewView(webviewView: vscode.WebviewView) {
		this.view = webviewView;
		const extensionUri = vscode.Uri.joinPath(this.context.extensionUri, 'src', 'webview');
		webviewView.webview.options = {
			enableScripts: true,
			localResourceRoots: [extensionUri]
		};

		const htmlPath = vscode.Uri.joinPath(this.context.extensionUri, 'src', 'webview', 'index.html');
		const htmlContent = fs.readFileSync(htmlPath.fsPath, 'utf8');
		webviewView.webview.html = htmlContent;

		webviewView.webview.onDidReceiveMessage(async (message: any) => {
			try {
				const baseUrl = getBackendUrl();

				if (message.type === 'checkAuth') {
					const key = await getApiKey(this.context);
					console.log('DevMentor checkAuth: key=', key ? 'present' : 'missing');
					if (key) {
						const client = new ApiClient({ baseUrl, apiKey: key });
						const isValid = await client.checkApiKey();
						console.log('DevMentor checkAuth: isValid=', isValid);
						if (isValid) {
							initApiClient(baseUrl, key);
							webviewView.webview.postMessage({ type: 'authSuccess' });
						} else {
							await clearApiKey(this.context);
							webviewView.webview.postMessage({ type: 'showAuth' });
						}
					} else {
						webviewView.webview.postMessage({ type: 'showAuth' });
					}
				} else if (message.type === 'checkBackend') {
					console.log('DevMentor checkBackend: url=', baseUrl);
					const connected = await this.checkBackend(baseUrl);
					console.log('DevMentor checkBackend: connected=', connected);
					webviewView.webview.postMessage({ type: 'backendStatus', status: { connected } });
				} else if (message.type === 'login') {
					console.log('DevMentor login: email=', message.email);
					const client = new ApiClient({ baseUrl, apiKey: '' });
					const result = await client.login(message.email, message.password);
					console.log('DevMentor login: result=', result);
					if (result.error) {
						webviewView.webview.postMessage({ type: 'authError', text: result.error });
					} else {
						await setApiKey(this.context, result.api_key);
						initApiClient(baseUrl, result.api_key);
						webviewView.webview.postMessage({ type: 'authSuccess' });
					}
				} else if (message.type === 'register') {
					const client = new ApiClient({ baseUrl, apiKey: '' });
					const result = await client.register(message.username, message.email, message.password, message.groqKey);
					if (result.error) {
						webviewView.webview.postMessage({ type: 'authError', text: result.error });
					} else {
						await setApiKey(this.context, result.api_key);
						initApiClient(baseUrl, result.api_key);
						webviewView.webview.postMessage({ type: 'authSuccess' });
					}
				} else if (message.type === 'ask') {
					const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
					const client = await this.getClient();
					if (!client) {
						webviewView.webview.postMessage({ type: 'error', text: 'Not authenticated. Please login.' });
						return;
					}
					const result = await client.ask(message.text || '', workspacePath || '');
					if (result.error) {
						webviewView.webview.postMessage({ type: 'error', text: result.error });
					} else {
						webviewView.webview.postMessage({
							type: 'response',
							text: result.answer,
							sources: result.sources
						});
					}
				} else if (message.type === 'analyze') {
					const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
					if (!workspacePath) {
						webviewView.webview.postMessage({ type: 'error', text: 'No project folder open. Please open a folder first.' });
						return;
					}
					const client = await this.getClient();
					if (!client) {
						webviewView.webview.postMessage({ type: 'error', text: 'Not authenticated. Please login first.' });
						return;
					}
					const result = await client.analyze(workspacePath);
					if (result.error) {
						webviewView.webview.postMessage({ type: 'error', text: result.error });
					} else {
						webviewView.webview.postMessage({ type: 'response', text: `Analysis complete: ${result.files_found} files, ${result.chunks_created} chunks.` });
					}
				} else if (message.type === 'getHistory') {
					const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
					const client = await this.getClient();
					if (!client) {
						webviewView.webview.postMessage({ type: 'error', text: 'Not authenticated. Please login first.' });
						return;
					}
					const history = await client.getHistory(workspacePath);
					webviewView.webview.postMessage({ type: 'history', history });
				} else if (message.type === 'clear') {
					const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
					const client = await this.getClient();
					if (!client) return;
					await client.clearHistory(workspacePath);
					webviewView.webview.postMessage({ type: 'response', text: 'Conversation cleared.' });
				} else if (message.type === 'checkStatus') {
					const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
					const client = await this.getClient();
					if (!client) return;
					const status = await client.getStatus(workspacePath);
					webviewView.webview.postMessage({ type: 'status', status });
				} else if (message.type === 'startQuiz') {
					const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
					if (!workspacePath) {
						webviewView.webview.postMessage({ type: 'error', text: 'No project folder open.' });
						return;
					}
					const client = await this.getClient();
					if (!client) return;
					const result = await client.startQuiz(workspacePath, 5, 'beginner');
					webviewView.webview.postMessage({ type: 'quizStarted', quizSessionId: result.quiz_session_id, totalQuestions: result.total_questions });
				} else if (message.type === 'analyzeIssues') {
					const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
					if (!workspacePath) {
						webviewView.webview.postMessage({ type: 'error', text: 'No project folder open.' });
						return;
					}
					const client = await this.getClient();
					if (!client) {
						webviewView.webview.postMessage({ type: 'error', text: 'Not authenticated. Please login first.' });
						return;
					}
					try {
						const result = await client.analyzeIssues(workspacePath);
						webviewView.webview.postMessage({ type: 'issuesResult', totalIssues: result.total_issues, issuesBySeverity: result.issues_by_severity });
					} catch (e: any) {
						webviewView.webview.postMessage({ type: 'error', text: e.message });
					}
				} else if (message.type === 'generatePlan') {
					const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
					if (!workspacePath) {
						webviewView.webview.postMessage({ type: 'error', text: 'No project folder open.' });
						return;
					}
					const client = await this.getClient();
					if (!client) return;
					const result = await client.generateLearningPlan(workspacePath);
					webviewView.webview.postMessage({ type: 'learningPlan', plan: result.plan, sources: result.sources });
				} else if (message.type === 'loadQuizQuestion') {
					const client = await this.getClient();
					if (!client) return;
					const question = await client.getQuizQuestion(message.quizSessionId || '');
					webviewView.webview.postMessage({
						type: 'quizQuestion',
						question_index: question.question_index,
						question_id: question.question_id,
						question_text: question.question_text,
						question_type: question.question_type,
						code_context: question.code_context,
						options: question.options,
						completed: false
					});
				} else if (message.type === 'submitQuizAnswer') {
					const client = await this.getClient();
					if (!client) return;
					const result = await client.submitQuizAnswer(message.quizSessionId || '', message.questionId || '', message.answer || '');
					webviewView.webview.postMessage({
						type: 'quizAnswer',
						correct: result.correct,
						correct_answer: result.correct_answer,
						explanation: result.explanation,
						next_question_available: result.next_question_available
					});
				} else if (message.type === 'loadQuizResults') {
					const client = await this.getClient();
					if (!client) return;
					const results = await client.getQuizResults(message.quizSessionId || '');
					webviewView.webview.postMessage({
						type: 'quizResults',
						score_percentage: results.score_percentage,
						correct_answers: results.correct_answers,
						total_questions: results.total_questions
					});
				}
			} catch (err: any) {
				webviewView.webview.postMessage({ type: 'error', text: err.message || 'An unexpected error occurred.' });
			}
		});
	}

	private async checkBackend(baseUrl: string): Promise<boolean> {
		try {
			const response = await fetch(`${baseUrl}/health`);
			return response.ok;
		} catch {
			return false;
		}
	}

	private async getClient(): Promise<ApiClient | null> {
		if (apiClient) return apiClient;
		const apiKey = await getApiKey(this.context);
		if (!apiKey) return null;
		return initApiClient(getBackendUrl(), apiKey);
	}
}
