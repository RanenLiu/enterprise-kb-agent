# 企业知识库智能问答

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python" alt="Python 3.11">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" alt="React 19">
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-Apache%202.0-red" alt="Apache 2.0">
</p>

基于 RAG（检索增强生成）的企业智能问答系统。上传文档，用自然语言提问，获得基于知识库的精准回答。

- **检索**：混合检索（向量 + 全文）+ Cross-Encoder 重排
- **聊天**：LangGraph 驱动的多轮对话，含意图识别
- **文档**：支持 PDF、Office、图片、邮件 — 自动解析索引
- **权限**：部门级 RBAC 访问控制
- **部署**：`docker compose` 一键启动

[English](README.md) | **中文**

---

## 快速开始

```bash
git clone https://github.com/RanenLiu/enterprise-kb-agent.git
cd enterprise-kb-agent

# 启动所有服务
docker compose up -d

# 访问 Web 界面
open http://localhost:5173
```

默认管理员：`admin` / `admin123`

> **前提条件**：Docker & Docker Compose v2

---

## 功能

### 🔍 混合检索
| 通道 | 引擎 | 说明 |
|---------|--------|-------------|
| 向量 | Milvus | BGE-M3 语义相似度检索 |
| 全文 | PostgreSQL tsvector | BM25 关键词匹配，支持中文分词 |
| 融合 | RRF | 互惠排名融合，合并多路结果 |
| 重排 | Cross-Encoder | BGE-reranker-v2 精排，提升精度 |

### 💬 智能聊天
- LangGraph 状态机驱动的多轮对话
- 意图分类（知识检索 / 闲聊 / 工具调用）
- 短期（Redis 滑动窗口）+ 长期记忆（PostgreSQL）
- SSE 流式输出，实时展示 token
- 回答附引用来源

### 📄 文档处理
| 格式 | 解析器 |
|--------|--------|
| PDF | PyMuPDF（结构感知、表格检测） |
| Office | LlamaIndex readers（DOCX/XLSX/PPTX） |
| 图片 | PaddleOCR（JPG/PNG/BMP/TIFF） |
| 文本 | Native 解析（TXT/MD/CSV） |
| 邮件 | .msg / .eml 解析 |

### 👥 权限控制
- 部门级数据隔离（Milvus 字段过滤）
- 4 种角色：`dept_admin` / `dept_editor` / `dept_viewer` / `admin`
- 文档可见性：`private` / `dept` / `public`

### 🎨 前端
- React 19 + TypeScript + shadcn/ui
- 深色/浅色主题 + 5 种强调色
- 流式聊天 UI，内联引用来源

---

## 架构

详见[架构深度解析](docs/ARCHITECTURE.zh-CN.md)了解详细设计。

**基础设施：**

```
docker-compose.yml
  postgres ── pgvector + tsvector
  redis    ── 缓存 + 会话
  minio    ── 文件存储 (S3)
  etcd     ── Milvus 元数据
  milvus   ── 向量数据库
  rabbitmq ── 消息队列
  backend  ── FastAPI 应用
  frontend ── React SPA
```

---

## 配置

关键环境变量（`.env`）：

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://kbuser:kbpass@postgres:5432/enterprise_kb` | PostgreSQL 连接 |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 连接 |
| `MILVUS_HOST` | `milvus` | Milvus 主机名 |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO S3 端点 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 嵌入模型 |
| `RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | 重排模型 |

> **模型部署说明**：嵌入模型和重排模型**未预先部署**，首次使用时系统自动从 HuggingFace Hub 下载到本地运行，推理过程**完全在本地执行**，文档数据不会离开容器。  
> - **国内用户**：推荐使用 ModelScope 镜像加速下载：  
>   - [BAAI/bge-m3](https://www.modelscope.cn/models/BAAI/bge-m3)  
>   - [BAAI/bge-reranker-v2-m3](https://www.modelscope.cn/models/BAAI/bge-reranker-v2-m3)  
> - **离线/隔离环境**：提前下载模型文件（通过 HF 或 ModelScope），挂载到 `/models` 目录，设置 `EMBEDDING_MODEL=/models/BAAI/bge-m3` 即可。  
> - **LLM（对话）API** 是独立配置项，数据安全考量请参考下方的 LLM 配置指南。

详细 LLM 配置请参考 [LLM 配置指南](docs/llm-config.zh-CN.md)。

---

## 资源配置

| 资源 | 上限 |
|----------|-------|
| 用户 | 30 |
| 部门 | 5 |
| 文档 | 150 |
| 单文件大小 | 50 MB |
| 总存储 | 5 GB |

---

## 开发

```bash
# 后端
cd server && pip install -e packages/kb-core -e packages/kb-biz -e packages/kb-adapter-postgres
uvicorn backend.main:app --reload

# 前端
cd frontend && pnpm install && pnpm dev
```

---

## 技术栈

| 层 | 选型 |
|-------|-----------|
| 后端 | Python 3.11, FastAPI |
| AI 框架 | LangGraph, LangChain |
| RAG | LlamaIndex, MinerU |
| 向量库 | Milvus 2.6 |
| 关系库 | PostgreSQL 16 (pgvector) |
| 缓存 | Redis 7 |
| 对象存储 | MinIO |
| 前端 | React 19, shadcn/ui, TypeScript |

---

## 版本对比

| 版本 | 说明 |
|---------|-------------|
| **开源版**（本仓库） | 核心 RAG + 聊天 + RBAC，Apache 2.0 |
| **企业版** | 开源版全功能 + 高级企业能力 |
| **信创版** | 企业版全功能 + 国产化适配 |

企业版和信创版持续开发中，提供差异化功能、专业支持和优先更新。商业授权请联系 [xiao_boy@sohu.com](mailto:xiao_boy@sohu.com)。

---

## FAQ

### 聊天响应慢（10 秒以上）？

默认的 DeepSeek 公共 API 平均响应 12-16 秒，建议切换为更快的 LLM：

| LLM | 响应时间 | 配置方式 |
|-----|:--------:|---------|
| DeepSeek（默认） | 12-16s | 无需配置 |
| 阿里云百炼 Qwen | 3-6s | 系统设置 → 模型配置 |
| 本地 GPU 部署 | 1-2s | 部署 vLLM/Ollama |

详细配置请参考 [LLM 配置指南](docs/llm-config.zh-CN.md)。

### 可以用本地 LLM 吗？

可以。系统支持任何兼容 OpenAI API 的模型（Ollama、vLLM、LM Studio 等），在系统设置 → 模型配置中配置即可。

### 最低服务器要求？

- **CPU**: 4 核
- **内存**: 8 GB（含 Milvus）
- **存储**: 50 GB+ SSD
- **系统**: Linux（推荐）、macOS、Windows（Docker Desktop）

单机即可支持中小团队使用。

---

## 许可

Apache 2.0 — 参见 [LICENSE](LICENSE)。

---

## 贡献

欢迎提交 Issue 或 Pull Request！
