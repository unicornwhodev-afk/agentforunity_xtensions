"""Tests for the RAG indexer module."""
import pytest
from src.rag.indexer import (
    CodeChunk,
    chunk_csharp,
    chunk_markdown,
    chunk_shader,
    compute_content_hash,
)


def test_chunk_csharp_small_file():
    """Test small C# file returns single chunk."""
    source = "public class Test {\n    void Update() {}\n}"
    chunks = chunk_csharp("Test.cs", source)
    assert len(chunks) == 1
    assert chunks[0].symbol == "file"


def test_chunk_csharp_with_methods():
    """Test C# file chunking by method boundaries."""
    source = """public class Test {
    void Start() {
        // init
    }
    void Update() {
        // update
    }
    void OnDestroy() {
        // cleanup
    }
}"""
    chunks = chunk_csharp("Test.cs", source)
    assert len(chunks) >= 2
    assert any(c.symbol == "Start" for c in chunks)
    assert any(c.symbol == "Update" for c in chunks)


def test_chunk_markdown():
    """Test markdown chunking by headings."""
    source = """# Title
Some intro text.

## Section 1
Content 1.

## Section 2
Content 2.
"""
    chunks = chunk_markdown("doc.md", source)
    assert len(chunks) >= 2
    assert chunks[0].source_type == "kb"


def test_chunk_shader():
    """Test shader chunking."""
    source = """Shader "Custom/Test" {
    SubShader {
        Pass {
            float4 frag(v2f i) : SV_Target {
                return float4(1,0,0,1);
            }
        }
    }
}"""
    chunks = chunk_shader("Test.shader", source)
    assert len(chunks) >= 1
    assert chunks[0].source_type == "shader"


def test_compute_content_hash():
    """Test content hash is deterministic."""
    content = "test content"
    h1 = compute_content_hash(content)
    h2 = compute_content_hash(content)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex