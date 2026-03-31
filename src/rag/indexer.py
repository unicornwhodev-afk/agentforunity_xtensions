"""RAG indexer — fetches C# scripts via MCP-Unity and indexes them in Qdrant.

Also indexes local KB markdown files, shaders, ScriptableObjects, and prefabs
for comprehensive FPS game knowledge retrieval.

Features:
- Extended indexing: C#, shaders, SO, prefabs, KB markdown
- Incremental indexing: hash-based change detection
- Metadata filtering: source type, namespace, path prefix
- Conversation memory storage
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.config import settings
from src.tools import mcp_unity

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    path: str
    symbol: str  # class / method / top-level
    content: str
    start_line: int
    end_line: int
    source_type: str = "code"  # code, kb, shader, so, prefab
    namespace: str = ""
    tags: list[str] = field(default_factory=list)


# ── chunking ─────────────────────────────────────────────────────────

_CLASS_RE = re.compile(
    r"^(\s*(?:public|private|protected|internal|abstract|sealed|static|partial)\s+)*"
    r"class\s+(\w+)",
    re.MULTILINE,
)
_METHOD_RE = re.compile(
    r"^(\s*(?:public|private|protected|internal|static|virtual|override|abstract|async)\s+)+"
    r"[\w<>\[\],\s]+\s+(\w+)\s*\(",
    re.MULTILINE,
)


def chunk_csharp(path: str, source: str) -> list[CodeChunk]:
    """Split a C# file into meaningful chunks (class-level then method-level)."""
    lines = source.splitlines(keepends=True)
    if len(lines) <= settings.rag_chunk_max_tokens:
        return [CodeChunk(path=path, symbol="file", content=source, start_line=1, end_line=len(lines))]

    chunks: list[CodeChunk] = []
    # find method boundaries
    boundaries: list[tuple[int, str]] = []
    for m in _METHOD_RE.finditer(source):
        line_no = source[: m.start()].count("\n") + 1
        boundaries.append((line_no, m.group(2)))

    if not boundaries:
        # no methods found — chunk by fixed windows
        step = settings.rag_chunk_max_tokens
        for i in range(0, len(lines), step):
            chunk_lines = lines[i : i + step]
            chunks.append(
                CodeChunk(
                    path=path,
                    symbol="block",
                    content="".join(chunk_lines),
                    start_line=i + 1,
                    end_line=min(i + step, len(lines)),
                )
            )
        return chunks

    # split on method boundaries
    for idx, (start, name) in enumerate(boundaries):
        end = boundaries[idx + 1][0] - 1 if idx + 1 < len(boundaries) else len(lines)
        chunk_content = "".join(lines[start - 1 : end])
        chunks.append(CodeChunk(path=path, symbol=name, content=chunk_content, start_line=start, end_line=end))

    return chunks


# ── embedding ────────────────────────────────────────────────────────


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call the local embedding server (BGE-M3)."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.embedding_url}/embed",
            json={"texts": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]


# ── qdrant helpers ───────────────────────────────────────────────────


async def ensure_collection(client: AsyncQdrantClient, name: str) -> None:
    collections = await client.get_collections()
    existing = {c.name for c in collections.collections}
    if name not in existing:
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", name)


# ── main indexing pipeline ───────────────────────────────────────────


