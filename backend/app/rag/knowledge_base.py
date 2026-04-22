"""需求知识库

基于向量存储抽象层，对外提供：
- 入库：需求文档 chunk / 已采纳测试用例
- 检索：跨任务召回相似历史经验（强制 metadata 过滤防污染）
- prompt 上下文构建

升级要点（v3）：
- 默认用 Qdrant + 真实 OpenAI embedding（text-embedding-3-small）
- 跨任务召回**只检索 adopted_test_case**，不会调取别人的原始需求 chunk
- payload index 加速过滤，原生 must/must_not 二级筛选
- 失败兜底为 hash embedding，不影响主流程
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any

from loguru import logger

from app.core.config import settings
from app.rag.vector_store import (
    SearchHit,
    VectorRecord,
    asearch,
    aupsert,
    embed_text,
    embed_texts,
    get_vector_store,
)


CHUNK_MAX_CHARS = 700
CHUNK_OVERLAP_CHARS = 120

# 跨任务召回时只返回这些 entry_type，避免别人的需求原文跨领域污染。
CROSS_TASK_ALLOWED_TYPES = {"adopted_test_case"}


def _normalize_text(text: str) -> str:
    value = str(text or "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def split_requirement_text(
    text: str,
    *,
    max_chars: int = CHUNK_MAX_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:
    source = _normalize_text(text)
    if not source:
        return []

    raw_paragraphs = [p.strip() for p in source.split("\n\n") if p.strip()]
    paragraphs: list[str] = []
    for para in raw_paragraphs:
        if len(para) <= max_chars:
            paragraphs.append(para)
            continue
        for i in range(0, len(para), max_chars):
            piece = para[i:i + max_chars].strip()
            if piece:
                paragraphs.append(piece)

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = para if not current else f"{current}\n\n{para}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current.strip():
            chunks.append(current.strip())
            tail = current[-overlap_chars:] if overlap_chars > 0 else ""
            current = f"{tail}\n\n{para}".strip() if tail else para
        else:
            chunks.append(para)
            current = ""

    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]


# ---------------------- 入库 ----------------------

async def _aingest_document(
    *,
    task_id: str,
    text: str,
    source_type: str,
    file_name: str | None,
    submitter: str | None,
) -> dict:
    chunks = split_requirement_text(text)
    if not chunks:
        raise ValueError("需求文档拆分后为空，无法入库")

    embeddings = await embed_texts(chunks)
    now = datetime.utcnow().isoformat()

    records: list[VectorRecord] = []
    ids: list[str] = []
    for idx, (chunk, vec) in enumerate(zip(chunks, embeddings), start=1):
        rid = f"{task_id}:chunk:{idx}"
        ids.append(rid)
        records.append(
            VectorRecord(
                id=rid,
                text=chunk,
                metadata={
                    "task_id": task_id,
                    "entry_type": "requirement_chunk",
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "source_type": source_type or "",
                    "file_name": file_name or "",
                    "submitter": submitter or "",
                    "created_at": now,
                },
                embedding=vec,
            )
        )

    await aupsert(records)
    logger.info("KB ingest 需求: task={} chunks={}", task_id, len(records))
    return {"task_id": task_id, "chunk_count": len(records), "chunk_ids": ids}


async def _aingest_adopted(
    *,
    task_id: str,
    cases: list[dict[str, Any]],
    source_type: str,
    file_name: str | None,
    submitter: str | None,
) -> dict:
    valid = [c for c in cases if isinstance(c, dict)]
    if not valid:
        raise ValueError("采纳用例为空，无法入库")

    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    ext_ids: list[str] = []
    now = datetime.utcnow().isoformat()
    for idx, case in enumerate(valid, start=1):
        case_id = str(case.get("id") or idx).strip() or str(idx)
        module = str(case.get("module") or "").strip()
        title = str(case.get("title") or "").strip()
        precondition = str(case.get("precondition") or "").strip()
        steps = str(case.get("steps") or "").strip()
        expected_result = str(case.get("expected_result") or "").strip()
        priority = str(case.get("priority") or "").strip() or "中"
        adoption_status = str(case.get("adoption_status") or "accepted").strip()

        doc_text = "\n".join([
            "【历史采纳测试用例】",
            f"模块: {module}",
            f"标题: {title}",
            f"前置条件: {precondition}",
            f"测试步骤: {steps}",
            f"预期结果: {expected_result}",
            f"优先级: {priority}",
        ]).strip()
        if not _normalize_text(doc_text):
            continue

        docs.append(doc_text)
        ext_ids.append(f"{task_id}:adopted:{case_id}:{idx}")
        metas.append({
            "task_id": task_id,
            "entry_type": "adopted_test_case",
            "case_id": case_id,
            "case_module": module,
            "case_title": title,
            "case_priority": priority,
            "adoption_status": adoption_status,
            "source_type": source_type or "",
            "file_name": file_name or "",
            "submitter": submitter or "",
            "created_at": now,
        })

    if not docs:
        raise ValueError("采纳用例内容为空，无法入库")

    embeddings = await embed_texts(docs)
    records = [
        VectorRecord(id=ext_id, text=doc, metadata=meta, embedding=emb)
        for ext_id, doc, meta, emb in zip(ext_ids, docs, metas, embeddings)
    ]
    await aupsert(records)
    logger.info("KB ingest 采纳用例: task={} cases={}", task_id, len(records))
    return {"task_id": task_id, "case_count": len(records), "case_ids": ext_ids}


# ---------------------- 检索 ----------------------

async def _asearch_similar(
    *,
    query_text: str,
    current_task_id: str | None,
    top_k: int,
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    chunks = split_requirement_text(query_text)
    if not chunks:
        return []

    # 取前几个 chunks 的 embedding 各检索一次，合并后按 score 去重排序
    sample_chunks = chunks[:6]
    query_vectors = await embed_texts(sample_chunks)

    must_filters: dict[str, Any] = {"entry_type": list(CROSS_TASK_ALLOWED_TYPES)}
    must_not_filters: dict[str, Any] = {}
    if current_task_id:
        must_not_filters["task_id"] = current_task_id

    candidates: dict[str, dict[str, Any]] = {}
    for vec in query_vectors:
        hits: list[SearchHit] = await asearch(
            query_vector=vec,
            top_k=max(top_k * 3, 10),
            score_threshold=similarity_threshold,
            must_filters=must_filters,
            must_not_filters=must_not_filters or None,
        )
        for h in hits:
            prev = candidates.get(h.id)
            if prev:
                prev["similarity"] = max(float(prev["similarity"]), h.score)
                prev["hit_count"] = int(prev["hit_count"]) + 1
            else:
                candidates[h.id] = {
                    "id": h.id,
                    "task_id": str(h.metadata.get("task_id") or ""),
                    "similarity": h.score,
                    "hit_count": 1,
                    "text": h.text,
                    "metadata": h.metadata,
                }

    ranked = sorted(
        candidates.values(),
        key=lambda x: (float(x["similarity"]), int(x["hit_count"])),
        reverse=True,
    )
    return ranked[:top_k]


# ---------------------- 同步对外 API（向后兼容） ----------------------

def _run_async(coro):
    """在同步调用方安全执行协程（处理已有事件循环的情况）。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is None:
        return asyncio.run(coro)
    # 在事件循环中：同步包一层
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def ingest_requirement_document(
    *,
    task_id: str,
    text: str,
    source_type: str,
    file_name: str | None = None,
    submitter: str | None = None,
) -> dict:
    return _run_async(_aingest_document(
        task_id=task_id,
        text=text,
        source_type=source_type,
        file_name=file_name,
        submitter=submitter,
    ))


