from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from loguru import logger


CHUNK_MAX_CHARS = 700
CHUNK_OVERLAP_CHARS = 120
EMBEDDING_DIM = 384
SIMILARITY_THRESHOLD = 0.45
DEFAULT_TOP_K = 5
COLLECTION_NAME = "requirement_chunks_v2"
KEYWORD_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6


def _normalize_text(text: str) -> str:
    value = str(text or "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def split_requirement_text(text: str, *, max_chars: int = CHUNK_MAX_CHARS, overlap_chars: int = CHUNK_OVERLAP_CHARS) -> list[str]:
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


def _tokenize_for_embedding(text: str) -> list[str]:
    value = str(text or "").lower()
    tokens: list[str] = re.findall(r"[a-z0-9_]+", value)
    cjk_sequences = re.findall(r"[\u4e00-\u9fff]+", value)
    for seq in cjk_sequences:
        chars = [ch for ch in seq if ch.strip()]
        tokens.extend(chars)
        tokens.extend(seq[i:i + 2] for i in range(len(seq) - 1))
    return [t for t in tokens if t]


def _hash_embedding(text: str, *, dim: int = EMBEDDING_DIM) -> list[float]:
    tokens = _tokenize_for_embedding(text)
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


def _distance_to_similarity(distance: Any) -> float:
    try:
        dist = float(distance)
    except Exception:
        return 0.0
    similarity = 1.0 - (dist / 2.0)
    return max(0.0, min(1.0, similarity))


def _keyword_relevance_score(query_text: str, doc_text: str) -> float:
    query_tokens = set(_tokenize_for_embedding(query_text))
    doc_tokens = set(_tokenize_for_embedding(doc_text))
    if not query_tokens or not doc_tokens:
        return 0.0
    overlap = query_tokens.intersection(doc_tokens)
    return len(overlap) / max(len(query_tokens), 1)


class RequirementKnowledgeBase:
    def __init__(self) -> None:
        db_path = Path(__file__).resolve().parents[2] / "data" / "kb_chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    def ingest_document(
        self,
        *,
        task_id: str,
        text: str,
        source_type: str,
        file_name: str | None = None,
        submitter: str | None = None,
    ) -> dict:
        chunks = split_requirement_text(text)
        if not chunks:
            raise ValueError("需求文档拆分后为空，无法入库")

        now = datetime.utcnow().isoformat()
        ids: list[str] = []
        metadatas: list[dict[str, Any]] = []
        for idx, chunk in enumerate(chunks, start=1):
            ids.append(f"{task_id}:{idx}")
            metadatas.append(
                {
                    "task_id": task_id,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "source_type": source_type or "",
                    "file_name": file_name or "",
                    "submitter": submitter or "",
                    "created_at": now,
                }
            )

        embeddings = [_hash_embedding(chunk) for chunk in chunks]
        self.collection.upsert(ids=ids, documents=chunks, metadatas=metadatas, embeddings=embeddings)
        logger.info("Knowledge base ingested: task_id={}, chunks={}", task_id, len(chunks))
        return {"task_id": task_id, "chunk_count": len(chunks), "chunk_ids": ids}

    def ingest_adopted_cases(
        self,
        *,
        task_id: str,
        cases: list[dict[str, Any]],
        source_type: str,
        file_name: str | None = None,
        submitter: str | None = None,
    ) -> dict:
        valid_cases = [item for item in cases if isinstance(item, dict)]
        if not valid_cases:
            raise ValueError("采纳用例为空，无法入库")

        now = datetime.utcnow().isoformat()
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for idx, case in enumerate(valid_cases, start=1):
            case_id = str(case.get("id") or idx).strip() or str(idx)
            module = str(case.get("module") or "").strip()
            title = str(case.get("title") or "").strip()
            precondition = str(case.get("precondition") or "").strip()
            steps = str(case.get("steps") or "").strip()
            expected_result = str(case.get("expected_result") or "").strip()
            priority = str(case.get("priority") or "").strip() or "中"
            adoption_status = str(case.get("adoption_status") or "accepted").strip()

            doc_text = "\n".join(
                [
                    "【历史采纳测试用例】",
                    f"模块: {module}",
                    f"标题: {title}",
                    f"前置条件: {precondition}",
                    f"测试步骤: {steps}",
                    f"预期结果: {expected_result}",
                    f"优先级: {priority}",
                ]
            ).strip()
            if not _normalize_text(doc_text):
                continue

            ids.append(f"{task_id}:adopted:{case_id}:{idx}")
            documents.append(doc_text)
            metadatas.append(
                {
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
                }
            )

        if not documents:
            raise ValueError("采纳用例内容为空，无法入库")

        embeddings = [_hash_embedding(doc) for doc in documents]
        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        logger.info("Knowledge base ingested adopted cases: task_id={}, cases={}", task_id, len(documents))
        return {"task_id": task_id, "case_count": len(documents), "case_ids": ids}

    def search_similar(
        self,
        *,
        query_text: str,
        current_task_id: str | None = None,
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ) -> list[dict[str, Any]]:
        query_chunks = split_requirement_text(query_text)
        if not query_chunks:
            return []

        candidate_map: dict[str, dict[str, Any]] = {}
        for chunk in query_chunks[:8]:
            query_embedding = _hash_embedding(chunk)
            result = self.collection.query(query_embeddings=[query_embedding], n_results=max(top_k * 4, 12))
            ids = (result.get("ids") or [[]])[0]
            docs = (result.get("documents") or [[]])[0]
            metas = (result.get("metadatas") or [[]])[0]
            dists = (result.get("distances") or [[]])[0]
            for doc_id, doc_text, meta, distance in zip(ids, docs, metas, dists):
                if not doc_id or not isinstance(meta, dict):
                    continue
                task_id = str(meta.get("task_id") or "")
                if current_task_id and task_id == current_task_id:
                    continue
                vector_similarity = _distance_to_similarity(distance)
                keyword_score = _keyword_relevance_score(chunk, str(doc_text or ""))
                hybrid_score = (VECTOR_WEIGHT * vector_similarity) + (KEYWORD_WEIGHT * keyword_score)
                if hybrid_score < similarity_threshold:
                    continue
                prev = candidate_map.get(doc_id)
                if prev:
                    prev["vector_similarity"] = max(float(prev.get("vector_similarity") or 0.0), vector_similarity)
                    prev["keyword_score"] = max(float(prev.get("keyword_score") or 0.0), keyword_score)
                    prev["similarity"] = max(float(prev.get("similarity") or 0.0), hybrid_score)
                    prev["hit_count"] = int(prev.get("hit_count") or 1) + 1
                    continue
                candidate_map[doc_id] = {
                    "id": doc_id,
                    "task_id": task_id,
                    "similarity": hybrid_score,
                    "vector_similarity": vector_similarity,
                    "keyword_score": keyword_score,
                    "hit_count": 1,
                    "text": str(doc_text or ""),
                    "metadata": meta,
                }

        ranked = sorted(
            candidate_map.values(),
            key=lambda item: (float(item.get("similarity") or 0.0), int(item.get("hit_count") or 0)),
            reverse=True,
        )
        return ranked[:top_k]


