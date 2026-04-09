import os
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from config import CHROMA_DIR, EMBEDDING_MODEL, DEFAULT_PROJECT_PATH
from file_parser import walk_project, files_to_documents

# Maximum workers for parallel processing
MAX_WORKERS = min(os.cpu_count() or 4, 8)

# Batch size for processing files
BATCH_SIZE = 50


def get_embeddings():
    """Create embedding model (1024-dimensional vectors for bge-large-en-v1.5)."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'}
    )


def get_text_splitter():
    """Create text splitter for code chunks."""
    return RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )


def get_project_chroma_path(project_path: str, user_id: str = None) -> Path:
    """Get user- and project-specific ChromaDB path."""
    path_hash = hashlib.md5(project_path.encode()).hexdigest()[:12]
    if user_id:
        chroma_path = Path(CHROMA_DIR) / f"user_{user_id}_project_{path_hash}"
    else:
        chroma_path = Path(CHROMA_DIR) / f"project_{path_hash}"
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chroma_path


def _process_file_batch(files_batch: List[Dict]) -> List:
    """Process a batch of files and return documents (for multiprocessing)."""
    from langchain_core.documents import Document

    documents = []
    for file_info in files_batch:
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


def ingest_project(project_path: str = None, user_id: str = None) -> Dict:
    """Ingest project into user-specific ChromaDB with parallel processing."""
    if project_path is None:
        project_path = str(DEFAULT_PROJECT_PATH)

    print(f"Starting ingestion of: {project_path} (user: {user_id})")

    files_data = walk_project(project_path)
    if not files_data:
        return {"status": "error", "files_found": 0, "chunks_created": 0}

    print(f"Found {len(files_data)} files")

    # Parallel document creation
    print(f"Processing files with {MAX_WORKERS} workers...")
    all_documents = []

    # Split files into batches
    batches = [files_data[i:i + BATCH_SIZE] for i in range(0, len(files_data), BATCH_SIZE)]

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_process_file_batch, batch): i for i, batch in enumerate(batches)}
        for future in as_completed(futures):
            try:
                docs = future.result()
                all_documents.extend(docs)
            except Exception as e:
                print(f"Batch processing error: {e}")

    print(f"Converted {len(files_data)} files to {len(all_documents)} documents")

    # Split documents into chunks
    text_splitter = get_text_splitter()
    chunks = text_splitter.split_documents(all_documents)
    print(f"Split into {len(chunks)} chunks")

    embeddings = get_embeddings()

    # Use user- and project-specific ChromaDB
    chroma_path = get_project_chroma_path(project_path, user_id)

    # Clear existing collection for this user+project
    if chroma_path.exists():
        try:
            import shutil
            shutil.rmtree(chroma_path)
            chroma_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(chroma_path)
    )

    print(f"Stored in ChromaDB at: {chroma_path}")

    return {
        "status": "success",
        "files_found": len(files_data),
        "chunks_created": len(chunks)
    }


def ingest_project_async(project_path: str = None):
    """Async wrapper for ingest_project (for use with FastAPI)."""
    import asyncio
    return asyncio.to_thread(ingest_project, project_path)


def retrieve_context(query: str, project_path: str = None, user_id: str = None, k: int = 8) -> Tuple[str, List[Dict]]:
    """Retrieve relevant context for a query from user-specific ChromaDB."""
    if project_path is None:
        project_path = str(DEFAULT_PROJECT_PATH)

    chroma_path = get_project_chroma_path(project_path, user_id)

    if not chroma_path.exists():
        return "No project ingested yet. Please analyze your project first.", []

    embeddings = get_embeddings()
    vectorstore = Chroma(
        persist_directory=str(chroma_path),
        embedding_function=embeddings
    )

    results = vectorstore.similarity_search_with_score(query, k=k)

    if not results:
        return "No relevant context found.", []

    context_parts = []
    sources = []

    for doc, score in results:
        context_parts.append(f"[{doc.metadata.get('source', 'unknown')}]\n{doc.page_content}")
        sources.append({
            "source": doc.metadata.get('source', 'unknown'),
            "full_path": doc.metadata.get('full_path', ''),
            "score": float(score),
            "preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        })

    context = "\n\n---\n\n".join(context_parts)

    return context, sources


def check_ingestion_status(project_path: str = None, user_id: str = None) -> Dict:
    """Check if project is already ingested for a user."""
    if project_path is None:
        project_path = str(DEFAULT_PROJECT_PATH)

    chroma_path = get_project_chroma_path(project_path, user_id)

    if not chroma_path.exists():
        return {"ingested": False, "chunks": 0}

    try:
        embeddings = get_embeddings()
        vectorstore = Chroma(
            persist_directory=str(chroma_path),
            embedding_function=embeddings
        )
        count = vectorstore._collection.count()
        return {"ingested": True, "chunks": count}
    except:
        return {"ingested": False, "chunks": 0}


if __name__ == "__main__":
    print("=" * 50)
    print("Testing RAG Pipeline")
    print("=" * 50)

    print("\n1. Ingesting project...")
    result = ingest_project()
    print(f"   Result: {result}")

    print("\n2. Testing retrieval...")
    context, sources = retrieve_context("what files exist in this project")
    print(f"   Found {len(sources)} relevant chunks")

    if sources:
        print(f"\n   Top source: {sources[0]['source']}")
        print(f"   Score: {sources[0]['score']:.4f}")

    print("\n3. Checking status...")
    status = check_ingestion_status()
    print(f"   Status: {status}")

    print("\n" + "=" * 50)
    print("RAG Pipeline Test Complete!")
    print("=" * 50)