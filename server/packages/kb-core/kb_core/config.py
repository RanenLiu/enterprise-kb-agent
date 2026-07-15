from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """kb-core infrastructure settings (no dependency on app.* or kb_biz.*)."""

    # LLM
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # RAG
    embedding_model: str = "BAAI/bge-m3"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    use_hyde: bool = True
    use_query_fusion: bool = False
    use_step_decomp: bool = False

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "enterprise-kb"
    minio_secure: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
