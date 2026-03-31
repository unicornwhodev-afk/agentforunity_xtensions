"""Lightweight reranker server for BGE-Reranker-v2-M3, served on port 8003."""

import logging
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from FlagEmbedding import FlagReranker
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = "/workspace/models/bge-reranker-v2-m3"

app = FastAPI(title="BGE Reranker")
reranker: FlagReranker | None = None


class RerankRequest(BaseModel):
    query: str
    documents: list[str]


class RerankResponse(BaseModel):
    scores: list[float]


@app.on_event("startup")
async def load_model():
    global reranker
    logger.info("Loading BGE-Reranker-v2-M3 from %s ...", MODEL_PATH)
    reranker = FlagReranker(
        MODEL_PATH,
        use_fp16=True if torch.cuda.is_available() else False,
    )
    logger.info("Reranker loaded")


@app.post("/rerank", response_model=RerankResponse)
async def rerank_endpoint(req: RerankRequest) -> RerankResponse:
    pairs = [[req.query, doc] for doc in req.documents]
    scores = reranker.compute_score(pairs, normalize=True)
    if isinstance(scores, float):
        scores = [scores]
    elif hasattr(scores, "tolist"):
        scores = scores.tolist()
    elif not isinstance(scores, list):
        scores = list(scores)
    return RerankResponse(scores=scores)


@app.get("/health")
async def health():
    return {"status": "ok", "model": "bge-reranker-v2-m3"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
