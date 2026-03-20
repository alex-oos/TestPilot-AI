from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.core.database import AsyncSessionLocal
from app.repositories import TaskTableRepository


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            # keep consistent with persisted UTC-like timestamps
            return dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return dt
    except Exception:
        return None


def _round1(value: float) -> float:
    return round(value, 1)


def _change_pct(current: float, previous: float) -> Optional[float]:
    if previous <= 0:
        return None
    return _round1(((current - previous) / previous) * 100.0)


def _safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return _round1((numerator / denominator) * 100.0)


async def get_dashboard_overview() -> Dict[str, Any]:
    tz = datetime.now().astimezone().tzinfo
    now = datetime.now(tz=tz)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    prev_week_start = week_start - timedelta(days=7)

    async with AsyncSessionLocal() as db:
        total_tasks = await TaskTableRepository.count_all(db)
        status_counts = await TaskTableRepository.count_by_status(db)
        source_counts = await TaskTableRepository.count_by_source_type(db)
        tasks = await TaskTableRepository.list_all(db)

    completed_tasks = int(status_counts.get("completed", 0))
    coverage_rate = _safe_pct(completed_tasks, total_tasks)

    weekly_activity = [0, 0, 0, 0, 0, 0, 0]  # Monday -> Sunday
    this_week_total = 0
    prev_week_total = 0
    this_week_completed = 0
    prev_week_completed = 0
    completed_durations_all: list[float] = []
    completed_durations_this_week: list[float] = []
    completed_durations_prev_week: list[float] = []

    for task in tasks:
        created_at = _parse_time(getattr(task, "created_at", None))
        updated_at = _parse_time(getattr(task, "updated_at", None))
        status = str(getattr(task, "status", "") or "")

        if created_at:
            local_created = created_at.astimezone(tz)
            if week_start <= local_created < week_end:
                this_week_total += 1
                weekly_activity[local_created.weekday()] += 1
                if status == "completed":
                    this_week_completed += 1
            elif prev_week_start <= local_created < week_start:
                prev_week_total += 1
                if status == "completed":
                    prev_week_completed += 1

        if status == "completed" and created_at and updated_at:
            duration = (updated_at - created_at).total_seconds()
            if duration >= 0:
                completed_durations_all.append(duration)
                if week_start <= created_at.astimezone(tz) < week_end:
                    completed_durations_this_week.append(duration)
                elif prev_week_start <= created_at.astimezone(tz) < week_start:
                    completed_durations_prev_week.append(duration)

    avg_duration_all = _round1(sum(completed_durations_all) / len(completed_durations_all)) if completed_durations_all else 0.0
    avg_duration_this_week = (
        _round1(sum(completed_durations_this_week) / len(completed_durations_this_week))
        if completed_durations_this_week else 0.0
    )
    avg_duration_prev_week = (
        _round1(sum(completed_durations_prev_week) / len(completed_durations_prev_week))
        if completed_durations_prev_week else 0.0
    )

    source_meta = [
        ("feishu", "飞书文档", "📄"),
        ("dingtalk", "钉钉文档", "💬"),
        ("local", "本地上传文件", "📁"),
        ("manual", "手动输入需求", "✍️"),
    ]
    source_distribution = []
    for source_type, label, icon in source_meta:
        count = int(source_counts.get(source_type, 0))
        source_distribution.append(
            {
                "source_type": source_type,
                "label": label,
                "icon": icon,
                "count": count,
                "percent": _safe_pct(count, total_tasks),
            }
        )

    # Include unknown sources if any
    known = {x[0] for x in source_meta}
    for source_type, count in source_counts.items():
        if source_type in known:
            continue
        source_distribution.append(
            {
                "source_type": source_type or "unknown",
                "label": source_type or "未知来源",
                "icon": "🧩",
                "count": int(count),
                "percent": _safe_pct(int(count), total_tasks),
            }
        )

    source_distribution.sort(key=lambda x: x["count"], reverse=True)

    labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekly_series = [{"label": labels[i], "value": weekly_activity[i]} for i in range(7)]

    coverage_this_week = _safe_pct(this_week_completed, this_week_total)
    coverage_prev_week = _safe_pct(prev_week_completed, prev_week_total)

    return {
        "summary": {
            "total_documents": total_tasks,
            "generated_cases_total": completed_tasks,
            "coverage_rate": coverage_rate,
            "average_duration_seconds": avg_duration_all,
            "this_week_new_count": this_week_total,
        },
        "trends": {
            "documents_week_change_pct": _change_pct(this_week_total, prev_week_total),
            "generated_week_change_pct": _change_pct(this_week_completed, prev_week_completed),
            "coverage_week_change_pct": _change_pct(coverage_this_week, coverage_prev_week),
            "average_duration_week_change_pct": _change_pct(avg_duration_this_week, avg_duration_prev_week),
        },
        "weekly_activity": weekly_series,
        "source_distribution": source_distribution,
        "status_distribution": {
            "pending": int(status_counts.get("pending", 0)),
            "running": int(status_counts.get("running", 0)),
            "completed": int(status_counts.get("completed", 0)),
            "failed": int(status_counts.get("failed", 0)),
        },
    }
