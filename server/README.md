# 开源版后端

## 包结构

```
server/
├── backend/              # FastAPI 入口
│   ├── main.py           # 注册基础路由
│   ├── Dockerfile        # 构建镜像
│   └── docker-entrypoint.sh
└── packages/
    ├── kb-core/          # AI 引擎（LLM/RAG/解析/分块/索引）
    ├── kb-biz/           # 业务逻辑（API/模型/认证/RBAC）
    ├── kb-adapter-postgres/ # PostgreSQL
    └── kb-adapter-rabbitmq/ # RabbitMQ
```

## 本地开发

```bash
# 安装包
uv pip install -e packages/kb-core -e packages/kb-biz \
                -e packages/kb-adapter-postgres \
                -e server/backend

# 启动服务（需先启动 PostgreSQL、Redis）
uvicorn backend.main:app --reload --port 8000
```

## Docker 构建

```bash
# 修改代码后重建
docker compose build backend
docker compose up -d --force-recreate backend
```

## 清理数据

```bash
# 停止服务（保留数据）
docker compose down

# ⚠️ 清空所有数据（不可恢复）
rm -rf ./data/os/
docker compose up -d
```
