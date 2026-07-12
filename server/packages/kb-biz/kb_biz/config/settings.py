from __future__ import annotations


from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Enterprise KB Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://kbuser:kbpass@localhost:5432/enterprise_kb"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    jwt_refresh_expire_days: int = 7

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "enterprise-kb"
    minio_secure: bool = False

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "kbpass123"

    # LLM
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Rate Limit
    rate_limit_per_minute: int = 60
    login_rate_limit_per_minute: int = 10
    login_max_failures: int = 5
    login_lock_minutes: int = 15

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "kbuser"
    rabbitmq_pass: str = "kbpass"
    rabbitmq_document_queue: str = "doc.processing"

    # RAG
    embedding_model: str = "/Users/xiangliu/models/BAAI/bge-m3"
    rag_worker_concurrency: int = 2
    rerank_model: str = "/Users/xiangliu/models/BAAI/bge-reranker-v2-m3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


settings = Settings()
