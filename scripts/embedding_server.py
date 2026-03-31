"""Lightweight embedding server for BGE-M3, served on port 8002."""

import logging
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = "/workspace/models/bge-m3"

app = FastAPI(title="BGE-M3 Embeddings")
model: SentenceTransformer | None = None


class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


class OpenAIEmbeddingRequest(BaseModel):
    input: str | list[str]
    model: str = "bge-m3"


class OpenAIEmbeddingItem(BaseModel):
    object: str = "embedding"
    index: int
    embedding: list[float]


class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    total_tokens: int = 0


class OpenAIEmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[OpenAIEmbeddingItem]
    model: str
    usage: OpenAIUsage


def _encode(texts: list[str]) -> list[list[float]]:
    if model is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


@app.on_event("startup")
async def load_model():
    global model
    logger.info("Loading BGE-M3 from %s ...", MODEL_PATH)
    model = SentenceTransformer(MODEL_PATH, device="cuda" if torch.cuda.is_available() else "cpu")
    logger.info("BGE-M3 loaded (dim=%d)", model.get_sentence_embedding_dimension())


@app.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest) -> EmbedResponse:
    MAX_BATCH = 32
    texts = req.texts[:MAX_BATCH]
    return EmbedResponse(embeddings=_encode(texts))


@app.post("/v1/embeddings", response_model=OpenAIEmbeddingResponse)
async def openai_embeddings(req: OpenAIEmbeddingRequest) -> OpenAIEmbeddingResponse:
    MAX_BATCH = 32
    inputs = [req.input] if isinstance(req.input, str) else req.input
    texts = inputs[:MAX_BATCH]
    embeddings = _encode(texts)
    data = [OpenAIEmbeddingItem(index=i, embedding=emb) for i, emb in enumerate(embeddings)]
    token_count = sum(len(text.split()) for text in texts)
    return OpenAIEmbeddingResponse(
        data=data,
        model=req.model,
        usage=OpenAIUsage(prompt_tokens=token_count, total_tokens=token_count),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "model": "bge-m3"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
