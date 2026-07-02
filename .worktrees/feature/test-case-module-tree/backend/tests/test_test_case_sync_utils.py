"""测试用例同步上下文解析与落库模块命名。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.requirement_model import Requirement
from app.services import test_case_generation_service
from app.services.test_case_sync_utils import (
    coerce_optional_int,
    normalize_ai_module,
    resolve_case_sync_context,
    strip_html_tags,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        (12, 12),
        ("34", 34),
        ("bad", None),
    ],
)
def test_coerce_optional_int(raw, expected):
    assert coerce_optional_int(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, "默认模块"),
        ("", "默认模块"),
        ("  登录  ", "登录"),
        ("<p>项目申报</p>", "项目申报"),
    ],
)
def test_normalize_ai_module(raw, expected):
    assert normalize_ai_module(raw) == expected


def test_strip_html_tags():
    assert strip_html_tags("<p>注册 / 登录</p>") == "注册 / 登录"
    assert strip_html_tags("plain") == "plain"


@pytest.mark.asyncio
async def test_resolve_case_sync_context_without_requirement():
    db = AsyncMock()
    module, project_id, req_id = await resolve_case_sync_context(
        db,
        requirement_id=None,
        project_id=5,
        ai_module="登录校验",
    )
    assert module == "登录校验"
    assert project_id == 5
    assert req_id is None
    db.get.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_case_sync_context_with_requirement():
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(title="用户登录", project_id=10)
    module, project_id, req_id = await resolve_case_sync_context(
        db,
        requirement_id="7",
        project_id=None,
        ai_module="登录校验",
    )
    assert module == "登录校验"
    assert project_id == 10
    assert req_id == 7
    db.get.assert_awaited_once_with(Requirement, 7)


@pytest.mark.asyncio
async def test_resolve_case_sync_context_requirement_not_found():
    db = AsyncMock()
    db.get.return_value = None
    module, project_id, req_id = await resolve_case_sync_context(
        db,
        requirement_id=99,
        project_id=3,
        ai_module="子模块",
    )
    assert module == "子模块"
    assert project_id == 3
    assert req_id == 99


@pytest.mark.asyncio
async def test_persist_adopted_cases_uses_requirement_module(monkeypatch):
    captured: dict = {}

    async def fake_resolve(db, *, requirement_id, project_id, ai_module):
        captured["calls"] = captured.get("calls", []) + [
            {"requirement_id": requirement_id, "project_id": project_id, "ai_module": ai_module}
        ]
        return "登录校验", 10, 7

    monkeypatch.setattr(
        test_case_generation_service,
        "resolve_case_sync_context",
        fake_resolve,
    )

    class FakeScalars:
        def first(self):
            return None

    class FakeResult:
        def scalars(self):
            return FakeScalars()

    db = AsyncMock()
    db.execute.return_value = FakeResult()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    cases = [
        {
            "title": "成功登录",
            "module": "登录校验",
            "priority": "high",
            "steps": "输入账号密码",
            "expected_result": "进入首页",
        }
    ]
    result = await test_case_generation_service._persist_adopted_cases_to_library(
        db,
        task_id="task-001",
        cases=cases,
        project_id=None,
        requirement_id="7",
    )

    assert result["count"] == 1
    assert result["created"] == 1
    assert len(captured["calls"]) == 1
    assert captured["calls"][0]["requirement_id"] == 7
    assert captured["calls"][0]["ai_module"] == "登录校验"

    added_case = db.add.call_args[0][0]
    assert added_case.module == "登录校验"
    assert added_case.project_id == 10
    assert added_case.requirement_id == 7


@pytest.mark.asyncio
async def test_batch_adopt_uses_resolve_case_sync_context(monkeypatch):
    from app.api.endpoints import test_cases as test_cases_endpoint

    captured: list[dict] = []

    async def fake_resolve(db, *, requirement_id, project_id, ai_module):
        captured.append({"requirement_id": requirement_id, "ai_module": ai_module})
        return "子模块B", 1, 2

    monkeypatch.setattr(test_cases_endpoint, "resolve_case_sync_context", fake_resolve)

    class FakeScalars:
        def first(self):
            return None

    class FakeResult:
        def scalars(self):
            return FakeScalars()

    db = AsyncMock()
    db.execute.return_value = FakeResult()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    body = {
        "cases": [
            {
                "title": "用例1",
                "module": "子模块B",
                "requirement_id": 2,
                "project_id": 1,
                "task_id": "t1",
                "steps": [],
            }
        ]
    }
    resp = await test_cases_endpoint.batch_adopt(body, db=db)
    assert resp["code"] == 0
    assert resp["data"]["count"] == 1
    assert len(captured) == 1
    added_case = db.add.call_args[0][0]
    assert added_case.module == "子模块B"
    assert added_case.requirement_id == 2
