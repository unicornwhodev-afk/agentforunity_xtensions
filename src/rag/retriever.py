"""RAG retriever — query Qdrant, rerank, build context for the LLM.

Features:
- Metadata filtering: source_type, path_prefix, namespace
- Conversation memory integration
- Hybrid search with fallback
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

from src.config import settings
from src.rag.indexer import embed_texts, retrieve_conversation_context

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    path: str
    symbol: str
    content: str
    start_line: int
    end_line: int
    score: float
    source_type: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class RetrievalFilters:
    """Filters for targeted retrieval."""
    source_types: list[str] | None = None  # e.g. ["code", "shader", "kb"]
    path_prefix: str | None = None  # e.g. "Assets/Scripts/Weapons/"
    namespace: str | None = None  # e.g. "WeaponSystem"
    min_score: float | None = None  # Minimum relevance score


# ── reranker ─────────────────────────────────────────────────────────


async def rerank(query: str, documents: list[str]) -> list[float]:
    """Call the local reranker server (BGE-Reranker-v2-M3)."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.reranker_url}/rerank",
            json={"query": query, "documents": documents},
        )
        resp.raise_for_status()
        return resp.json()["scores"]


# ── search pipeline ─────────────────────────────────────────────────


async def retrieve(
    query: str,
    collection: str | None = None,
    top_k: int | None = None,
    rerank_top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Full RAG retrieval: embed → vector search → rerank → return top chunks.

    If no collection is specified, searches both code and KB docs collections.
    """
    top_k = top_k or settings.rag_top_k
    rerank_top_k = rerank_top_k or settings.rag_rerank_top_k

    # 1. embed query
    query_embedding = (await embed_texts([query]))[0]

    # 2. vector search across collections
    collections = [collection] if collection else [settings.qdrant_collection_code, settings.qdrant_collection_docs]
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)

    all_results = []
    for coll in collections:
        try:
            results = await qdrant.search(
                collection_name=coll,
                query_vector=query_embedding,
                limit=top_k,
                with_payload=True,
            )
            all_results.extend(results)
        except Exception:
            logger.debug("Collection %s not available, skipping", coll)

    await qdrant.close()

    if not all_results:
        return []

    # 3. rerank
    documents = [hit.payload["content"] for hit in all_results]
    try:
        scores = await rerank(query, documents)
    except Exception:
        logger.warning("Reranker unavailable, using vector scores only")
        scores = [hit.score for hit in all_results]

    # 4. sort by reranker score and take top-k
    ranked = sorted(zip(all_results, scores), key=lambda x: x[1], reverse=True)
    ranked = ranked[:rerank_top_k]

    return [
        RetrievedChunk(
            path=hit.payload.get("path", "unknown"),
            symbol=hit.payload.get("symbol", "unknown"),
            content=hit.payload.get("content", ""),
            start_line=hit.payload.get("start_line", 0),
            end_line=hit.payload.get("end_line", 0),
            score=score,
        )
        for hit, score in ranked
    ]


async def retrieve_with_filters(
    query: str,
    filters: RetrievalFilters | None = None,
    collection: str | None = None,
    top_k: int | None = None,
    rerank_top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Full RAG retrieval with metadata filtering.

    Supports filtering by source_type, path_prefix, namespace, and min_score.
    """
    top_k = top_k or settings.rag_top_k
    rerank_top_k = rerank_top_k or settings.rag_rerank_top_k

    # 1. embed query
    query_embedding = (await embed_texts([query]))[0]

    # 2. build Qdrant filter
    qdrant_filter = None
    if filters:
        conditions = []

        if filters.source_types:
            # Match any of the source types
            for st in filters.source_types:
                conditions.append(FieldCondition(key="source_type", match=MatchValue(value=st)))

        if filters.path_prefix:
            conditions.append(
                FieldCondition(
                    key="path",
                    match={"text": filters.path_prefix},
                )
            )

        if filters.namespace:
            conditions.append(
                FieldCondition(key="namespace", match=MatchValue(value=filters.namespace))
            )

        if conditions:
            qdrant_filter = Filter(must=conditions)

    # 3. vector search across collections
    collections = [collection] if collection else [settings.qdrant_collection_code, settings.qdrant_collection_docs]
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)

    all_results = []
    for coll in collections:
        try:
            results = await qdrant.search(
                collection_name=coll,
                query_vector=query_embedding,
                limit=top_k,
                with_payload=True,
                query_filter=qdrant_filter,
            )
            all_results.extend(results)
        except Exception as exc:
            logger.debug("Collection %s search failed: %s", coll, exc)

    await qdrant.close()

    if not all_results:
        return []

    # 4. rerank
    documents = [hit.payload.get("content", "") for hit in all_results]
    try:
        scores = await rerank(query, documents)
    except Exception:
        logger.warning("Reranker unavailable, using vector scores only")
        scores = [hit.score for hit in all_results]

    # 5. sort by reranker score and take top-k
    ranked = sorted(zip(all_results, scores), key=lambda x: x[1], reverse=True)

    # Apply min_score filter after reranking
    if filters and filters.min_score is not None:
        ranked = [(hit, score) for hit, score in ranked if score >= filters.min_score]

    ranked = ranked[:rerank_top_k]

    return [
        RetrievedChunk(
            path=hit.payload.get("path", "unknown"),
            symbol=hit.payload.get("symbol", "unknown"),
            content=hit.payload.get("content", ""),
            start_line=hit.payload.get("start_line", 0),
            end_line=hit.payload.get("end_line", 0),
            score=score,
            source_type=hit.payload.get("source_type", ""),
            tags=hit.payload.get("tags", []),
        )
        for hit, score in ranked
    ]


async def retrieve_with_memory(
    query: str,
    conversation_id: str | None = None,
    filters: RetrievalFilters | None = None,
    top_k: int | None = None,
    rerank_top_k: int | None = None,
    include_conversation: bool = True,
) -> str:
    """Full retrieval combining RAG context + conversation memory.

    Returns a formatted context string ready for the LLM prompt.
    """
    # 1. Get RAG context
    rag_chunks = await retrieve_with_filters(
        query=query,
        filters=filters,
        top_k=top_k,
        rerank_top_k=rerank_top_k,
    )
    rag_context = build_context(rag_chunks)

    # 2. Get conversation memory context
    conv_context = ""
    if include_conversation:
        try:
            conv_context = await retrieve_conversation_context(
                query=query,
                conversation_id=conversation_id,
                max_turns=10,
                include_other_convs=False,
            )
        except Exception as exc:
            logger.warning("Conversation memory retrieval failed: %s", exc)

    # 3. Combine contexts
    parts = []
    if rag_context:
        parts.append(rag_context)
    if conv_context:
        parts.append(conv_context)

    return "\n\n".join(parts)


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a context block for the LLM prompt."""
    if not chunks:
        return ""
    parts = ["<retrieved_context>"]
    for c in chunks:
        parts.append(f"// {c.path} ({c.symbol}) L{c.start_line}-{c.end_line} [score={c.score:.3f}]")
        parts.append(c.content)
        parts.append("---")
    parts.append("</retrieved_context>")
    return "\n".join(parts)
