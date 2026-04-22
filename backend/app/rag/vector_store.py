"""向量存储抽象层

支持多后端：
- Qdrant (推荐，生产首选)
- Chroma (兼容旧数据)

设计目标：
1. 统一接口，便于切换后端
2. 强制 metadata 过滤（防跨任务/跨域污染）
3. 真实 embedding（OpenAI 兼容 API）+ hash embedding 兜底
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings


# ---------------------- 数据结构 ----------------------

@dataclass
class VectorRecord:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class SearchHit:
    id: str
    text: str
    metadata: dict[str, Any]
    score: float  # 越大越相似 (0-1)


# ---------------------- Embedding ----------------------

def _tokenize(text: str) -> list[str]:
    value = str(text or "").lower()
    tokens: list[str] = re.findall(r"[a-z0-9_]+", value)
    cjk = re.findall(r"[\u4e00-\u9fff]+", value)
    for seq in cjk:
        tokens.extend(seq)
        tokens.extend(seq[i:i + 2] for i in range(len(seq) - 1))
    return [t for t in tokens if t]


def hash_embedding(text: str, *, dim: int) -> list[float]:
    """伪 embedding，仅在真实 embedding 服务不可用时兜底使用。"""
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * dim
    vec = [0.0] * dim
    for token in tokens:
        h = hashlib.sha1(token.encode("utf-8")).hexdigest()
        idx = int(h[:8], 16) % dim
        sign = 1.0 if int(h[8:10], 16) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 1e-12:
        return vec
    return [x / norm for x in vec]


class EmbeddingService:
    """OpenAI 兼容 API 的 embedding 服务，自带批处理与失败兜底。"""

    def __init__(self) -> None:
        self.model: str = (settings.EMBEDDING_MODEL or "").strip()
        self.dim: int = int(settings.EMBEDDING_DIM or 1536)
        self.batch_size: int = max(1, int(settings.EMBEDDING_BATCH_SIZE or 32))
        api_key = (settings.EMBEDDING_API_KEY or settings.LLM_API_KEY or "").strip()
        base_url = (settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL or "").strip()
        self._client: AsyncOpenAI | None = None
        if self.model and api_key:
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url.rstrip("/") if base_url else None,
            )
            logger.info("EmbeddingService 初始化: model={} dim={}", self.model, self.dim)
        else:
            logger.warning(
                "EmbeddingService 未配置真实 embedding 模型，将退化为 hash embedding（仅供原型）。"
                "请在 .env 中设置 EMBEDDING_MODEL（推荐 text-embedding-3-small）。"
            )

    @property
    def is_real(self) -> bool:
        return self._client is not None and bool(self.model)

    async def embed_one(self, text: str) -> list[float]:
        if not self.is_real:
            return hash_embedding(text, dim=self.dim)
        try:
            assert self._client is not None
            resp = await self._client.embeddings.create(model=self.model, input=text)
            vec = list(resp.data[0].embedding)
            return vec
        except Exception as exc:
            logger.warning("Embedding API 调用失败，降级 hash: {}", exc)
            return hash_embedding(text, dim=self.dim)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.is_real:
            return [hash_embedding(t, dim=self.dim) for t in texts]
        results: list[list[float]] = []
        assert self._client is not None
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            try:
                resp = await self._client.embeddings.create(model=self.model, input=batch)
                results.extend(list(d.embedding) for d in resp.data)
            except Exception as exc:
                logger.warning("Embedding 批量调用失败，本批降级 hash: {}", exc)
                results.extend(hash_embedding(t, dim=self.dim) for t in batch)
        return results


# ---------------------- 抽象接口 ----------------------

class VectorStore(ABC):
    """向量存储后端接口。所有后端必须支持 metadata 过滤以防跨域污染。"""

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    def search(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        must_filters: dict[str, Any] | None = None,
        must_not_filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]: ...

    @abstractmethod
    def delete_by_filter(self, filters: dict[str, Any]) -> int: ...

    @abstractmethod
    def count(self) -> int: ...


# ---------------------- Qdrant 后端 ----------------------

class QdrantVectorStore(VectorStore):
    def __init__(self, *, dim: int) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels

        self._qmodels = qmodels
        self.dim = dim
        self.collection = settings.QDRANT_COLLECTION

        url = (settings.QDRANT_URL or "").strip()
        if url:
            self.client = QdrantClient(url=url, api_key=settings.QDRANT_API_KEY or None)
            logger.info("Qdrant 客户端: 远程模式 url={}", url)
        else:
            db_path = Path(settings.QDRANT_PATH)
            if not db_path.is_absolute():
                db_path = Path(__file__).resolve().parents[2] / settings.QDRANT_PATH
            db_path.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(db_path))
            logger.info("Qdrant 客户端: 嵌入式模式 path={}", db_path)

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection not in existing:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=self._qmodels.VectorParams(
                    size=self.dim,
                    distance=self._qmodels.Distance.COSINE,
                ),
            )
            logger.info("Qdrant 集合 {} 已创建 (dim={})", self.collection, self.dim)
            # 关键 payload 字段建索引，加速过滤
            for field_name, schema in [
                ("task_id", self._qmodels.PayloadSchemaType.KEYWORD),
                ("entry_type", self._qmodels.PayloadSchemaType.KEYWORD),
                ("source_type", self._qmodels.PayloadSchemaType.KEYWORD),
            ]:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection,
                        field_name=field_name,
                        field_schema=schema,
                    )
                except Exception:
                    pass

    @staticmethod
    def _to_uuid(text_id: str) -> str:
        # Qdrant point id 必须是 unsigned int 或 UUID。把任意字符串映射成 UUIDv5。
        return str(uuid.uuid5(uuid.NAMESPACE_URL, text_id))

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        points = []
        for r in records:
            if r.embedding is None:
                raise ValueError(f"VectorRecord {r.id} 缺少 embedding")
            payload = dict(r.metadata or {})
            payload["_text"] = r.text
            payload["_external_id"] = r.id
            points.append(
                self._qmodels.PointStruct(
                    id=self._to_uuid(r.id),
                    vector=r.embedding,
                    payload=payload,
                )
            )
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def _build_filter(
        self,
        *,
        must: dict[str, Any] | None,
        must_not: dict[str, Any] | None,
    ):
        Filter = self._qmodels.Filter
        FieldCondition = self._qmodels.FieldCondition
        MatchValue = self._qmodels.MatchValue
        MatchAny = self._qmodels.MatchAny

        def to_conditions(d: dict[str, Any] | None) -> list:
            conds = []
            for key, value in (d or {}).items():
                if isinstance(value, (list, tuple, set)):
                    conds.append(FieldCondition(key=key, match=MatchAny(any=list(value))))
                else:
                    conds.append(FieldCondition(key=key, match=MatchValue(value=value)))
            return conds

        m = to_conditions(must)
        mn = to_conditions(must_not)
        if not m and not mn:
            return None
        return Filter(must=m or None, must_not=mn or None)

    def search(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        must_filters: dict[str, Any] | None = None,
        must_not_filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        flt = self._build_filter(must=must_filters, must_not=must_not_filters)
        try:
            res = self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                limit=max(1, top_k),
                score_threshold=score_threshold if score_threshold > 0 else None,
                query_filter=flt,
                with_payload=True,
            )
            points = res.points
        except Exception:
            # 兼容旧版客户端
            points = self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=max(1, top_k),
                score_threshold=score_threshold if score_threshold > 0 else None,
                query_filter=flt,
                with_payload=True,
            )

        hits: list[SearchHit] = []
        for p in points:
            payload = dict(p.payload or {})
            text = str(payload.pop("_text", "") or "")
            ext_id = str(payload.pop("_external_id", "") or str(p.id))
            hits.append(SearchHit(id=ext_id, text=text, metadata=payload, score=float(p.score or 0.0)))
        return hits

    def delete_by_filter(self, filters: dict[str, Any]) -> int:
        flt = self._build_filter(must=filters, must_not=None)
        if flt is None:
            return 0
        before = self.count()
        self.client.delete(
            collection_name=self.collection,
            points_selector=self._qmodels.FilterSelector(filter=flt),
            wait=True,
        )
        after = self.count()
        return max(0, before - after)

    def count(self) -> int:
        try:
            return int(self.client.count(collection_name=self.collection, exact=True).count)
        except Exception:
            return 0


# ---------------------- Chroma 后端 (兼容旧数据) ----------------------

class ChromaVectorStore(VectorStore):
    def __init__(self, *, dim: int) -> None:
        import chromadb

        self.dim = dim
        db_path = Path(__file__).resolve().parents[2] / "data" / "kb_chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(
            name="requirement_chunks_v2",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Chroma 客户端 (兼容模式) 已就绪 path={}", db_path)

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        ids = [r.id for r in records]
        docs = [r.text for r in records]
        metas = [r.metadata or {} for r in records]
        embs = [r.embedding for r in records if r.embedding is not None]
        if len(embs) != len(records):
            raise ValueError("Chroma upsert: 部分 record 缺少 embedding")
        self.collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)

    def search(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        must_filters: dict[str, Any] | None = None,
        must_not_filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        where: dict[str, Any] = {}
        if must_filters:
            for k, v in must_filters.items():
                if isinstance(v, (list, tuple, set)):
                    where[k] = {"$in": list(v)}
                else:
                    where[k] = {"$eq": v}
        if must_not_filters:
            for k, v in must_not_filters.items():
                if isinstance(v, (list, tuple, set)):
                    where[k] = {"$nin": list(v)}
                else:
                    where[k] = {"$ne": v}
        result = self.collection.query(
            query_embeddings=[query_vector],
            n_results=max(1, top_k),
            where=where or None,
        )
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        hits: list[SearchHit] = []
        for doc_id, doc_text, meta, dist in zip(ids, docs, metas, dists):
            similarity = max(0.0, 1.0 - float(dist) / 2.0)
            if similarity < score_threshold:
                continue
            hits.append(SearchHit(id=str(doc_id), text=str(doc_text or ""), metadata=dict(meta or {}), score=similarity))
        return hits

    def delete_by_filter(self, filters: dict[str, Any]) -> int:
        before = self.collection.count()
        self.collection.delete(where={k: {"$eq": v} for k, v in filters.items()})
        return max(0, before - self.collection.count())

    def count(self) -> int:
        return int(self.collection.count())


# ---------------------- 工厂 + 单例 ----------------------

_store: VectorStore | None = None
_embedding: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding
    if _embedding is None:
        _embedding = EmbeddingService()
    return _embedding


def get_vector_store() -> VectorStore:
    global _store
    if _store is not None:
        return _store
    backend = (settings.VECTOR_DB_BACKEND or "qdrant").lower()
    dim = int(settings.EMBEDDING_DIM or 1536)
    if backend == "chroma":
        _store = ChromaVectorStore(dim=dim)
    else:
        _store = QdrantVectorStore(dim=dim)
    return _store


def reset_vector_store_singleton() -> None:
    """测试 / 迁移用：清掉单例。"""
    global _store, _embedding
    _store = None
    _embedding = None


# ---------------------- 异步包装 ----------------------

async def embed_text(text: str) -> list[float]:
    return await get_embedding_service().embed_one(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return await get_embedding_service().embed_many(texts)


async def aupsert(records: list[VectorRecord]) -> None:
    if not records:
        return
    store = get_vector_store()
    await asyncio.to_thread(store.upsert, records)


async def asearch(
    *,
    query_vector: list[float],
    top_k: int,
    score_threshold: float,
    must_filters: dict[str, Any] | None = None,
    must_not_filters: dict[str, Any] | None = None,
) -> list[SearchHit]:
    store = get_vector_store()
    return await asyncio.to_thread(
        store.search,
        query_vector=query_vector,
        top_k=top_k,
        score_threshold=score_threshold,
        must_filters=must_filters,
        must_not_filters=must_not_filters,
    )
