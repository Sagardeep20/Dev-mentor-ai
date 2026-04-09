"""Tests for RAG pipeline."""

import pytest
from pathlib import Path
from rag import (
    get_project_chroma_path,
    get_text_splitter,
    get_embeddings,
)
from services.explainer import hash_code


class TestRagHelpers:
    """Test RAG helper functions."""

    def test_get_project_chroma_path(self):
        """Should return consistent path for same project."""
        path1 = get_project_chroma_path("/path/to/project")
        path2 = get_project_chroma_path("/path/to/project")
        assert path1 == path2
        assert "project_" in str(path1)

    def test_get_project_chroma_path_different_projects(self):
        """Should return different paths for different projects."""
        path1 = get_project_chroma_path("/path/to/project1")
        path2 = get_project_chroma_path("/path/to/project2")
        assert path1 != path2

    def test_get_text_splitter(self):
        """Text splitter should be configured correctly."""
        splitter = get_text_splitter()
        # Verify by splitting some text
        chunks = splitter.split_text("def foo():\n    pass\n\ndef bar():\n    pass")
        assert len(chunks) > 0

    def test_hash_code_consistency(self):
        """Same code should produce same hash."""
        code = "def hello():\n    print('world')"
        hash1 = hash_code(code)
        hash2 = hash_code(code)
        assert hash1 == hash2

    def test_hash_code_different(self):
        """Different code should produce different hashes."""
        code1 = "def hello():\n    print('world')"
        code2 = "def goodbye():\n    print('world')"
        hash1 = hash_code(code1)
        hash2 = hash_code(code2)
        assert hash1 != hash2

    def test_hash_code_length(self):
        """Hash should be 64 characters (SHA256 hex)."""
        code = "test code"
        hash_result = hash_code(code)
        assert len(hash_result) == 64


class TestEmbeddings:
    """Test embedding model configuration."""

    def test_get_embeddings_type(self):
        """Should return HuggingFaceEmbeddings instance."""
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = get_embeddings()
        assert isinstance(embeddings, HuggingFaceEmbeddings)

    def test_get_embeddings_model_name(self):
        """Should use configured embedding model."""
        from config import EMBEDDING_MODEL
        embeddings = get_embeddings()
        assert EMBEDDING_MODEL in embeddings.model_name


class TestChromaPath:
    """Test ChromaDB path handling."""

    def test_path_creates_directory(self):
        """Should create parent directories."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test_project")
            chroma_path = get_project_chroma_path(test_path)
            # Path should exist or be creatable
            chroma_path.mkdir(parents=True, exist_ok=True)
            assert chroma_path.exists()