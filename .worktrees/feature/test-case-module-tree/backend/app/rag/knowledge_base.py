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
import hashlib
import re
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
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
CROSS_TASK_ALLOWED_TYPES = {"adopted_test_case", "task_summary"}

_PHASE_TOP_K: dict[str, str] = {
    "analysis": "KB_TOP_K_ANALYSIS",
    "strategy": "KB_TOP_K_STRATEGY",
    "generation": "KB_TOP_K",
    "generation_batch": "KB_TOP_K_MODULE",
}


def _is_transient_task_id(task_id: str) -> bool:
    """判断是否为流式/legacy 临时 task_id。"""
    tid = str(task_id or "").strip().lower()
    return tid.startswith("stream-") or tid.startswith("legacy-")


def _content_hash(text: str) -> str:
    """文本内容哈希（稳定 vector id）。"""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _text_jaccard(a: str, b: str) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


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
    """拆分需求文本；标题感知分段在入库 metadata 中记录 section_title。"""
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


def _extract_section_title(chunk: str) -> str:
    """从 chunk 首行提取 Markdown 标题作为 section_title。"""
    for line in chunk.splitlines():
        m = re.match(r"^#{1,4}\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    first = chunk.split("\n", 1)[0].strip()
    return first[:80] if first else ""


# ---------------------- 入库 ----------------------

async def _aingest_document(
    *,
    task_id: str,
    text: str,
    source_type: str,
    file_name: str | None,
    submitter: str | None,
) -> dict:
    if bool(getattr(settings, "KB_SKIP_TRANSIENT_INGEST", True)) and _is_transient_task_id(task_id):
        logger.info("KB skip transient ingest: task={}", task_id)
        return {"task_id": task_id, "chunk_count": 0, "skipped": True, "chunk_ids": []}

    chunks = split_requirement_text(text)
    if not chunks:
        raise ValueError("需求文档拆分后为空，无法入库")

    embeddings = await embed_texts(chunks)
    now = datetime.utcnow().isoformat()

    records: list[VectorRecord] = []
    ids: list[str] = []
    for idx, (chunk, vec) in enumerate(zip(chunks, embeddings), start=1):
        section_title = _extract_section_title(chunk)
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
                    "section_title": section_title,
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
        case_type = str(case.get("case_type") or "").strip()
        quality_score = case.get("quality_score")
        adoption_status = str(case.get("adoption_status") or "accepted").strip()

        doc_text = "\n".join([
            "【历史采纳测试用例】",
            f"模块: {module}",
            f"标题: {title}",
            f"类型: {case_type}",
            f"前置条件: {precondition}",
            f"测试步骤: {steps}",
            f"预期结果: {expected_result}",
            f"优先级: {priority}",
        ]).strip()
        if not _normalize_text(doc_text):
            continue

        content_hash = _content_hash(doc_text)
        docs.append(doc_text)
        ext_ids.append(f"{task_id}:adopted:{case_id}:{content_hash}")
        metas.append({
            "task_id": task_id,
            "entry_type": "adopted_test_case",
            "case_id": case_id,
            "case_module": module,
            "case_title": title,
            "case_type": case_type,
            "case_priority": priority,
            "quality_score": quality_score,
            "content_hash": content_hash,
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


async def _aingest_task_summary(
    *,
    task_id: str,
    summary_text: str,
    modules: list[str] | None = None,
    case_type_counts: dict[str, int] | None = None,
    source_type: str = "",
    file_name: str | None = None,
) -> dict:
    """入库任务级摘要，供跨任务快速召回。"""
    if bool(getattr(settings, "KB_SKIP_TRANSIENT_INGEST", True)) and _is_transient_task_id(task_id):
        return {"task_id": task_id, "skipped": True}
    body = _normalize_text(summary_text)
    if not body:
        return {"task_id": task_id, "skipped": True, "reason": "empty_summary"}
    modules_line = ", ".join(modules or [])
    type_line = ", ".join(f"{k}:{v}" for k, v in (case_type_counts or {}).items())
    doc = "\n".join([
        "【任务测试摘要】",
        body,
        f"模块清单: {modules_line}" if modules_line else "",
        f"用例类型分布: {type_line}" if type_line else "",
    ]).strip()
    vec = await embed_text(doc)
    now = datetime.utcnow().isoformat()
    rid = f"{task_id}:summary:{_content_hash(doc)}"
    record = VectorRecord(
        id=rid,
        text=doc,
        metadata={
            "task_id": task_id,
            "entry_type": "task_summary",
            "modules": modules or [],
            "case_type_counts": case_type_counts or {},
            "source_type": source_type,
            "file_name": file_name or "",
            "created_at": now,
        },
        embedding=vec,
    )
    await aupsert([record])
    return {"task_id": task_id, "summary_id": rid}


# ---------------------- 检索 ----------------------

def rerank_kb_hits(
    hits: list[dict[str, Any]],
    query_text: str,
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """MMR 风格重排：优先 task_summary，抑制近重复 snippet。"""
    if not hits:
        return []
    query_norm = _normalize_text(query_text)[:500]

    def _boost(item: dict[str, Any]) -> float:
        base = float(item.get("similarity") or 0.0)
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        if meta.get("entry_type") == "task_summary":
            base += 0.08
        if query_norm and query_norm[:40] in str(item.get("text") or ""):
            base += 0.02
        return base

    ranked = sorted(hits, key=_boost, reverse=True)
    selected: list[dict[str, Any]] = []
    for item in ranked:
        if len(selected) >= top_k:
            break
        text = str(item.get("text") or "")
        if all(_text_jaccard(text, s.get("text", "")) < 0.88 for s in selected):
            selected.append(item)
    if len(selected) < top_k:
        for item in ranked:
            if item not in selected:
                selected.append(item)
            if len(selected) >= top_k:
                break
    return selected[:top_k]


async def _asearch_similar(
    *,
    query_text: str,
    current_task_id: str | None,
    top_k: int,
    similarity_threshold: float,
    module_filter: str | None = None,
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
            if module_filter:
                meta = h.metadata or {}
                mod = str(meta.get("case_module") or meta.get("modules") or "")
                if mod and module_filter not in mod and mod not in module_filter:
                    if SequenceMatcher(None, module_filter, mod).ratio() < 0.55:
                        continue
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
    module_filter: str | None = None,
) -> list[dict[str, Any]]:
    effective_top_k = top_k or int(settings.KB_TOP_K or 5)
    threshold = float(settings.KB_SIMILARITY_THRESHOLD or 0.55)
    hits = _run_async(_asearch_similar(
        query_text=query_text,
        current_task_id=current_task_id,
        top_k=effective_top_k,
        similarity_threshold=threshold,
        module_filter=module_filter,
    ))
    if hits:
        return hits
    if bool(getattr(settings, "KB_SQL_FALLBACK_ENABLED", False)):
        return _sql_keyword_fallback(query_text, top_k=effective_top_k)
    return []


def retrieve_kb_context(
    phase: str,
    query_text: str,
    *,
    current_task_id: str | None = None,
    module_filter: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """多阶段 KB 检索并组装 prompt 上下文。"""
    cfg_key = _PHASE_TOP_K.get(phase, "KB_TOP_K")
    top_k = int(getattr(settings, cfg_key, 0) or settings.KB_TOP_K or 5)
    raw_hits = find_similar_requirement_history(
        query_text=query_text,
        current_task_id=current_task_id,
        top_k=top_k * 2,
        module_filter=module_filter,
    )
    reranked = rerank_kb_hits(raw_hits, query_text, top_k=top_k)
    context = build_generation_history_context(reranked)
    max_chars = int(getattr(settings, "KB_CONTEXT_MAX_CHARS", 2400) or 2400)
    if len(context) > max_chars:
        context = context[:max_chars] + "\n...(KB 上下文已截断)"
    meta = {
        "phase": phase,
        "top_k": top_k,
        "hit_count": len(reranked),
        "embedding_mode": settings.EMBEDDING_MODEL or "hash_fallback",
        "module_filter": module_filter,
        "preview": [
            {
                "id": h.get("id"),
                "similarity": h.get("similarity"),
                "entry_type": (h.get("metadata") or {}).get("entry_type"),
            }
            for h in reranked[:5]
        ],
    }
    return context, meta


def _sql_keyword_fallback(query_text: str, *, top_k: int) -> list[dict[str, Any]]:
    """冷启动：从 SQLite test_cases 表关键词召回。"""
    db_path = Path(str(getattr(settings, "SQLITE_DB_PATH", "./data/app.db")))
    if not db_path.is_file():
        return []
    keywords = [w for w in re.split(r"\W+", query_text) if len(w) >= 2][:8]
    if not keywords:
        return []
    like_clause = " OR ".join(["title LIKE ? OR module LIKE ?"] * len(keywords))
    params: list[str] = []
    for kw in keywords:
        pat = f"%{kw}%"
        params.extend([pat, pat])
    sql = (
        f"SELECT id, title, module, precondition, description FROM test_cases "
        f"WHERE status='active' AND ({like_clause}) ORDER BY id DESC LIMIT ?"
    )
    params.append(top_k)
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        conn.close()
    except Exception as exc:
        logger.warning("KB SQL fallback 失败: {}", exc)
        return []
    results: list[dict[str, Any]] = []
    for row in rows:
        text = "\n".join([
            "【历史用例库】",
            f"模块: {row['module'] or ''}",
            f"标题: {row['title'] or ''}",
            f"前置: {row['precondition'] or ''}",
            f"预期: {row['description'] or ''}",
        ])
        results.append({
            "id": f"sql:{row['id']}",
            "task_id": "",
            "similarity": 0.5,
            "hit_count": 1,
            "text": text,
            "metadata": {"entry_type": "sql_fallback", "case_id": row["id"]},
        })
    return results


def build_generation_history_context(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return ""

    snippet_max = int(getattr(settings, "KB_SNIPPET_MAX_CHARS", 600) or 600)
    modules: set[str] = set()
    type_counts: dict[str, int] = {}
    for item in matches:
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        mod = str(meta.get("case_module") or "").strip()
        if mod:
            modules.add(mod)
        ct = str(meta.get("case_type") or "").strip()
        if ct:
            type_counts[ct] = type_counts.get(ct, 0) + 1

    lines = [
        "以下历史用例**仅用于参考测试用例的写法和颗粒度**，"
        "**不要**把其业务术语 / 模块名 / 字段名照搬到当前用例中：",
    ]
    if modules:
        lines.append(f"【历史模块分布】{', '.join(sorted(modules)[:20])}")
    if type_counts:
        dist = ", ".join(f"{k}:{v}" for k, v in sorted(type_counts.items()))
        lines.append(f"【历史 case_type 分布】{dist}")

    for idx, item in enumerate(matches, start=1):
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        score = f"{float(item.get('similarity') or 0.0):.3f}"
        source = str(meta.get("file_name") or meta.get("task_id") or item.get("task_id") or "unknown")
        entry = str(meta.get("entry_type") or "")
        snippet = str(item.get("text") or "").strip()
        if len(snippet) > snippet_max:
            snippet = snippet[:snippet_max] + "..."
        lines.append(f"{idx}. 相似度={score} 类型={entry} 来源={source}\n{snippet}")
    return "\n\n".join(lines)


def ingest_task_summary(
    *,
    task_id: str,
    summary_text: str,
    modules: list[str] | None = None,
    case_type_counts: dict[str, int] | None = None,
    source_type: str = "",
    file_name: str | None = None,
) -> dict:
    """同步包装：任务摘要入库。"""
    return _run_async(_aingest_task_summary(
        task_id=task_id,
        summary_text=summary_text,
        modules=modules,
        case_type_counts=case_type_counts,
        source_type=source_type,
        file_name=file_name,
    ))


def purge_kb_by_task_prefix(task_prefix: str) -> dict[str, Any]:
    """按 task_id 前缀清理向量（运维脚本）。"""
    prefix = str(task_prefix or "").strip()
    if not prefix:
        return {"deleted": 0}
    try:
        store = get_vector_store()
        if hasattr(store, "delete_by_metadata_prefix"):
            deleted = store.delete_by_metadata_prefix("task_id", prefix)
            return {"deleted": deleted, "prefix": prefix}
        logger.warning("向量库不支持 delete_by_metadata_prefix，跳过 purge")
        return {"deleted": 0, "skipped": True}
    except Exception as exc:
        logger.exception("purge_kb_by_task_prefix 失败: {}", exc)
        return {"deleted": 0, "error": str(exc)}


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
