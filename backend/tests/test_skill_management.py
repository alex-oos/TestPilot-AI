"""Skill 管理中心：角色配置、导出、删除相关单元测试。"""

from __future__ import annotations

import io
import os
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.role_config import _pick_role_skill_id, _normalize_role
from app.ai.skills.loader import SkillLoader
from app.ai.skills.protected import PROTECTED_SKILL_IDS, is_protected_skill
from app.ai.skills.role_skill_config import (
    list_skill_references,
    pick_qa_skills_enabled,
    pick_role_skill_enabled,
    resolve_effective_skill_id,
)
from app.ai.skills.zip_exporter import ZipSkillExporter


def test_resolve_effective_skill_id_config_priority() -> None:
    """config > env > catalog_default。"""
    cfg = {
        "skill_configs": [
            {"role": "analysis", "skill_id": "from-config", "enabled": True},
        ],
    }
    sid, source = resolve_effective_skill_id(cfg, "analysis")
    assert sid == "from-config"
    assert source == "config"


def test_resolve_effective_skill_id_disabled_falls_back() -> None:
    """禁用角色配置时回退 env/catalog，不使用绑定的 skill_id。"""
    cfg = {
        "skill_configs": [
            {"role": "generation", "skill_id": "blocked-skill", "enabled": False},
        ],
    }
    sid, _source = resolve_effective_skill_id(cfg, "generation")
    assert sid != "blocked-skill"


def test_chinese_role_name_normalization() -> None:
    """中文角色名应归一化为 pipeline 角色。"""
    cfg = {
        "skill_configs": [
            {"role": "用例编写", "skill_id": "zh-gen-skill", "enabled": True},
        ],
    }
    assert _normalize_role("用例编写") == "generation"
    assert _pick_role_skill_id(cfg, "generation") == "zh-gen-skill"
    assert pick_role_skill_enabled(cfg, "generation") is True


def test_pick_qa_skills_enabled_config_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """配置中心 qa_skills_enabled 优先于环境变量。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "USE_QA_SKILLS", True)
    assert pick_qa_skills_enabled({"qa_skills_enabled": False}) is False
    assert pick_qa_skills_enabled({}) is True


def test_list_skill_references_only_enabled() -> None:
    """仅 enabled 的角色绑定计入引用。"""
    cfg = {
        "skill_configs": [
            {"role": "analysis", "skill_id": "shared-skill", "enabled": True},
            {"role": "review", "skill_id": "shared-skill", "enabled": False},
        ],
    }
    refs = list_skill_references(cfg, "shared-skill")
    assert len(refs) == 1
    assert refs[0]["role"] == "analysis"


def test_protected_skill_ids() -> None:
    """内置 Skill 不可删除。"""
    assert is_protected_skill("requirements-analysis-plus")
    assert is_protected_skill("discover-testing")
    assert not is_protected_skill("my-custom-skill")
    assert "requirements-analysis-plus" in PROTECTED_SKILL_IDS


def test_zip_exporter_roundtrip(tmp_path: Path) -> None:
    """导出 ZIP 应包含 skill 目录内容。"""
    skill_id = "tmp-export-skill"
    skill_dir = tmp_path / skill_id
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: tmp\ndescription: d\n---\nbody", encoding="utf-8")
    (skill_dir / "prompts").mkdir()
    (skill_dir / "prompts" / "primary.md").write_text("hello", encoding="utf-8")

    loader = SkillLoader(tmp_path)
    data, filename = ZipSkillExporter(loader).export_bytes(skill_id)
    assert filename == f"{skill_id}.zip"

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert f"{skill_id}/SKILL.md" in names
        assert f"{skill_id}/prompts/primary.md" in names
