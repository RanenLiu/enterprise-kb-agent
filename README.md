# Enterprise Knowledge Base Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python" alt="Python 3.11">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" alt="React 19">
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-Apache%202.0-red" alt="Apache 2.0">
</p>

Company documents live in scattered shared folders — contracts, policies, technical docs, email attachments. You need that Q3 report from last year, but nobody remembers where it is. Windows search won't find what's *inside* the files. And uploading everything to ChatGPT? Not an option — your data can't leave the building.

**Enterprise Knowledge Base Agent** is a self-hosted RAG Q&A system. Drop in your PDFs, Word docs, spreadsheets, CSV files, and emails. Ask questions in plain language. Get answers grounded in your own knowledge base — no data ever leaves your infrastructure.

- **Knowledge goes unused** → Hybrid search (semantic + keyword + rerank) with Cross-Encoder precision, finds what you need even when you don't know the exact terms
- **Can't trust AI answers** → Strict mode blocks hallucinations, every answer cites its source documents
- **Can't use public cloud AI** → One-command Docker deployment, all inference runs locally

**English** | [中文](README.zh-CN.md)

---

## Quick Start

```bash
git clone https://github.com/RanenLiu/enterprise-kb-agent.git
cd enterprise-kb-agent

# Configure LLM API Key (at least one provider)
cp server/.env.example server/.env
# Edit server/.env, set LLM_API_KEY (DeepSeek / OpenAI, etc.)

# Start all services
docker compose up -d

# Access the web UI
open http://localhost:5173
```

> In Docker mode, database and cache connection URLs are pre-configured in `docker-compose.yml`. You only need to set your LLM API Key in `.env`.

Default admin account: `admin` / `admin123`

> **Prerequisites**: Docker & Docker Compose v2

---

## Features

### 🔍 Hybrid Search
| Channel | Engine | Description |
|---------|--------|-------------|
| Vector | Milvus (IVF_FLAT, COSINE) | Semantic similarity search with BGE-M3 embeddings |
| Fulltext | PostgreSQL tsvector + ILIKE | BM25-style keyword search with Chinese word segmentation |
| Fusion | RRF | Reciprocal Rank Fusion combines multi-channel results |
| BM25 Rescore | jieba + BM25 | Chinese keyword rescoring prevents RRF from flattening precision matches |
| Rerank | Cross-Encoder | BGE-reranker-v2 re-ranks top candidates for precision |
| **HyDE** *(default: on)* | LLM-generated hypothetical answer | Bridges query-document wording gaps. Cost: +1 LLM call (~3s) per query |
| **QueryFusion** *(optional)* | Multi-perspective LLM expansion | Generates query variants, searches all, RRF merges. Cost: 3-5x retrieval + fusion delay |

### 💬 Intelligent Chat
- Multi-turn conversation with LangGraph state machine
- Intent classification (knowledge query / general chat / tool use)
- Short-term context (Redis sliding window) + long-term memory (PostgreSQL)
- Streaming SSE responses with real-time token output
- Deep thinking mode with reasoning content display (typewriter effect)
- Source citation with relevance threshold (score ≥ 0.2)
- Strict mode: knowledge_query without results returns "not found", no LLM hallucination
- General chat intent skips knowledge base search entirely

### 📄 Document Processing
| Format | Parser |
|--------|--------|
| PDF | PyMuPDF (structure-aware, table detection) |
| Office | Native parsers (DOCX, XLSX, PPTX) |
| Text | Native parser (TXT, MD, CSV) |
| Email | Native .msg / .eml parser |

### 👥 Access Control
- Department-level data isolation via Milvus field filtering
- 4 roles: `dept_admin` / `dept_editor` / `dept_viewer` / `admin`
- Document visibility: `private` / `dept` / `public`

### 🎨 Frontend
- React 19 + TypeScript + shadcn/ui
- Dark/light theme with 5 accent colors + glass mode
- Streaming chat UI with inline citations and reasoning display
- File type filtering and keyword search in knowledge base
- Inline file preview (PDF, Office, images, markdown)

---

## Architecture

See [Architecture Deep Dive](docs/ARCHITECTURE.md) for a detailed design walkthrough.

**Services:**

```
docker-compose.yml
  postgres ── pgvector + tsvector
  redis    ── cache + session
  minio    ── file storage (S3)
  etcd     ── Milvus metadata
  milvus   ── vector database
  rabbitmq ── message queue
  backend  ── FastAPI application
  frontend ── React SPA
```

---

## Configuration

