"""Centralized configuration loaded from environment variables.

Supports two modes:
- LOCAL mode: RunPod services locally (vLLM, Qdrant, etc.) + MCP-Unity via ws://localhost
- POD mode: RunPod services on remote pod + MCP-Unity via cloudflared tunnel
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ── Mode ──
    run_mode: str = Field(default="local", alias="RUN_MODE")  # "local" or "pod"

    # ── API ──
    api_secret_key: str = Field(default="dev-key", alias="API_SECRET_KEY")
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    # ── MCP-Unity ──
    # Local: ws://localhost:8090/McpUnity (Unity Editor on same machine)
    # Pod: wss://xxx.trycloudflare.com/McpUnity (via cloudflared tunnel)
    mcp_unity_ws_url: str = Field(
        default="ws://localhost:8090/McpUnity",
        alias="MCP_UNITY_WS_URL",
    )
    mcp_unity_timeout: int = 30

    # ── vLLM endpoints ──
    # Local: http://localhost:8000/v1
    # Pod: https://PODID-8000.proxy.runpod.net/v1
    vllm_llm_url: str = Field(default="http://localhost:8000/v1", alias="VLLM_LLM_URL")
    vllm_vision_url: str = Field(default="http://localhost:8001/v1", alias="VLLM_VISION_URL")
    vllm_llm_model: str = "Qwen2.5-Coder-32B-Instruct-AWQ"
    vllm_vision_model: str = "Qwen2-VL-7B-Instruct"

    # ── Embedding / Reranker ──
    # Local: http://localhost:8002
    # Pod: https://PODID-8002.proxy.runpod.net
    embedding_url: str = Field(default="http://localhost:8002", alias="EMBEDDING_URL")
    reranker_url: str = Field(default="http://localhost:8003", alias="RERANKER_URL")

    # ── Qdrant ──
    # Local: http://localhost:6333
    # Pod: https://PODID-6333.proxy.runpod.net
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection_code: str = "project_code"
    qdrant_collection_docs: str = "unity_docs"
    qdrant_collection_patterns: str = "unity_patterns"
    qdrant_collection_memory: str = "conversation_memory"
    embedding_dim: int = 1024  # BGE-M3

    # ── RAG tuning ──
    rag_top_k: int = 20
    rag_rerank_top_k: int = 5
    rag_chunk_max_tokens: int = 512

    # ── Pod connection ──
    pod_id: str = Field(default="", alias="POD_ID")
    pod_proxy_base: str = "https://{pod_id}-{port}.proxy.runpod.net"

    @property
    def is_local(self) -> bool:
        """Check if running in local mode."""
        return self.run_mode == "local"

    @property
    def is_pod(self) -> bool:
        """Check if running in pod mode."""
        return self.run_mode == "pod"

    def get_pod_url(self, port: int) -> str:
        """Get the proxy URL for a given pod port."""
        if not self.pod_id:
            raise ValueError("POD_ID must be set for pod mode")
        return self.pod_proxy_base.format(pod_id=self.pod_id, port=port)


settings = Settings()  # type: ignore[call-arg]
