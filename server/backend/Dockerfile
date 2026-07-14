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
# CPU-only torch to avoid downloading 1GB+ of NVIDIA GPU libraries
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
        torch --index-url https://download.pytorch.org/whl/cpu
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
        python-docx python-pptx \
        sentence-transformers

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
