"""拆分历史「需求标题/子模块」拼接的 test_cases.module 字段。

作者: Zhao Wang

用法:
    cd backend && .venv/bin/python scripts/migrate_test_case_modules.py
    cd backend && .venv/bin/python scripts/migrate_test_case_modules.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.requirement_model import Requirement
from app.models.test_case_model import TestCase
from app.util.time_utils import now_str


def split_requirement_module(full_module: str, requirement_title: str) -> str | None:
    """若 module 为「需求标题/子模块」则返回子模块名。"""
    title = (requirement_title or "").strip()
    mod = (full_module or "").strip()
    if not title or not mod or "/" not in mod:
        return None
    prefix = f"{title}/"
    if mod.startswith(prefix):
        suffix = mod[len(prefix):].strip()
        return suffix or None
    return None


async def migrate(*, dry_run: bool) -> None:
    updated = 0
    skipped = 0
    unresolved = 0
    ts = now_str()

    async with AsyncSessionLocal() as db:
        stmt = select(TestCase).where(
            TestCase.requirement_id.isnot(None),
            TestCase.module.isnot(None),
            TestCase.module.like("%/%"),
        )
        cases = (await db.execute(stmt)).scalars().all()
        req_cache: dict[int, Requirement | None] = {}

        for case in cases:
            req_id = int(case.requirement_id)
            if req_id not in req_cache:
                req_cache[req_id] = await db.get(Requirement, req_id)
            req = req_cache[req_id]
            if not req:
                unresolved += 1
                continue

            sub_module = split_requirement_module(case.module or "", req.title)
            if not sub_module:
                skipped += 1
                continue
            if sub_module == case.module:
                skipped += 1
                continue

            print(f"  id={case.id}: {case.module!r} -> {sub_module!r}")
            if not dry_run:
                case.module = sub_module
                case.updated_at = ts
            updated += 1

        if not dry_run:
            await db.commit()

    mode = "DRY-RUN" if dry_run else "APPLIED"
    print(f"[{mode}] updated={updated}, skipped={skipped}, unresolved={unresolved}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate test case module names")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写库")
    args = parser.parse_args()
    asyncio.run(migrate(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
