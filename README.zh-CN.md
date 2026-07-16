# 企业知识库智能问答

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python" alt="Python 3.11">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" alt="React 19">
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-Apache%202.0-red" alt="Apache 2.0">
</p>

企业文档散落在各个部门的共享文件夹里 — 合同、制度、技术文档、邮件附件。
想找份去年的方案，问了一圈人说"好像在 XXX 那里"；用文件名搜索根本找不到内容；
把文档塞给 ChatGPT？数据出域了怎么办？

**企业知识库智能问答** 是一个私有化部署的 RAG 问答系统。
把 PDF / Word / Excel / PPT / 邮件丢进去，用自然语言提问，
回答完全基于你的知识库，数据不出容器。

- **辛苦整理的知识没人用** → 混合检索（语义 + 关键词 + 重排）+ Cross-Encoder 精排，搜得准才答得准
- **AI 回答不敢信** → 严格模式拒绝幻觉，每句回答带原文引用溯源
- **数据不敢上公有云** → Docker 一键私有化部署，推理全部本地执行

[English](README.md) | **中文**

---

## 快速开始

```bash
git clone https://github.com/RanenLiu/enterprise-kb-agent.git
cd enterprise-kb-agent

# 配置 LLM API Key（至少一个）
cp server/.env.example server/.env
# 编辑 server/.env，设置 LLM_API_KEY（DeepSeek / OpenAI 等）

# 启动所有服务
docker compose up -d

# 访问 Web 界面
open http://localhost:5173
```

> Docker 方式下数据库、缓存等连接地址由 `docker-compose.yml` 自动配置，`.env` 只需填写 LLM API Key 等敏感信息即可。

默认管理员：`admin` / `admin123`

> **前提条件**：Docker & Docker Compose v2

---

## 功能

### 🔍 混合检索
| 通道 | 引擎 | 说明 |
|---------|--------|-------------|
| 向量 | Milvus (IVF_FLAT, COSINE) | BGE-M3 语义相似度检索 |
| 全文 | PostgreSQL tsvector + ILIKE | BM25 关键词匹配，支持中文分词 |
| 融合 | RRF | 互惠排名融合，合并多路结果 |
| BM25 重排 | jieba + BM25 | 中文关键词重排，防止 RRF 摊平精确匹配 |
| 精排 | Cross-Encoder | BGE-reranker-v2 精排，提升精度 |
| **HyDE** *(默认开启)* | LLM 生成假设答案 | 弥合问答措辞差异。代价：每次查询 +1 次 LLM 调用 (~3s) |
| **QueryFusion** *(可选)* | 多视角 LLM 扩展 | 多查询变体并行检索后 RRF 融合。代价：3-5x 检索延迟 |

### 💬 智能聊天
- LangGraph 状态机驱动的多轮对话
- 意图识别和确认（知识检索 / 闲聊 / 工具调用）
- 短期（Redis 滑动窗口）+ 长期记忆（PostgreSQL）
- SSE 流式输出
- 回答附引用来源（score ≥ 0.2 阈值，低分不显示）
- 严格模式：知识查询无结果时返回"未找到"，不依赖 LLM 自有知识
- 闲聊意图自动跳过知识库检索

### 📄 文档处理
| 格式 | 解析器 |
|--------|--------|
| PDF | PyMuPDF（结构感知、表格检测） |
| Office | Native 解析（DOCX/XLSX/PPTX） |
| 文本 | Native 解析（TXT/MD/CSV/MARKDOWN） |
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
| `DATABASE_URL` | `postgresql+asyncpg://kbuser:kbpass@localhost:5432/enterprise_kb` | PostgreSQL 连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 |
| `MILVUS_HOST` | `localhost` | Milvus 主机名 |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO S3 端点 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 嵌入模型 |
| `RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | 重排模型 |

> **模型部署说明**：嵌入模型和重排模型**未预先部署**，首次使用时系统自动从 HuggingFace Hub 下载到本地运行，推理过程**完全在本地执行**，文档数据不会离开容器。  
> - **国内用户**：推荐使用 ModelScope 镜像加速下载：  
>   - [BAAI/bge-m3](https://www.modelscope.cn/models/BAAI/bge-m3)  
>   - [BAAI/bge-reranker-v2-m3](https://www.modelscope.cn/models/BAAI/bge-reranker-v2-m3)  
> - **离线/隔离环境**：提前下载模型文件（通过 HF 或 ModelScope），挂载到 `/models` 目录，设置 `EMBEDDING_MODEL=/models/BAAI/bge-m3` 即可。  
> - **开发阶段**可使用收费 API 快速验证（如 DeepSeek、通义千问），**生产环境私有化部署**建议使用 Ollama / vLLM / Xinference 等本地推理框架部署大模型和嵌入模型，确保数据不出容器。  
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

如果你需要修改代码、热重载调试，采用混合模式：基础设施用 Docker 运行，后端和前端在本地启动。

依赖服务（PostgreSQL、Redis、MinIO、Milvus）需要提前启动，如需文档处理功能再加 RabbitMQ：

```bash
# 启动基础设施（PostgreSQL、Redis、MinIO、Milvus）
docker compose up -d postgres redis minio etcd milvus

# 如需文档处理（worker），增加 rabbitmq
# docker compose up -d postgres redis minio etcd milvus rabbitmq
```

首次搭建开发环境可用 `server/scripts/setup_dev.sh` 快速安装依赖和启动基础设施。
如需彻底重置环境（清空数据库并重建容器），可运行 `server/scripts/reset-env.sh`。

```bash
# 后端
cd server
python3 -m venv .venv && source .venv/bin/activate
cp .env.example .env  # 已配好 localhost，无需修改
pip install -r requirements.txt
pip install -e packages/kb-core -e packages/kb-biz -e packages/kb-adapter-postgres
python -m scripts.seed_os  # 首次初始化数据库
uvicorn backend.main:app --reload

# 前端
cd frontend && pnpm install && pnpm dev
```

开发完成后如需 Docker 部署，参考[快速开始](#快速开始)。

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
