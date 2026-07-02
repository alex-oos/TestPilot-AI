"""把现有 Chroma 数据迁移到 Qdrant。

用法：
    cd backend
    python scripts/migrate_chroma_to_qdrant.py [--reembed]

--reembed   用真实 embedding 模型重新计算向量（强烈推荐！旧 hash embedding 没有语义）。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# 让脚本能 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger

from app.core.config import settings
from app.rag.vector_store import (
    QdrantVectorStore,
    VectorRecord,
    embed_texts,
    get_embedding_service,
)


def _load_chroma_records() -> list[dict]:
    import chromadb
    chroma_path = Path(__file__).resolve().parents[1] / "data" / "kb_chroma_db"
    if not chroma_path.exists():
        logger.warning("Chroma 路径不存在: {}", chroma_path)
        return []
    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        col = client.get_collection(name="requirement_chunks_v2")
    except Exception as exc:
        logger.warning("Chroma 集合不存在: {}", exc)
        return []
    items = col.get(include=["metadatas", "documents", "embeddings"])
    ids = items.get("ids") or []
    docs = items.get("documents") or []
    metas = items.get("metadatas") or []
    embs_raw = items.get("embeddings")
    if embs_raw is None:
        embs = []
    else:
        embs = list(embs_raw)  # 可能是 numpy 数组
    out = []
    for i, doc_id in enumerate(ids):
        embedding = None
        if i < len(embs):
            v = embs[i]
            if v is not None:
                try:
                    embedding = list(v)
                except TypeError:
                    embedding = None
        out.append({
            "id": str(doc_id),
            "text": str(docs[i] if i < len(docs) else "") or "",
            "metadata": dict(metas[i] if i < len(metas) else {}) or {},
            "embedding": embedding,
        })
    logger.info("从 Chroma 读取 {} 条记录", len(out))
    return out


async def _amigrate(reembed: bool) -> None:
    src_records = _load_chroma_records()
    if not src_records:
        logger.info("没有需要迁移的数据。")
        return

    target = QdrantVectorStore(dim=int(settings.EMBEDDING_DIM or 1536))
    logger.info("Qdrant 目标集合 {} 当前条目数: {}", target.collection, target.count())

    emb_service = get_embedding_service()
    if reembed and not emb_service.is_real:
        logger.error("--reembed 需要配置真实 EMBEDDING_MODEL，请先设置 .env")
        return

    if reembed:
        logger.info("使用真实 embedding 重算向量 (model={}, dim={}) ...", emb_service.model, emb_service.dim)
        texts = [r["text"] for r in src_records]
        new_vecs = await embed_texts(texts)
        for r, v in zip(src_records, new_vecs):
            r["embedding"] = v
    else:
        kept = [r for r in src_records if r["embedding"]]
        logger.info("沿用 Chroma 原有 embedding (向量数 {} / {})", len(kept), len(src_records))

    records = []
    skipped = 0
    for r in src_records:
        if not r["embedding"]:
            skipped += 1
            continue
        records.append(VectorRecord(
            id=r["id"],
            text=r["text"],
            metadata=r["metadata"],
            embedding=r["embedding"],
        ))
    if skipped:
        logger.warning("跳过 {} 条无 embedding 的记录", skipped)

    if records:
        # 分批写入，防止单次过大
        batch = 100
        for i in range(0, len(records), batch):
            target.upsert(records[i:i + batch])
        logger.success("成功写入 Qdrant {} 条记录，目标集合现共 {} 条", len(records), target.count())
    else:
        logger.warning("没有可写入 Qdrant 的记录")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reembed", action="store_true",
                        help="用真实 embedding 模型重算向量（强烈推荐）")
    args = parser.parse_args()
    asyncio.run(_amigrate(reembed=args.reembed))


if __name__ == "__main__":
    main()
