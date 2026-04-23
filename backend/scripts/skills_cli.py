#!/usr/bin/env python3
"""QA Skills CLI：list / validate / show / diff / audit / route。

用法：
  python scripts/skills_cli.py list
  python scripts/skills_cli.py validate                # 调用 health 检查
  python scripts/skills_cli.py show <skill_id>
  python scripts/skills_cli.py diff <skill_id> <other_dir>   # 与外部目录的 SKILL.md 内容比对
  python scripts/skills_cli.py audit [--limit N] [--task TID] [--role ROLE]
  python scripts/skills_cli.py audit-export <out.csv>
  python scripts/skills_cli.py route "需求文本"
"""

from __future__ import annotations

import csv
import difflib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def cmd_list() -> int:
    from app.ai.skills.loader import get_skill_loader
    loader = get_skill_loader()
    rows = []
    for sid in loader.list_available():
        try:
            b = loader.load(sid)
            rows.append((sid, b.version, b.lang, len(b.prompts), len(b.examples), b.content_hash[:8]))
        except Exception as e:
            rows.append((sid, "ERR", "?", 0, 0, str(e)[:30]))
    print(f"{'skill_id':<32} {'ver':<10} {'lang':<5} {'prompts':<7} {'ex':<3} hash")
    for r in rows:
        print(f"{r[0]:<32} {r[1]:<10} {r[2]:<5} {r[3]:<7} {r[4]:<3} {r[5]}")
    return 0


def cmd_validate() -> int:
    from app.ai.skills.health import run_health_check
    rep = run_health_check()
    print(json.dumps(rep.as_dict(), ensure_ascii=False, indent=2))
    return 0 if rep.ok else 1


def cmd_show(skill_id: str) -> int:
    from app.ai.skills.loader import get_skill_loader, SkillNotFoundError
    try:
        b = get_skill_loader().load(skill_id)
    except SkillNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"=== {b.skill_id} v{b.version} ({b.lang}) ===")
    print(f"name: {b.name}")
    print(f"description: {b.description}")
    print(f"tags: {b.tags}")
    print(f"requires: {b.requires}")
    print(f"prompts ({len(b.prompts)}): {list(b.prompts.keys())}")
    print(f"examples ({len(b.examples)}): {[e.filename for e in b.examples]}")
    print(f"templates ({len(b.output_templates)}): {list(b.output_templates.keys())}")
    print(f"references ({len(b.references)}): {list(b.references.keys())}")
    print(f"overlays_applied: {b.overlays_applied}")
    print(f"content_hash: {b.content_hash}")
    print("\n----- primary prompt 预览（前 1500 字）-----")
    print(b.primary_prompt[:1500])
    return 0


def cmd_diff(skill_id: str, other_dir: str) -> int:
    from app.ai.skills.loader import get_skill_loader, SkillNotFoundError
    try:
        b = get_skill_loader().load(skill_id)
    except SkillNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    other = Path(other_dir).expanduser().resolve()
    if not other.is_dir():
        print(f"ERROR: {other} 不是目录", file=sys.stderr)
        return 2
    other_skill_md = other / "SKILL.md"
    if not other_skill_md.exists():
        print(f"ERROR: {other_skill_md} 不存在", file=sys.stderr)
        return 2
    a = (b.skill_path / "SKILL.md").read_text(encoding="utf-8")
    c = other_skill_md.read_text(encoding="utf-8")
    diff = list(difflib.unified_diff(
        a.splitlines(), c.splitlines(),
        fromfile=f"{skill_id}/SKILL.md (local)",
        tofile=str(other_skill_md),
        lineterm="",
    ))
    if not diff:
        print("无差异")
        return 0
    print("\n".join(diff))
    return 0


def cmd_audit(args: list[str]) -> int:
    from app.ai.skills.audit import init_audit_storage, query_persisted
    import asyncio
    asyncio.run(init_audit_storage())
    limit, offset, role, task = 50, 0, None, None
    i = 0
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1]); i += 2
        elif args[i] == "--offset" and i + 1 < len(args):
            offset = int(args[i + 1]); i += 2
        elif args[i] == "--role" and i + 1 < len(args):
            role = args[i + 1]; i += 2
        elif args[i] == "--task" and i + 1 < len(args):
            task = args[i + 1]; i += 2
        else:
            i += 1
    res = query_persisted(limit=limit, offset=offset, role=role, task_id=task)
    if not res.get("persisted"):
        print("审计表未启用（QA_SKILL_AUDIT_PERSIST=false 或未初始化）")
        return 1
    print(f"total={res['total']}  showing {len(res['items'])}")
    for it in res["items"]:
        print(f"[{it['ts']:.0f}] role={it['role']:<10} skill={it['skill_id']:<22} v{it['skill_version']:<6} task={it['task_id']} tk_est={it['prompt_tokens_est']} actual_p={it['prompt_tokens_actual']}")
    return 0


def cmd_audit_export(out_path: str) -> int:
    from app.ai.skills.audit import init_audit_storage, query_persisted
    import asyncio
    asyncio.run(init_audit_storage())
    res = query_persisted(limit=10**6, offset=0)
    if not res.get("persisted"):
        print("审计表未启用，无法导出")
        return 1
    items = res["items"]
    if not items:
        print("无记录")
        return 0
    fields = list(items[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for it in items:
            it = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in it.items()}
            w.writerow(it)
    print(f"已导出 {len(items)} 条 → {out_path}")
    return 0


def cmd_route(text: str) -> int:
    from app.ai.skills.discover import route_combined, filter_to_available
    from app.ai.skills.loader import get_skill_loader
    avail = get_skill_loader().list_available()
    r = route_combined(text or "", available_skills=avail)
    r = filter_to_available(r, avail)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd, args = argv[0], argv[1:]
    if cmd == "list":
        return cmd_list()
    if cmd == "validate":
        return cmd_validate()
    if cmd == "show" and args:
        return cmd_show(args[0])
    if cmd == "diff" and len(args) >= 2:
        return cmd_diff(args[0], args[1])
    if cmd == "audit":
        return cmd_audit(args)
    if cmd == "audit-export" and args:
        return cmd_audit_export(args[0])
    if cmd == "route" and args:
        return cmd_route(" ".join(args))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