_kb: RequirementKnowledgeBase | None = None


def _get_kb() -> RequirementKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = RequirementKnowledgeBase()
    return _kb


def ingest_requirement_document(
    *,
    task_id: str,
    text: str,
    source_type: str,
    file_name: str | None = None,
    submitter: str | None = None,
) -> dict:
    return _get_kb().ingest_document(
        task_id=task_id,
        text=text,
        source_type=source_type,
        file_name=file_name,
        submitter=submitter,
    )


def find_similar_requirement_history(
    *,
    query_text: str,
    current_task_id: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    return _get_kb().search_similar(query_text=query_text, current_task_id=current_task_id, top_k=top_k)


def ingest_adopted_test_cases(
    *,
    task_id: str,
    cases: list[dict[str, Any]],
    source_type: str,
    file_name: str | None = None,
    submitter: str | None = None,
) -> dict:
    return _get_kb().ingest_adopted_cases(
        task_id=task_id,
        cases=cases,
        source_type=source_type,
        file_name=file_name,
        submitter=submitter,
    )


def build_generation_history_context(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return ""

    lines = ["以下是历史相似需求片段，请基于这些历史经验生成测试用例："]
    for idx, item in enumerate(matches, start=1):
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        score = f"{float(item.get('similarity') or 0.0):.3f}"
        vector_score = f"{float(item.get('vector_similarity') or 0.0):.3f}"
        keyword_score = f"{float(item.get('keyword_score') or 0.0):.3f}"
        source = str(meta.get("file_name") or meta.get("task_id") or item.get("task_id") or "unknown")
        snippet = str(item.get("text") or "").strip()
        if len(snippet) > 700:
            snippet = snippet[:700] + "..."
        lines.append(
            f"{idx}. 混合相似度={score} (向量={vector_score}, 关键词={keyword_score}) 来源={source}\n{snippet}"
        )
    return "\n\n".join(lines)
