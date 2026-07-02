"""GitHub Skill 导入器单元测试（URL 解析，无网络）。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.skills.github_importer import (
    GitHubSkillImportError,
    parse_github_skill_source,
    validate_skill_md_text,
)


def test_parse_github_tree_url() -> None:
    ref = parse_github_skill_source(
        "https://github.com/naodeng/awesome-qa-skills/tree/main/skills/zh/testing-types/api-test-pytest"
    )
    assert ref.owner == "naodeng"
    assert ref.repo == "awesome-qa-skills"
    assert ref.branch == "main"
    assert ref.skill_path == "skills/zh/testing-types/api-test-pytest"
    assert ref.skill_id == "api-test-pytest"


def test_parse_github_blob_skill_md_url() -> None:
    ref = parse_github_skill_source(
        "https://github.com/naodeng/awesome-qa-skills/blob/main/skills/zh/testing-types/testcase-writer-plus/SKILL.md"
    )
    assert ref.skill_id == "testcase-writer-plus"
    assert ref.skill_path == "skills/zh/testing-types/testcase-writer-plus"


def test_parse_skill_id_only() -> None:
    ref = parse_github_skill_source("requirements-analysis-plus")
    assert ref.owner == "naodeng"
    assert ref.repo == "awesome-qa-skills"
    assert ref.skill_id == "requirements-analysis-plus"
    assert ref.skill_path == ""
    assert ref.resolved_from == "skill_id_autodetect"


def test_parse_repo_path_shorthand() -> None:
    ref = parse_github_skill_source(
        "naodeng/awesome-qa-skills/main/skills/zh/testing-types/test-case-reviewer-plus"
    )
    assert ref.skill_id == "test-case-reviewer-plus"
    assert ref.skill_path.endswith("test-case-reviewer-plus")


def test_validate_skill_md() -> None:
    ok, msg = validate_skill_md_text("---\nname: x\ndescription: y\n---\nbody")
    assert ok and msg == "ok"
    bad, _ = validate_skill_md_text("# no frontmatter")
    assert not bad


def test_invalid_skill_id_raises() -> None:
    try:
        parse_github_skill_source("../evil")
        assert False, "should raise"
    except GitHubSkillImportError:
        pass