async def index_project_code() -> int:
    """Fetch all scripts via MCP-Unity, chunk, embed, and upsert into Qdrant."""
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    await ensure_collection(qdrant, settings.qdrant_collection_code)

    # 1. list scripts
    scripts_result = await mcp_unity.list_scripts()
    script_paths: list[str] = scripts_result.get("scripts", [])
    logger.info("Found %d scripts to index", len(script_paths))

    total_chunks = 0
    batch_size = 16

    for i in range(0, len(script_paths), batch_size):
        batch_paths = script_paths[i : i + batch_size]
        # fetch content
        contents: list[tuple[str, str]] = []
        for p in batch_paths:
            try:
                result = await mcp_unity.get_script_content(p)
                contents.append((p, result.get("content", "")))
            except Exception:
                logger.warning("Failed to fetch %s, skipping", p)

        # chunk
        all_chunks: list[CodeChunk] = []
        for path, source in contents:
            all_chunks.extend(chunk_csharp(path, source))

        if not all_chunks:
            continue

        # embed
        texts = [f"// {c.path}:{c.symbol}\n{c.content}" for c in all_chunks]
        embeddings = await embed_texts(texts)

        # upsert
        points = [
            PointStruct(
                id=int(hashlib.md5(f"{c.path}:{c.start_line}".encode()).hexdigest(), 16) & 0x7FFFFFFFFFFFFFFF,
                vector=emb,
                payload={
                    "path": c.path,
                    "symbol": c.symbol,
                    "content": c.content,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                },
            )
            for c, emb in zip(all_chunks, embeddings)
        ]
        await qdrant.upsert(collection_name=settings.qdrant_collection_code, points=points)
        total_chunks += len(points)
        logger.info("Indexed %d chunks (batch %d/%d)", len(points), i // batch_size + 1, -(-len(script_paths) // batch_size))

    await qdrant.close()
    logger.info("Indexing complete: %d total chunks", total_chunks)
    return total_chunks


# ── KB markdown indexer ──────────────────────────────────────────────

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


def chunk_markdown(path: str, source: str) -> list[CodeChunk]:
    """Split a markdown KB file into section-based chunks."""
    lines = source.splitlines(keepends=True)
    if len(lines) <= settings.rag_chunk_max_tokens:
        return [CodeChunk(path=path, symbol="document", content=source, start_line=1, end_line=len(lines))]

    chunks: list[CodeChunk] = []
    boundaries: list[tuple[int, str]] = []

    for m in _HEADING_RE.finditer(source):
        line_no = source[: m.start()].count("\n") + 1
        boundaries.append((line_no, m.group(2).strip()))

    if not boundaries:
        step = settings.rag_chunk_max_tokens
        for i in range(0, len(lines), step):
            chunk_lines = lines[i : i + step]
            chunks.append(
                CodeChunk(path=path, symbol="block", content="".join(chunk_lines), start_line=i + 1, end_line=min(i + step, len(lines)))
            )
        return chunks

    for idx, (start, name) in enumerate(boundaries):
        end = boundaries[idx + 1][0] - 1 if idx + 1 < len(boundaries) else len(lines)
        chunk_content = "".join(lines[start - 1 : end])
        if chunk_content.strip():
            chunks.append(CodeChunk(path=path, symbol=name, content=chunk_content, start_line=start, end_line=end))

    return chunks


async def index_kb_documents(kb_dir: str | None = None) -> int:
    """Index all markdown files from the kb/ directory into Qdrant."""
    kb_path = Path(kb_dir) if kb_dir else Path(__file__).resolve().parent.parent.parent / "kb"
    if not kb_path.exists():
        logger.warning("KB directory not found: %s", kb_path)
        return 0

    md_files = sorted(kb_path.glob("*.md"))
    if not md_files:
        logger.warning("No .md files found in %s", kb_path)
        return 0

    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    await ensure_collection(qdrant, settings.qdrant_collection_docs)

    total_chunks = 0

    for md_file in md_files:
        source = md_file.read_text(encoding="utf-8")
        chunks = chunk_markdown(md_file.name, source)
        if not chunks:
            continue

        texts = [f"[KB: {c.path}] {c.symbol}\n{c.content}" for c in chunks]
        embeddings = await embed_texts(texts)

        points = [
            PointStruct(
                id=int(hashlib.md5(f"kb:{c.path}:{c.start_line}".encode()).hexdigest(), 16) & 0x7FFFFFFFFFFFFFFF,
                vector=emb,
                payload={
                    "path": c.path,
                    "symbol": c.symbol,
                    "content": c.content,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "source": "kb",
                    "source_type": "kb",
                    "namespace": "",
                    "tags": [],
                },
            )
            for c, emb in zip(chunks, embeddings)
        ]
        await qdrant.upsert(collection_name=settings.qdrant_collection_docs, points=points)
        total_chunks += len(points)
        logger.info("Indexed KB file %s: %d chunks", md_file.name, len(points))

    await qdrant.close()
    logger.info("KB indexing complete: %d total chunks from %d files", total_chunks, len(md_files))
    return total_chunks


# ── Shader chunker ───────────────────────────────────────────────────

_SHADER_FUNC_RE = re.compile(
    r"^\s*(?:void|float[234]?|half[234]?|int[234]?|bool|fixed[234]?|COLOR|SV_Target)\s+(\w+)\s*\(",
    re.MULTILINE,
)
_SHADER_PASS_RE = re.compile(r"^\s*Pass\s*\{", re.MULTILINE)


def chunk_shader(path: str, source: str) -> list[CodeChunk]:
    """Split a shader file into meaningful chunks (passes, functions)."""
    lines = source.splitlines(keepends=True)
    if len(lines) <= settings.rag_chunk_max_tokens:
        return [CodeChunk(path=path, symbol="shader", content=source, start_line=1, end_line=len(lines), source_type="shader")]

    chunks: list[CodeChunk] = []

    # Try to split by Pass blocks first
    pass_boundaries: list[tuple[int, str]] = []
    for m in _SHADER_PASS_RE.finditer(source):
        line_no = source[: m.start()].count("\n") + 1
        pass_boundaries.append((line_no, f"Pass_{len(pass_boundaries) + 1}"))

    if pass_boundaries:
        for idx, (start, name) in enumerate(pass_boundaries):
            end = pass_boundaries[idx + 1][0] - 1 if idx + 1 < len(pass_boundaries) else len(lines)
            chunk_content = "".join(lines[start - 1 : end])
            chunks.append(CodeChunk(path=path, symbol=name, content=chunk_content, start_line=start, end_line=end, source_type="shader"))

    # If no passes, try function boundaries
    if not chunks:
        func_boundaries: list[tuple[int, str]] = []
        for m in _SHADER_FUNC_RE.finditer(source):
            line_no = source[: m.start()].count("\n") + 1
            func_boundaries.append((line_no, m.group(1)))

        if func_boundaries:
            for idx, (start, name) in enumerate(func_boundaries):
                end = func_boundaries[idx + 1][0] - 1 if idx + 1 < len(func_boundaries) else len(lines)
                chunk_content = "".join(lines[start - 1 : end])
                chunks.append(CodeChunk(path=path, symbol=name, content=chunk_content, start_line=start, end_line=end, source_type="shader"))

    # Fallback: fixed window chunking
    if not chunks:
        step = settings.rag_chunk_max_tokens
        for i in range(0, len(lines), step):
            chunk_lines = lines[i : i + step]
            chunks.append(CodeChunk(path=path, symbol="block", content="".join(chunk_lines), start_line=i + 1, end_line=min(i + step, len(lines)), source_type="shader"))

    return chunks


# ── ScriptableObject chunker ─────────────────────────────────────────

_SO_FIELD_RE = re.compile(r"^\s*public\s+(?:float|int|string|bool|Vector[23]|Color|AnimationCurve)\s+(\w+)", re.MULTILINE)


def chunk_scriptable_object(path: str, source: str) -> list[CodeChunk]:
    """Split a ScriptableObject C# class into field and method chunks."""
    # Use C# chunker but add SO-specific metadata
    chunks = chunk_csharp(path, source)
    for chunk in chunks:
        chunk.source_type = "so"
        # Extract field names for tagging
        for m in _SO_FIELD_RE.finditer(chunk.content):
            chunk.tags.append(f"field:{m.group(1)}")
    return chunks


# ── Incremental indexing ─────────────────────────────────────────────


def compute_content_hash(content: str) -> str:
    """Compute a stable hash for content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def get_indexed_hashes(qdrant: AsyncQdrantClient, collection: str) -> dict[str, str]:
    """Get hashes of all indexed documents from Qdrant."""
    hashes: dict[str, str] = {}
    try:
        # Scroll through all points to get their paths and hashes
        offset = None
        while True:
            result = await qdrant.scroll(
                collection_name=collection,
                limit=100,
                offset=offset,
                with_payload=["path", "content_hash"],
                with_vectors=False,
            )
            points, offset = result
            if not points:
                break
            for point in points:
                path = point.payload.get("path", "")
                content_hash = point.payload.get("content_hash", "")
                if path and content_hash:
                    hashes[path] = content_hash
            if offset is None:
                break
    except Exception:
        logger.debug("Could not read indexed hashes (collection may be empty)")
    return hashes


async def index_project_code_incremental() -> dict[str, int]:
    """Incrementally index scripts: only re-index changed files.

    Returns dict with counts: {indexed, skipped, total}
    """
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    await ensure_collection(qdrant, settings.qdrant_collection_code)

    # Get currently indexed hashes
    indexed_hashes = await get_indexed_hashes(qdrant, settings.qdrant_collection_code)
    logger.info("Found %d previously indexed scripts", len(indexed_hashes))

    # List all current scripts
    scripts_result = await mcp_unity.list_scripts()
    script_paths: list[str] = scripts_result.get("scripts", [])
    logger.info("Found %d scripts in project", len(script_paths))

    total_chunks = 0
    indexed_count = 0
    skipped_count = 0
    batch_size = 16

    for i in range(0, len(script_paths), batch_size):
        batch_paths = script_paths[i : i + batch_size]

        # Fetch content and check for changes
        changed_contents: list[tuple[str, str, str]] = []  # (path, content, hash)
        for p in batch_paths:
            try:
                result = await mcp_unity.get_script_content(p)
                content = result.get("content", "")
                content_hash = compute_content_hash(content)

                # Skip if unchanged
                if indexed_hashes.get(p) == content_hash:
                    skipped_count += 1
                    continue

                changed_contents.append((p, content, content_hash))
                indexed_count += 1
            except Exception:
                logger.warning("Failed to fetch %s, skipping", p)

        if not changed_contents:
            continue

        # Chunk changed files
        all_chunks: list[CodeChunk] = []
        for path, source, _ in changed_contents:
            all_chunks.extend(chunk_csharp(path, source))

        if not all_chunks:
            continue

        # Embed
        texts = [f"// {c.path}:{c.symbol}\n{c.content}" for c in all_chunks]
        embeddings = await embed_texts(texts)

        # Create hash lookup
        hash_lookup = {path: h for path, _, h in changed_contents}

        # Upsert with metadata
        points = [
            PointStruct(
                id=int(hashlib.md5(f"{c.path}:{c.start_line}".encode()).hexdigest(), 16) & 0x7FFFFFFFFFFFFFFF,
                vector=emb,
                payload={
                    "path": c.path,
                    "symbol": c.symbol,
                    "content": c.content,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "content_hash": hash_lookup.get(c.path, ""),
                    "source_type": "code",
                    "indexed_at": time.time(),
                    "namespace": "",
                    "tags": [],
                },
            )
            for c, emb in zip(all_chunks, embeddings)
        ]
        await qdrant.upsert(collection_name=settings.qdrant_collection_code, points=points)
        total_chunks += len(points)
        logger.info("Indexed %d chunks from %d changed files (batch %d/%d)", len(points), len(changed_contents), i // batch_size + 1, -(-len(script_paths) // batch_size))

    await qdrant.close()
    logger.info("Incremental indexing complete: %d indexed, %d skipped, %d total chunks", indexed_count, skipped_count, total_chunks)
    return {"indexed": indexed_count, "skipped": skipped_count, "total_chunks": total_chunks, "total_files": len(script_paths)}


async def index_project_all_assets() -> dict[str, int]:
    """Index all project assets: C# scripts, shaders, SO, KB docs.

    Returns dict with counts per type.
    """
    results: dict[str, int] = {}

    # 1. Index C# scripts (incremental)
    code_result = await index_project_code_incremental()
    results["code_chunks"] = code_result["total_chunks"]
    results["code_files"] = code_result["total_files"]

    # 2. Index KB documents
    kb_count = await index_kb_documents()
    results["kb_chunks"] = kb_count

    # 3. Index shaders (via list_assets)
    try:
        shaders_result = await mcp_unity.list_assets(folder="Assets", file_extension=".shader", recursive=True)
        shader_paths = shaders_result.get("assets", [])
        logger.info("Found %d shader files", len(shader_paths))

        qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        await ensure_collection(qdrant, settings.qdrant_collection_code)
        indexed_hashes = await get_indexed_hashes(qdrant, settings.qdrant_collection_code)

        shader_chunks = 0
        for shader_path in shader_paths:
            try:
                content_result = await mcp_unity.get_script_content(shader_path)
                content = content_result.get("content", "")
                content_hash = compute_content_hash(content)

                if indexed_hashes.get(shader_path) == content_hash:
                    continue

                chunks = chunk_shader(shader_path, content)
                if not chunks:
                    continue

                texts = [f"[Shader: {c.path}] {c.symbol}\n{c.content}" for c in chunks]
                embeddings = await embed_texts(texts)

                points = [
                    PointStruct(
                        id=int(hashlib.md5(f"shader:{c.path}:{c.start_line}".encode()).hexdigest(), 16) & 0x7FFFFFFFFFFFFFFF,
                        vector=emb,
                        payload={
                            "path": c.path,
                            "symbol": c.symbol,
                            "content": c.content,
                            "start_line": c.start_line,
                            "end_line": c.end_line,
                            "content_hash": content_hash,
                            "source_type": "shader",
                            "indexed_at": time.time(),
                            "namespace": "",
                            "tags": c.tags,
                        },
                    )
                    for c, emb in zip(chunks, embeddings)
                ]
                await qdrant.upsert(collection_name=settings.qdrant_collection_code, points=points)
                shader_chunks += len(points)
            except Exception:
                logger.warning("Failed to index shader %s, skipping", shader_path)

        await qdrant.close()
        results["shader_chunks"] = shader_chunks
        results["shader_files"] = len(shader_paths)
        logger.info("Shader indexing complete: %d chunks from %d files", shader_chunks, len(shader_paths))
    except Exception as exc:
        logger.warning("Shader indexing failed (non-fatal): %s", exc)
        results["shader_chunks"] = 0
        results["shader_files"] = 0

    return results


# ── Conversation memory ──────────────────────────────────────────────


@dataclass
class ConversationEntry:
    """A single conversation turn for memory storage."""
    conversation_id: str
    turn_index: int
    role: str  # user, assistant
    content: str
    route: str  # code, scene, vision, etc.
    timestamp: float = field(default_factory=time.time)


async def store_conversation_turn(
    conversation_id: str,
    turn_index: int,
    role: str,
    content: str,
    route: str = "",
) -> int:
    """Store a conversation turn in the memory collection.

    Returns the point ID stored.
    """
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    await ensure_collection(qdrant, settings.qdrant_collection_memory)

    entry = ConversationEntry(
        conversation_id=conversation_id,
        turn_index=turn_index,
        role=role,
        content=content,
        route=route,
    )

    # Embed the content
    embedding = (await embed_texts([content]))[0]

    point_id = int(
        hashlib.md5(f"conv:{conversation_id}:{turn_index}:{role}".encode()).hexdigest(),
        16,
    ) & 0x7FFFFFFFFFFFFFFF

    point = PointStruct(
        id=point_id,
        vector=embedding,
        payload={
            "conversation_id": conversation_id,
            "turn_index": turn_index,
            "role": role,
            "content": content,
            "route": route,
            "timestamp": entry.timestamp,
            "source_type": "conversation",
        },
    )

    await qdrant.upsert(collection_name=settings.qdrant_collection_memory, points=[point])
    await qdrant.close()

    logger.debug("Stored conversation turn %s:%d (%s)", conversation_id, turn_index, role)
    return point_id


async def retrieve_conversation_context(
    query: str,
    conversation_id: str | None = None,
    max_turns: int = 10,
    include_other_convs: bool = False,
) -> str:
    """Retrieve relevant conversation context for a query.

    Args:
        query: The current user query
        conversation_id: Optional conversation ID to prioritize
        max_turns: Maximum number of turns to include
        include_other_convs: Whether to include turns from other conversations

    Returns:
        Formatted context string
    """
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    await ensure_collection(qdrant, settings.qdrant_collection_memory)

    # Embed query
    query_embedding = (await embed_texts([query]))[0]

    # Search for relevant conversation turns
    results = await qdrant.search(
        collection_name=settings.qdrant_collection_memory,
        query_vector=query_embedding,
        limit=max_turns * 2,  # Get extra to filter
        with_payload=True,
    )

    await qdrant.close()

    if not results:
        return ""

    # Filter and format
    relevant_turns = []
    for hit in results:
        payload = hit.payload
        # Prioritize same conversation
        if conversation_id and payload.get("conversation_id") != conversation_id:
            if not include_other_convs:
                continue
        relevant_turns.append({
            "conversation_id": payload.get("conversation_id", "unknown"),
            "turn_index": payload.get("turn_index", 0),
            "role": payload.get("role", "unknown"),
            "content": payload.get("content", ""),
            "route": payload.get("route", ""),
            "score": hit.score,
        })

    # Sort by conversation and turn index
    relevant_turns.sort(key=lambda x: (x["conversation_id"], x["turn_index"]))

    # Take last max_turns
    relevant_turns = relevant_turns[-max_turns:]

    if not relevant_turns:
        return ""

    # Format context
    parts = ["<conversation_history>"]
    for turn in relevant_turns:
        parts.append(f"[{turn['role']}] (route: {turn['route']}, score: {turn['score']:.3f})")
        parts.append(turn["content"])
        parts.append("---")
    parts.append("</conversation_history>")

    return "\n".join(parts)
