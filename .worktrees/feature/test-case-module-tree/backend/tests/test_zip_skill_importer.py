"""ZIP Skill 导入器单元测试（无网络）。"""

from __future__ import annotations

import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.skills.zip_importer import ZipSkillImportError, analyze_zip_skill

SKILL_MD = """---
name: demo-skill
description: demo skill for zip import test
version: 1.0.0
lang: zh
---

# Demo
"""


def _make_zip(entries: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in entries.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            zf.writestr(path, content)
    return buf.getvalue()


def test_analyze_wrapped_skill_folder() -> None:
    data = _make_zip({
        "my-skill/SKILL.md": SKILL_MD,
        "my-skill/prompts/main.md": "# prompt",
        "my-skill/examples/sample.md": "sample",
    })
    analysis = analyze_zip_skill(data, archive_name="ignored.zip")
    assert analysis.skill_id == "my-skill"
    assert analysis.file_count == 3
    assert "prompts/main.md" in analysis.sample_files


def test_analyze_root_skill_uses_archive_name() -> None:
    data = _make_zip({
        "SKILL.md": SKILL_MD,
        "prompts/main.md": "# prompt",
    })
    analysis = analyze_zip_skill(data, archive_name="custom-skill.zip")
    assert analysis.skill_id == "custom-skill"
    assert analysis.file_count == 2


def test_analyze_deep_path() -> None:
    data = _make_zip({
        "skills/zh/testing-types/deep-skill/SKILL.md": SKILL_MD,
        "skills/zh/testing-types/deep-skill/prompts/p.md": "p",
    })
    analysis = analyze_zip_skill(data)
    assert analysis.skill_id == "deep-skill"
    assert analysis.skill_root == "skills/zh/testing-types/deep-skill"


def test_missing_skill_md_raises() -> None:
    data = _make_zip({"readme.md": "no skill"})
    try:
        analyze_zip_skill(data)
        assert False, "should raise"
    except ZipSkillImportError as exc:
        assert "SKILL.md" in str(exc)


def test_skill_id_override() -> None:
    data = _make_zip({"foo/SKILL.md": SKILL_MD})
    analysis = analyze_zip_skill(data, skill_id_override="renamed-skill")
    assert analysis.skill_id == "renamed-skill"
