from __future__ import annotations

from fastapi import APIRouter

from kb_biz.schemas.common import Response

router = APIRouter()

FEATURES = [
    {
        "icon": "MessageSquare",
        "title": "智能问答",
        "desc": "基于 RAG 的精准问答，多路召回 + 精排，流式输出",
        "color": "linear-gradient(to right, #00000000, #a855f71a)",
        "iconColor": "text-violet-600",
        "perm": "chat.access",
    },
    {
        "icon": "BookOpen",
        "title": "知识库管理",
        "desc": "多格式文档上传、解析、分块、索引，支持 PDF/Word/PPT/Excel",
        "color": "linear-gradient(to right, #00000000, #06b6d41a)",
        "iconColor": "text-blue-600",
        "perm": "document.create",
    },
    {
        "icon": "Shield",
        "title": "权限管控",
        "desc": "RBAC 五级角色体系，部门字段级数据隔离",
        "color": "linear-gradient(to right, #00000000, #f43f5e1a)",
        "iconColor": "text-destructive",
        "perm": "system.config",
    },
    {
        "icon": "Database",
        "title": "多模型支持",
        "desc": "DeepSeek / OpenAI / Ollama vLLM 多 Provider 切换",
        "color": "linear-gradient(to right, #00000000, #14b8a61a)",
        "iconColor": "text-emerald-600",
        "perm": "llm_config.read",
    },
]


@router.get("/config/features")
async def get_homepage_features():
    return Response(data=FEATURES)
