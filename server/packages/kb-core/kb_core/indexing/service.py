from __future__ import annotations

import logging

from kb_core.config import settings
from kb_core.llm.client import LLMClient

logger = logging.getLogger("kb_core.indexing")

# ── Embedding ──

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        import time
        t0 = time.time()
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model %s ...", settings.embedding_model)
        _embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded in %.1fs", time.time() - t0)
    return _embedding_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量生成文本向量."""
    model = _get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def embed_chunks(chunks: list[dict]) -> list[list[float]]:
    """为 chunk 列表生成向量，提取 content 字段批量编码."""
    texts = [c["content"] for c in chunks]
    return embed_texts(texts)


# ── Milvus ──

_milvus_collection = None


def get_milvus_collection(dim: int = 1024):
    global _milvus_collection
    if _milvus_collection is not None:
        return _milvus_collection

    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

    connections.connect(
        alias="default",
        host=settings.milvus_host,
        port=settings.milvus_port,
        timeout=5,  # 5 秒连接超时
    )

    collection_name = "document_chunks"

    # 如果 collection 存在但 schema 旧了，删掉重建
    if utility.has_collection(collection_name):
        _milvus_collection = Collection(collection_name)
        existing_fields = [f.name for f in _milvus_collection.schema.fields]
        existing_dim = None
        for f in _milvus_collection.schema.fields:
            if f.name == "embedding":
                existing_dim = f.params.get("dim")
                break
        existing_content_len = None
        for f in _milvus_collection.schema.fields:
            if f.name == "content":
                existing_content_len = f.params.get("max_length")
                break
        if existing_dim != dim or existing_content_len != 65535:
            _milvus_collection.release()
            utility.drop_collection(collection_name)
            logger.info(
                "Dropped old Milvus collection for schema upgrade (dim=%s, had_dim=%s)",
                dim,
                existing_dim,
            )

    if not utility.has_collection(collection_name):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="dept_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="visibility", dtype=DataType.VARCHAR, max_length=20),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="heading_path", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="page_range", dtype=DataType.VARCHAR, max_length=20),
            FieldSchema(name="project_id", dtype=DataType.VARCHAR, max_length=64, default_value=""),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields, description="Document chunk embeddings")
        _milvus_collection = Collection(collection_name, schema)
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        _milvus_collection.create_index("embedding", index_params)
    else:
        _milvus_collection = Collection(collection_name)

    _milvus_collection.load()
    return _milvus_collection


def ensure_tenant_partition(tenant_code: str) -> str:
    """Create or verify a Milvus partition for a tenant. Returns partition name."""
    from pymilvus import Collection
    partition_name = f"tenant_{tenant_code}"
    collection = get_milvus_collection()
    existing = [p.name for p in collection.partitions]
    if partition_name not in existing:
        collection.create_partition(partition_name)
    return partition_name


def index_to_milvus(
    doc_id: str, dept_id: str, visibility: str, chunks: list[dict], embeddings: list[list[float]],
    project_id: str = "", partition_name: str = "",
) -> list[str]:
    """写入 Milvus，返回 milvus_id 列表."""
    collection = get_milvus_collection()

    entities = [
        [doc_id] * len(chunks),
        [dept_id] * len(chunks),
        [visibility] * len(chunks),
        [c["chunk_index"] for c in chunks],
        [c["content"][:65535] for c in chunks],
        [c.get("heading_path", "")[:512] for c in chunks],
        [c.get("page_range", "")[:20] for c in chunks],
        [project_id] * len(chunks),
        embeddings,
    ]
    insert_kwargs = {"data": entities}
    if partition_name:
        insert_kwargs["partition_name"] = partition_name
    insert_result = collection.insert(**insert_kwargs)
    collection.flush()
    return [str(uid) for uid in insert_result.primary_keys]


def delete_milvus_vectors(doc_id: str) -> None:
    """按 doc_id 删除 Milvus 中的向量."""
    collection = get_milvus_collection()
    if collection.num_entities > 0:
        collection.delete(f'doc_id == "{doc_id}"')
        collection.flush()


# ── LLM 增强 ──


async def generate_summary(chunk_text: str, llm_client: LLMClient | None = None) -> str:
    """生成 chunk 摘要."""
    if llm_client is None:
        llm_client = LLMClient()
    system_prompt = "你是一个文档摘要助手。用不超过 300 字概括以下内容的核心信息。"
    try:
        return await llm_client.chat(
            prompt=f"请摘要以下内容:\n\n{chunk_text[:2000]}",
            system_prompt=system_prompt,
        )
    except Exception as e:
        logger.warning("Summary generation failed: %s", e)
        return ""


async def generate_hypothetical_questions(chunk_text: str, llm_client: LLMClient | None = None) -> list[str]:
    """为 chunk 生成假设问题 (HQG)."""
    if llm_client is None:
        llm_client = LLMClient()
    system_prompt = (
        "你是一个检索优化助手。基于以下内容生成 3-5 个假设问题，"
        "用户可能通过这些问题检索到这段内容。"
        "输出 JSON 字符串数组，如 [\"问题1\", \"问题2\", ...]。"
    )
    try:
        result = await llm_client.chat_json(
            prompt=f"内容:\n\n{chunk_text[:2000]}",
            system_prompt=system_prompt,
        )
        if isinstance(result, list):
            return [str(q) for q in result]
        return []
    except Exception as e:
        logger.warning("HQG generation failed: %s", e)
        return []


async def extract_triples(full_text: str, llm_client: LLMClient | None = None) -> list[dict]:
    """使用 LLM 从文本中抽取实体-关系三元组."""
    if llm_client is None:
        llm_client = LLMClient()
    system_prompt = (
        "你是一个知识图谱抽取专家。从文本中提取实体和关系，"
        "输出 JSON 格式: "
        '[{"subject": "实体1", "relation": "关系", "object": "实体2"}, ...]。'
        "规则："
        "1. 实体名称用中文，同一概念必须使用完全相同的名称；"
        "2. 关系用简短动词（如\"包含\"、\"属于\"、\"要求\"、\"采用\"、\"存储\"），不要带标点；"
        "3. 尽量连接实体形成网络，让不同段落提取的实体能够通过关系关联起来；"
        "4. 如果实体 A 包含实体 B，B 又包含 C，请同时抽取 A--包含-->B 和 B--包含-->C；"
        "5. 优先复用已有实体名，不要创造同义词。"
        "只输出 JSON 数组，不要其他内容。"
    )
    try:
        result = await llm_client.chat_json(
            prompt=f"从以下文本中抽取实体-关系三元组:\n\n{full_text[:8000]}",
            system_prompt=system_prompt,
        )
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "triples" in result:
            return result["triples"]
        return []
    except Exception as e:
        logger.warning("Triple extraction failed: %s", e)
        return []


class IndexingService:
    """索引编排服务的可注入包装.

    编排解析→分块→embedding→写入 Milvus 的完整流程。
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self._llm_client = llm_client or LLMClient()

    async def index_document(
        self,
        doc_id: str,
        dept_id: str,
        visibility: str,
        chunks: list[dict],
        project_id: str = "",
    ) -> list[str]:
        """对已分块的文档生成 embedding 并写入 Milvus."""
        embeddings = embed_chunks(chunks)
        return index_to_milvus(doc_id, dept_id, visibility, chunks, embeddings, project_id=project_id)

    async def generate_summary(self, chunk_text: str) -> str:
        return await generate_summary(chunk_text, llm_client=self._llm_client)

    async def generate_hypothetical_questions(self, chunk_text: str) -> list[str]:
        return await generate_hypothetical_questions(chunk_text, llm_client=self._llm_client)
