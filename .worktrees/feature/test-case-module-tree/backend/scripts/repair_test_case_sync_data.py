"""修复历史同步用例：回填 requirement_id、清理 module HTML。

作者: Zhao Wang

用法:
    cd backend && .venv/bin/python scripts/repair_test_case_sync_data.py
    cd backend && .venv/bin/python scripts/repair_test_case_sync_data.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.task_detail_model import TaskDetail
from app.models.test_case_model import TestCase
from app.services.test_case_sync_utils import coerce_optional_int, strip_html_tags
from app.util.time_utils import now_str


async def repair(*, dry_run: bool) -> None:
    """回填任务 upload 元数据并规范化 module 字段。"""
    html_fixed = 0
    req_backfilled = 0
    proj_backfilled = 0
    ts = now_str()

    async with AsyncSessionLocal() as db:
        cases = (await db.execute(select(TestCase))).scalars().all()
        upload_meta_by_task: dict[str, dict] = {}

        for case in cases:
            raw_module = case.module or ""
            clean_module = strip_html_tags(raw_module)
            if clean_module != raw_module:
                print(f"  module id={case.id}: {raw_module!r} -> {clean_module!r}")
                if not dry_run:
                    case.module = clean_module or None
                    case.updated_at = ts
                html_fixed += 1

            task_id = str(case.task_id or "").strip()
            if not task_id:
                continue

            if task_id not in upload_meta_by_task:
                row = (
                    await db.execute(
                        select(TaskDetail).where(
                            TaskDetail.task_id == task_id,
                            TaskDetail.phase_key == "upload",
                        )
                    )
                ).scalars().first()
                meta: dict = {}
                if row and row.data_json:
                    try:
                        parsed = json.loads(row.data_json)
                        if isinstance(parsed, dict):
                            meta = parsed
                    except json.JSONDecodeError:
                        pass
                upload_meta_by_task[task_id] = meta

            meta = upload_meta_by_task[task_id]
            meta_req = coerce_optional_int(meta.get("requirement_id"))
            meta_proj = coerce_optional_int(meta.get("project_id"))

            changed = False
            if meta_req is not None and case.requirement_id is None:
                print(f"  requirement_id id={case.id}: None -> {meta_req}")
                if not dry_run:
                    case.requirement_id = meta_req
                    case.updated_at = ts
                req_backfilled += 1
                changed = True

            if meta_proj is not None and case.project_id is None:
                if not dry_run:
                    case.project_id = meta_proj
                    case.updated_at = ts
                proj_backfilled += 1
                changed = True

            if changed and not dry_run:
                pass

        if not dry_run:
            await db.commit()

    mode = "DRY-RUN" if dry_run else "APPLIED"
    print(
        f"[{mode}] html_fixed={html_fixed}, "
        f"requirement_id_backfilled={req_backfilled}, "
        f"project_id_backfilled={proj_backfilled}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair synced test case metadata")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写库")
    args = parser.parse_args()
    asyncio.run(repair(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
