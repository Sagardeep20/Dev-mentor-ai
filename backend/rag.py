import os
from pathlib import Path
from typing import Dict, List, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from config import CHROMA_DIR, EMBEDDING_MODEL, DEFAULT_PROJECT_PATH
from file_parser import walk_project, files_to_documents


def get_embeddings():
    """Create embedding model (384-dimensional vectors)."""
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


def ingest_project(project_path: str = None) -> Dict:
    """Ingest project into ChromaDB."""
    if project_path is None:
        project_path = str(DEFAULT_PROJECT_PATH)

    print(f"Starting ingestion of: {project_path}")

    files_data = walk_project(project_path)
    if not files_data:
        return {"status": "error", "files_found": 0, "chunks_created": 0}

    print(f"Found {len(files_data)} files")

    documents = files_to_documents(files_data)
    print(f"Converted to {len(documents)} documents")

    text_splitter = get_text_splitter()
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")

    embeddings = get_embeddings()

    chroma_path = Path(CHROMA_DIR) / "devmentor"
    chroma_path.mkdir(parents=True, exist_ok=True)

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


def retrieve_context(query: str, k: int = 8) -> Tuple[str, List[Dict]]:
    """Retrieve relevant context for a query."""
    chroma_path = Path(CHROMA_DIR) / "devmentor"

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


def check_ingestion_status() -> Dict:
    """Check if project is already ingested."""
    chroma_path = Path(CHROMA_DIR) / "devmentor"

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
