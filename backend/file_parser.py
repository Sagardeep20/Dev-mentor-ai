import os
from pathlib import Path
from typing import List, Dict
from langchain_core.documents import Document


CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r',
    '.lua', '.pl', '.sh', '.bash', '.zsh', '.ps1', '.sql', '.html', '.css',
    '.scss', '.sass', '.less', '.json', '.yaml', '.yml', '.xml', '.md',
    '.vue', '.svelte', '.dart', '.ex', '.exs', '.erl', '.hrl'
}

SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
    '.env', 'dist', 'build', 'out', 'target', 'bin', 'obj', '.idea',
    '.vscode', '.pytest_cache', '.mypy_cache', 'vendor', 'packages',
    '.next', '.nuxt', 'coverage', '.nyc_output', 'tmp', 'temp'
}


def is_code_file(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in CODE_EXTENSIONS


def should_skip_path(path: str) -> bool:
    parts = Path(path).parts
    return any(skip_dir in parts for skip_dir in SKIP_DIRS)


def read_file_safely(file_path: str) -> str:
    encodings = ['utf-8', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return ""


def walk_project(project_path: str) -> List[Dict]:
    files_data = []
    project_root = Path(project_path)
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in files:
            file_path = Path(root) / filename
            if not is_code_file(str(file_path)):
                continue
            if should_skip_path(str(file_path)):
                continue
            try:
                relative_path = str(file_path.relative_to(project_root))
            except ValueError:
                relative_path = str(file_path)
            content = read_file_safely(str(file_path))
            if not content:
                continue
            lines_count = len(content.splitlines())
            ext = file_path.suffix.lower()
            file_type = ext.lstrip('.') if ext else 'txt'
            files_data.append({
                'path': str(file_path),
                'relative_path': relative_path,
                'content': content,
                'file_type': file_type,
                'lines_count': lines_count
            })
    return files_data


def files_to_documents(files_data: List[Dict]) -> List[Document]:
    documents = []
    for file_info in files_data:
        doc = Document(
            page_content=file_info['content'],
            metadata={
                'source': file_info['relative_path'],
                'full_path': file_info['path'],
                'file_type': file_info['file_type'],
                'lines': file_info['lines_count']
            }
        )
        documents.append(doc)
    return documents


if __name__ == "__main__":
    import sys
    test_path = sys.argv[1] if len(sys.argv) > 1 else ".."
    print(f"Scanning project: {test_path}")
    files = walk_project(test_path)
    print(f"\nFound {len(files)} code files:")
    total_lines = 0
    for f in files[:10]:
        print(f"  - {f['relative_path']} ({f['lines_count']} lines)")
        total_lines += f['lines_count']
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more files")
    print(f"\nTotal: {len(files)} files, ~{total_lines} lines")
    docs = files_to_documents(files)
    print(f"Converted to {len(docs)} LangChain Documents")
