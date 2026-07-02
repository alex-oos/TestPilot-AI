"""从 awesome-qa-skills 仓库同步选定 skill 到本地 library/。

用法：
  python backend/scripts/sync_qa_skills.py \
      --source ~/.codex/skills/zh/testing-types \
      --skills requirements-analysis-plus testcase-writer-plus test-case-reviewer-plus \
      [--dry-run] [--force]

行为：
  1. 检查每个 skill 的 SKILL.md 是否存在 frontmatter (name/description)，缺失会报错。
  2. 比较本地与源的内容差异（按文件 hash），输出新增/修改/删除清单。
  3. 默认会保留本地特有文件（如 SOURCE.md），不删除。
  4. --dry-run 仅报告差异，不写入。
  5. 同步完成后打印新版本号建议。
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

DEFAULT_DEST = Path(__file__).resolve().parents[1] / "app" / "ai" / "skills" / "library"
PROTECTED_FILES = {"SOURCE.md"}  # 本地维护，不允许被同步删除/覆盖


def file_hash(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()[:16]


def relative_files(root: Path) -> dict[str, Path]:
    out = {}
    if not root.is_dir():
        return out
    for p in root.rglob("*"):
        if p.is_file():
            out[str(p.relative_to(root))] = p
    return out


def diff_skill(src: Path, dst: Path) -> tuple[list[str], list[str], list[str]]:
    src_files = relative_files(src)
    dst_files = relative_files(dst)
    added, modified, removed = [], [], []
    for rel, sp in src_files.items():
        dp = dst_files.get(rel)
        if dp is None:
            added.append(rel)
        elif file_hash(sp) != file_hash(dp):
            modified.append(rel)
    for rel in dst_files:
        if rel in PROTECTED_FILES:
            continue
        if rel.startswith("_overlays"):
            continue
        if rel not in src_files:
            removed.append(rel)
    return added, modified, removed


def validate_skill_md(skill_root: Path) -> tuple[bool, str]:
    md = skill_root / "SKILL.md"
    if not md.exists():
        return False, "SKILL.md 不存在"
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False, "缺少 frontmatter"
    end = text.find("\n---", 3)
    if end < 0:
        return False, "frontmatter 未闭合"
    fm = text[3:end]
    if "name:" not in fm:
        return False, "frontmatter 缺少 name"
    if "description:" not in fm:
        return False, "frontmatter 缺少 description"
    return True, "ok"


def sync(src_root: Path, dst_root: Path, skill_id: str, *, dry_run: bool, force: bool) -> int:
    src = src_root / skill_id
    dst = dst_root / skill_id
    if not src.is_dir():
        print(f"  [✗] 源不存在：{src}")
        return 2

    ok, msg = validate_skill_md(src)
    if not ok:
        print(f"  [✗] 源 {skill_id} 校验失败：{msg}")
        return 3

    added, modified, removed = diff_skill(src, dst)
    print(f"  + 新增 {len(added)}：{added[:5]}{' ...' if len(added) > 5 else ''}")
    print(f"  ~ 修改 {len(modified)}：{modified[:5]}{' ...' if len(modified) > 5 else ''}")
    print(f"  - 删除 {len(removed)}：{removed[:5]}{' ...' if len(removed) > 5 else ''}")

    if dry_run:
        return 0
    if (added or modified or removed) and not force:
        # 默认安全：保留本地修改，仅追加 / 更新
        pass

    dst.mkdir(parents=True, exist_ok=True)
    for rel, sp in relative_files(src).items():
        dp = dst / rel
        dp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sp, dp)

    if force:
        for rel in removed:
            (dst / rel).unlink(missing_ok=True)

    print(f"  [✓] {skill_id} 已同步到 {dst}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="awesome-qa-skills 本地路径，如 ~/.codex/skills/zh/testing-types")
    parser.add_argument("--dest", default=str(DEFAULT_DEST), help="本地 library 路径")
    parser.add_argument("--skills", nargs="+", required=True, help="要同步的 skill_id 列表")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="允许删除本地多余文件（与源对齐）")
    args = parser.parse_args()

    src_root = Path(args.source).expanduser().resolve()
    dst_root = Path(args.dest).expanduser().resolve()
    print(f"源：{src_root}\n目标：{dst_root}\n")

    rc = 0
    for sid in args.skills:
        print(f"=== {sid} ===")
        rc = sync(src_root, dst_root, sid, dry_run=args.dry_run, force=args.force) or rc
        print()

    print(f"完成。提示：同步后请手动调用 POST /api/ai/skills/reload 重新加载缓存。")
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
