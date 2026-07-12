# syntax=docker/dockerfile:1.7
# ═══════════════════════════════════════════════
#  BUILD STAGE — compile dependencies
# ═══════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /app

# Build context is project root (./)
COPY server/packages/ /app/packages/
COPY server/scripts/ /app/scripts/

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Editable packages + runtime deps
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
        -e packages/kb-core \
        -e packages/kb-biz \
        -e packages/kb-adapter-postgres \
        -e packages/kb-adapter-rabbitmq \
    && pip install --no-cache-dir \
        fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
        pydantic pydantic-settings pyjwt passlib[bcrypt] python-multipart \
        redis python-json-logger httpx tenacity jieba email-validator \
        minio openpyxl aio-pika greenlet pymilvus 'bcrypt<4.1'

# Worker ML dependencies (document parsing + embedding)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
        python-docx python-pptx \
        sentence-transformers

# Purge GPU garbage — CPU inference only, no CUDA/triton needed.
# Separate RUN so COPY --from picks up the cleaned state (whiteout layer).
RUN rm -rf /usr/local/lib/python3.11/site-packages/nvidia \
           /usr/local/lib/python3.11/site-packages/triton \
           /usr/local/lib/python3.11/site-packages/cuda* \
           /usr/local/lib/python3.11/site-packages/torch/lib/libtorch_cuda* \
           /usr/local/lib/python3.11/site-packages/torch/include \
           /usr/local/lib/python3.11/site-packages/torch/bin \
           /usr/local/lib/python3.11/site-packages/torch/testing \
           /usr/local/lib/python3.11/site-packages/torch/distributed

# ═══════════════════════════════════════════════
#  RUNTIME STAGE — minimal production image
# ═══════════════════════════════════════════════
FROM python:3.11-slim

WORKDIR /app

# Python packages + binaries from builder (excludes build tools, pip cache, apt lists)
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Applications source code (packages installed editable)
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/scripts /app/scripts
COPY server/backend/ /app/

# Strip runtime-unnecessary bloat
RUN rm -rf /app/packages/kb-biz/.venv /app/packages/kb-core/.venv 2>/dev/null; \
    find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.11 -name '*.pyc' -delete 2>/dev/null; \
    pip uninstall -y pip setuptools 2>/dev/null; true

RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
