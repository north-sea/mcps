#!/bin/bash
# NAS Deployment Script: hermes-db-v0.2.23
# Feature: hermes-db-batch-planning-api
# Date: 2026-06-16

set -euo pipefail

echo "======================================"
echo "部署 hermes-db-v0.2.23"
echo "Migration: 0008_novel_planning_tables"
echo "======================================"
echo ""

# 检查必要环境变量
if [ ! -f deploy/nas.local.env ]; then
    echo "❌ 错误：deploy/nas.local.env 不存在"
    exit 1
fi

# 设置版本
export TAG=v0.2.23

echo "📦 Step 1: 拉取新镜像..."
docker compose -f deploy/services/hermes-db.yml pull
echo "✅ 镜像拉取完成"
echo ""

echo "⚠️  Step 2: 执行 Migration（关键步骤）"
echo "即将执行: alembic upgrade head"
echo "将创建 6 个新表 + 扩展 2 个现有表 + 9 个索引"
read -p "确认继续？[y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 用户取消"
    exit 1
fi

echo "🔄 执行 Migration..."
docker compose -f deploy/services/hermes-db.yml run --rm --entrypoint alembic hermes-db-mcp upgrade head

if [ $? -ne 0 ]; then
    echo "❌ Migration 失败！"
    echo "请检查日志并手动处理"
    exit 1
fi
echo "✅ Migration 执行成功"
echo ""

echo "🚀 Step 3: 重启服务..."
docker compose -f deploy/services/hermes-db.yml up -d hermes-db-mcp
echo "✅ 服务已重启"
echo ""

echo "⏳ 等待服务启动（10 秒）..."
sleep 10

echo "🔍 Step 4: 验证部署..."
echo ""
echo "请手动执行以下验证："
echo ""
echo "1. 检查容器状态："
echo "   docker ps | grep hermes-db-mcp"
echo ""
echo "2. 检查日志（无错误）："
echo "   docker logs hermes-db-mcp --tail 50"
echo ""
echo "3. 调用 health() 工具（通过 MCP client）："
echo "   期望返回："
echo "   {\"schema_revision\": \"0008_novel_planning_tables\", ...}"
echo ""
echo "4. 检查 tools/list 包含新工具："
echo "   - batch_create_book_planning"
echo "   - get_chapter_input_pack"
echo "   - update_context_version"
echo "   - get_current_context_version"
echo ""
echo "======================================"
echo "✅ 部署脚本执行完成"
echo "======================================"
echo ""
echo "⚠️  后续待办："
echo "1. 通知 agents 仓库团队（bookId→bookSlug 接口变更）"
echo "2. 执行集成测试（可选）"
echo "3. 监控服务运行状态"
