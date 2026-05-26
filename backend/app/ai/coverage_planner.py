"""覆盖驱动生成：覆盖矩阵、缺口检测、合并去重。

作者: Zhao Wang
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from app.ai.strategy_schema import TestStrategyV1


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip().lower())


def _title_similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _steps_prefix(steps: str, n: int = 100) -> str:
    return (steps or "")[:n]


def _jaccard(a: str, b: str) -> float:
    sa = set(_norm(a))
    sb = set(_norm(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def build_coverage_matrix(
    strategy: TestStrategyV1,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """构建 test_point → case_ids 覆盖矩阵。"""
    mapping: dict[str, list[Any]] = {}
    uncovered: list[dict[str, Any]] = []

    tp_index: list[tuple[str, str, str]] = []
    for mod in strategy.modules:
        for tp in mod.test_points:
            tp_index.append((mod.name, tp.id, tp.title))

    for mod_name, tp_id, tp_title in tp_index:
        matched: list[Any] = []
        for c in cases:
            c_mod = str(c.get("module") or "").strip()
            c_title = str(c.get("title") or "").strip()
            mod_ok = (not c_mod) or _title_similar(c_mod, mod_name) >= 0.6 or mod_name in c_mod or c_mod in mod_name
            title_ok = _title_similar(c_title, tp_title) >= 0.45 or tp_title[:8] in c_title
            if mod_ok and title_ok:
                matched.append(c.get("id"))
        mapping[tp_id] = matched
        if not matched:
            uncovered.append({"module": mod_name, "test_point_id": tp_id, "title": tp_title})

    return {
        "mapping": mapping,
        "uncovered": uncovered,
        "covered_count": sum(1 for v in mapping.values() if v),
        "total_test_points": len(tp_index),
    }


def find_coverage_gaps(
    strategy: TestStrategyV1,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """查找未覆盖测试点与缺失 case_type。"""
    matrix = build_coverage_matrix(strategy, cases)
    types_present = {str(c.get("case_type") or "").strip() for c in cases}
    required = set(strategy.global_requirements.required_case_types or [])
    missing_types = [t for t in required if t and t not in types_present]
    return {
        "uncovered_test_points": matrix["uncovered"],
        "missing_case_types": missing_types,
        "coverage_matrix": matrix,
    }


def merge_and_dedupe_cases(
    batches: list[list[dict[str, Any]]],
    *,
    case_scores: dict[Any, int] | None = None,
) -> list[dict[str, Any]]:
    """合并多批用例并去重。"""
    merged: list[dict[str, Any]] = []
    for batch in batches:
        merged.extend(batch)
    return normalize_merged_cases(merged, case_scores=case_scores)


def normalize_merged_cases(
    cases: list[dict[str, Any]],
    *,
    canonical_modules: list[str] | None = None,
    case_scores: dict[Any, int] | None = None,
) -> list[dict[str, Any]]:
    """id 重排、module 归一、语义去重。"""
    if not cases:
        return []

    scores = case_scores or {}
    normalized: list[dict[str, Any]] = []
    for c in cases:
        item = dict(c)
        if canonical_modules:
            item["module"] = _match_canonical_module(str(item.get("module") or ""), canonical_modules)
        normalized.append(item)

    deduped: list[dict[str, Any]] = []
    for c in normalized:
        dup_idx = None
        for i, existing in enumerate(deduped):
            if _title_similar(str(c.get("title")), str(existing.get("title"))) >= 0.92:
                if _jaccard(_steps_prefix(str(c.get("steps"))), _steps_prefix(str(existing.get("steps")))) > 0.85:
                    dup_idx = i
                    break
        if dup_idx is None:
            deduped.append(c)
        else:
            old_id = deduped[dup_idx].get("id")
            new_id = c.get("id")
            old_score = scores.get(old_id, 0)
            new_score = scores.get(new_id, 0)
            if new_score > old_score:
                deduped[dup_idx] = c

    for idx, c in enumerate(deduped, start=1):
        c["id"] = idx
    return deduped


def _match_canonical_module(module: str, canonical: list[str]) -> str:
    if not module:
        return canonical[0] if canonical else module
    for name in canonical:
        if _title_similar(module, name) >= 0.7 or name in module or module in name:
            return name
    if len(canonical) == 1:
        return canonical[0]
    return module


def split_strategy_batches(
    strategy: TestStrategyV1,
    *,
    max_test_points_per_batch: int = 15,
    max_batches: int = 20,
) -> list[dict[str, Any]]:
    """将策略拆为生成 batch 列表。"""
    batches: list[dict[str, Any]] = []
    for mod in strategy.modules:
        tps = mod.test_points
        if len(tps) <= max_test_points_per_batch:
            batches.append({"module": mod.name, "test_points": tps, "risk_level": mod.risk_level})
        else:
            for i in range(0, len(tps), max_test_points_per_batch):
                batches.append({
                    "module": mod.name,
                    "test_points": tps[i:i + max_test_points_per_batch],
                    "risk_level": mod.risk_level,
                    "sub_batch": i // max_test_points_per_batch + 1,
                })

    if len(batches) <= max_batches:
        return batches

    merged: list[dict[str, Any]] = []
    chunk_size = max(1, len(batches) // max_batches)
    for i in range(0, len(batches), chunk_size):
        group = batches[i:i + chunk_size]
        all_tps = []
        mod_name = group[0]["module"]
        for g in group:
            all_tps.extend(g["test_points"])
        merged.append({"module": mod_name, "test_points": all_tps, "merged": True})
    return merged[:max_batches]