def ingest_adopted_test_cases(
    *,
    task_id: str,
    cases: list[dict[str, Any]],
    source_type: str,
    file_name: str | None = None,
    submitter: str | None = None,
) -> dict:
    return _run_async(_aingest_adopted(
        task_id=task_id,
        cases=cases,
        source_type=source_type,
        file_name=file_name,
        submitter=submitter,
    ))


def find_similar_requirement_history(
    *,
    query_text: str,
    current_task_id: str | None = None,
    top_k: int = 0,
) -> list[dict[str, Any]]:
    effective_top_k = top_k or int(settings.KB_TOP_K or 5)
    threshold = float(settings.KB_SIMILARITY_THRESHOLD or 0.55)
    return _run_async(_asearch_similar(
        query_text=query_text,
        current_task_id=current_task_id,
        top_k=effective_top_k,
        similarity_threshold=threshold,
    ))


def build_generation_history_context(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return ""

    lines = [
        "以下历史用例**仅用于参考测试用例的写法和颗粒度**，"
        "**不要**把其业务术语 / 模块名 / 字段名照搬到当前用例中："
    ]
    for idx, item in enumerate(matches, start=1):
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        score = f"{float(item.get('similarity') or 0.0):.3f}"
        source = str(meta.get("file_name") or meta.get("task_id") or item.get("task_id") or "unknown")
        snippet = str(item.get("text") or "").strip()
        if len(snippet) > 600:
            snippet = snippet[:600] + "..."
        lines.append(f"{idx}. 相似度={score} 来源={source}\n{snippet}")
    return "\n\n".join(lines)


def get_knowledge_base_stats() -> dict[str, Any]:
    """运维诊断用：返回当前向量库后端 + 总条目数。"""
    backend = (settings.VECTOR_DB_BACKEND or "qdrant").lower()
    try:
        store = get_vector_store()
        total = store.count()
    except Exception as exc:
        logger.exception("获取向量库统计失败: {}", exc)
        return {"backend": backend, "error": str(exc), "count": 0}
    return {
        "backend": backend,
        "embedding_model": settings.EMBEDDING_MODEL or "(hash fallback)",
        "embedding_dim": int(settings.EMBEDDING_DIM or 0),
        "count": total,
    }
