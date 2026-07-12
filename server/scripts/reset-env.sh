#!/bin/bash
# 完全重置开发环境（清空所有数据 + 重建容器）
set -e

echo "=== 1/5 清空数据库 ==="
docker compose exec -T postgres psql -U kbuser -d postgres -c "DROP DATABASE IF EXISTS enterprise_kb WITH (FORCE)"
docker compose exec -T postgres psql -U kbuser -d postgres -c "CREATE DATABASE enterprise_kb"

echo "=== 2/5 清空 Redis 缓存 ==="
docker compose exec -T redis redis-cli FLUSHALL

echo "=== 3/5 停止旧容器 ==="
docker compose down

echo "=== 4/5 重新构建镜像 ==="
docker compose build backend frontend

echo "=== 5/5 启动全部服务（会自动建表 + 种子数据） ==="
docker compose up -d --force-recreate

echo ""
echo "完成！后端启动后会自动执行："
echo "  - alembic upgrade head（建表）"
echo "  - seed_data.py（admin/admin123 超级管理员 + 角色 + 菜单）"
echo "查看启动状态: docker compose logs backend --tail 20"