Key environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://kbuser:kbpass@localhost:5432/enterprise_kb` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `MILVUS_HOST` | `localhost` | Milvus hostname |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO S3 endpoint |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Embedding model (HF auto-download) |
| `RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | Reranker model |

> **Model deployment notes**: The embedding and reranker models are **not pre-deployed**. On first use, the system downloads them from HuggingFace Hub and runs inference **fully locally** — documents never leave the container.  
> - **Chinese users**: Use ModelScope for faster downloads:  
>   - [BAAI/bge-m3](https://www.modelscope.cn/models/BAAI/bge-m3)  
>   - [BAAI/bge-reranker-v2-m3](https://www.modelscope.cn/models/BAAI/bge-reranker-v2-m3)  
> - **Offline / air-gapped**: Pre-download models (via HF or ModelScope) and mount them to `/models`, then set `EMBEDDING_MODEL=/models/BAAI/bge-m3`.  
> - **Development**: paid APIs (DeepSeek, Qwen, etc.) are fine for prototyping. **For production private deployment**, use local inference frameworks like Ollama / vLLM / Xinference for both LLM and embedding models — data never leaves the container.  
> - **LLM (chat) APIs** are a separate concern — see the LLM config guide below for provider setup and data-security considerations.

See [LLM Configuration Guide](docs/llm-config.md) for provider-specific LLM setup.

---

## Resource Limits

| Resource | Limit |
|----------|-------|
| Users | 30 |
| Departments | 5 |
| Documents | 150 |
| File size | 50 MB |
| Total storage | 5 GB |

---

## Development

For local development with hot-reload, use a hybrid approach: infrastructure runs in Docker, backend and frontend run natively.

Dependencies (PostgreSQL, Redis, MinIO, Milvus) must be running first. RabbitMQ is needed for document processing (optional):

```bash
# Start infrastructure (PostgreSQL, Redis, MinIO, Milvus)
docker compose up -d postgres redis minio etcd milvus

# For document processing (worker), add rabbitmq
# docker compose up -d postgres redis minio etcd milvus rabbitmq
```

For first-time setup, `server/scripts/setup_dev.sh` installs dependencies and starts infrastructure services.
To reset the environment (wipe database and rebuild containers), run `server/scripts/reset-env.sh`.

```bash
# Backend
cd server
cp server/.env.example server/.env  # Already uses localhost, no changes needed
pip install -e packages/kb-core -e packages/kb-biz -e packages/kb-adapter-postgres
uvicorn backend.main:app --reload

# Frontend
cd frontend && pnpm install && pnpm dev
```

When you're ready to deploy with Docker, refer back to [Quick Start](#quick-start).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI |
| AI Framework | LangGraph, LangChain |
| RAG | LlamaIndex, MinerU |
| Vector DB | Milvus 2.6 |
| Relational DB | PostgreSQL 16 (pgvector) |
| Cache | Redis 7 |
| Object Storage | MinIO |
| Frontend | React 19, shadcn/ui, TypeScript |

---

## Editions

| Edition | Description |
|---------|-------------|
| **Open Source** (this repo) | Core RAG + chat + RBAC, Apache 2.0 |
| **Enterprise** | All OS features + advanced enterprise capabilities |
| **信创 (Xinchuang)** | Enterprise features adapted for domestic compliance |

Enterprise and 信创 editions include professional support and priority updates.  
For inquiries about licensing, custom deployment, or enterprise features:

> 📧 **Contact**: [xiao_boy@sohu.com](mailto:xiao_boy@sohu.com) — we'll follow up within 1-2 business days.

These editions are under active development. Feature requests and partnership discussions are welcome.

---

## FAQ

### Chat feels slow (takes 10+ seconds to respond)?

The default LLM (DeepSeek public API) can be slow, averaging 12-16s per response. For faster responses:

| LLM | Response Time | Setup |
|-----|:------------:|-------|
| DeepSeek (default) | 12-16s | Default, no setup needed |
| Qwen (阿里云百炼) | 3-6s | Change provider in UI |
| Local LLM (GPU) | 1-2s | Deploy with vLLM/Ollama |

See [LLM Configuration Guide](docs/llm-config.md) for provider-specific setup.

### Can I use a local LLM?

Yes. The system supports any OpenAI-compatible API (Ollama, vLLM, LM Studio, etc.). Configure it in Settings -> LLM Config, or through the API.

### What are the minimum server requirements?

- **CPU**: 4 cores
- **RAM**: 8 GB (for all services including Milvus)
- **Storage**: 50 GB+ SSD
- **OS**: Linux (recommended), macOS, Windows (Docker Desktop)

Runs comfortably on a single server for small to medium teams.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Contributing

Contributions are welcome! Please open an issue or pull request.
