import pytest

from app.ai import ai
from app.services import file_service
from app.services import test_case_generation_service


def test_default_task_name_rules():
    assert file_service.default_task_name("local", "需求说明-v1.docx", None) == "需求说明-v1.docx"
    assert file_service.default_task_name("feishu", None, "https://my.feishu.cn/wiki/abc") == file_service.ONLINE_TASK_NAME_PLACEHOLDER
    assert file_service.default_task_name("dingtalk", None, "https://alidocs.dingtalk.com/i/abc") == file_service.ONLINE_TASK_NAME_PLACEHOLDER
    assert file_service.default_task_name("manual", None, None) == "手动需求"


def test_normalize_cases_enforces_module_split_and_title_prefix():
    cases = ai._normalize_cases(
        [
            {
                "id": 1,
                "module": "通用",
                "title": "正常流程-灰度开关配置",
                "precondition": "无",
                "steps": "进入灰度配置页面并开启总开关",
                "expected_result": "保存成功",
                "priority": "高",
            },
            {
                "id": 2,
                "module": "",
                "title": "",
                "precondition": "无",
                "steps": "进入收益分析看板并筛选日期",
                "expected_result": "图表正确展示",
                "priority": "中",
            },
        ]
    )
    assert cases[0]["title"].startswith("验证")
    assert cases[0]["module"] == "灰度控制"
    assert cases[1]["title"].startswith("验证")
    assert cases[1]["module"] == "收益分析"


@pytest.mark.asyncio
async def test_upload_task_ingests_requirement_into_kb(monkeypatch):
    called = {
        "create_task": False,
        "update_phase_payload": None,
        "ingest_args": None,
    }

    async def fake_create_task(**kwargs):
        called["create_task"] = True
        return "task-test-001"

    async def fake_update_phase(task_id, phase, status, data):
        called["update_phase_payload"] = {
            "task_id": task_id,
            "phase": phase,
            "status": status,
            "data": data,
        }

    def fake_ingest_requirement_document(**kwargs):
        called["ingest_args"] = kwargs
        return {"task_id": kwargs["task_id"], "chunk_count": 2, "chunk_ids": ["task-test-001:1", "task-test-001:2"]}

    monkeypatch.setattr(file_service.task_manager, "create_task", fake_create_task)
    monkeypatch.setattr(file_service.task_manager, "update_phase", fake_update_phase)
    monkeypatch.setattr(file_service, "ingest_requirement_document", fake_ingest_requirement_document)

    result = await file_service.create_uploaded_task(
        source_type="local",
        task_name="上传入库测试",
        doc_url=None,
        submitter="tester",
        file_name="requirement.txt",
        file_content="用户登录并支持短信验证".encode("utf-8"),
    )

    assert called["create_task"] is True
    assert result["task_id"] == "task-test-001"
    assert called["ingest_args"] is not None
    assert called["ingest_args"]["task_id"] == "task-test-001"
    assert called["ingest_args"]["source_type"] == "local"

    phase_payload = called["update_phase_payload"]
    assert phase_payload is not None
    assert phase_payload["phase"] == "upload"
    assert phase_payload["status"] == "completed"
    assert phase_payload["data"]["knowledge_base"]["ingested_chunks"] == 2


@pytest.mark.asyncio
async def test_generate_test_cases_allows_cold_start_without_history(monkeypatch):
    captured_messages = {}

    async def fake_load_role_config():
        return {
            "generation": {
                "prompt": "你是测试工程师",
                "temperature": 0.1,
                "model": "fake-model",
                "api_key": None,
                "base_url": None,
                "max_tokens": None,
                "top_p": None,
            }
        }

    async def fake_chat(**kwargs):
        captured_messages["messages"] = kwargs.get("messages") or []
        return (
            '{"cases":[{"id":1,"module":"登录","title":"冷启动生成","precondition":"无",'
            '"steps":"1. 输入账号密码","expected_result":"登录成功","priority":"中"}]}'
        )

    monkeypatch.setattr(ai, "_load_role_config", fake_load_role_config)
    monkeypatch.setattr(ai.llm_client, "chat", fake_chat)

    cases = await ai.generate_test_cases("覆盖正常/异常/边界", "")
    assert len(cases) == 1
    user_message = captured_messages["messages"][1]["content"]
    assert "当前没有历史相似需求可参考" in user_message


@pytest.mark.asyncio
async def test_generate_test_cases_uses_history_context_when_available(monkeypatch):
    captured_messages = {}

    async def fake_load_role_config():
        return {
            "generation": {
                "prompt": "你是测试工程师",
                "temperature": 0.1,
                "model": "fake-model",
                "api_key": None,
                "base_url": None,
                "max_tokens": None,
                "top_p": None,
            }
        }

    async def fake_chat(**kwargs):
        captured_messages["messages"] = kwargs.get("messages") or []
        return (
            '{"cases":[{"id":2,"module":"登录","title":"历史增强生成","precondition":"无",'
            '"steps":"1. 连续输错5次","expected_result":"账号锁定","priority":"高"}]}'
        )

    monkeypatch.setattr(ai, "_load_role_config", fake_load_role_config)
    monkeypatch.setattr(ai.llm_client, "chat", fake_chat)

    history_context = "历史命中：连续失败5次锁定并触发二次验证"
    cases = await ai.generate_test_cases("覆盖登录安全策略", history_context)
    assert len(cases) == 1
    user_message = captured_messages["messages"][1]["content"]
    assert "历史相似需求" in user_message
    assert history_context in user_message


@pytest.mark.asyncio
async def test_update_review_cases_ingests_only_adopted_cases_into_kb(monkeypatch):
    called = {
        "ingest_kwargs": None,
        "manual_review_payload": None,
    }

    async def fake_get_task_or_404(task_id):
        return {
            "id": task_id,
            "task_name": "登录需求",
            "source_type": "local",
            "file_name": "req.md",
            "phases": {"review": {"data": {"review": {}}}},
        }

    async def fake_update_phase(task_id, phase, status, data):
        if phase == "manual_review" and status == "completed":
            called["manual_review_payload"] = data

    async def fake_set_task_mindmap(task_id, mindmap):
        return True

    async def fake_set_task_decision(task_id, **kwargs):
        return True

    async def fake_set_task_status(task_id, status, status_text=None):
        return True

    async def fake_get_task(task_id):
        return {"id": task_id, "status": "completed"}

    def fake_ingest_adopted_test_cases(**kwargs):
        called["ingest_kwargs"] = kwargs
        return {"task_id": kwargs["task_id"], "case_count": len(kwargs["cases"]), "case_ids": ["c1"]}

    monkeypatch.setattr(test_case_generation_service.task_service, "get_task_or_404", fake_get_task_or_404)
    monkeypatch.setattr(test_case_generation_service.task_service, "update_phase", fake_update_phase)
    monkeypatch.setattr(test_case_generation_service.task_service, "set_task_mindmap", fake_set_task_mindmap)
    monkeypatch.setattr(test_case_generation_service.task_service, "set_task_decision", fake_set_task_decision)
    monkeypatch.setattr(test_case_generation_service.task_service, "set_task_status", fake_set_task_status)
    monkeypatch.setattr(test_case_generation_service.task_service, "get_task", fake_get_task)
    monkeypatch.setattr(test_case_generation_service, "ingest_adopted_test_cases", fake_ingest_adopted_test_cases)

    payload = [
        {
            "id": 1,
            "module": "登录",
            "title": "成功登录",
            "precondition": "账号存在",
            "steps": "输入正确账号密码",
            "expected_result": "进入首页",
            "priority": "高",
            "adoption_status": "accepted",
        },
        {
            "id": 2,
            "module": "登录",
            "title": "失败登录",
            "precondition": "账号存在",
            "steps": "输入错误密码",
            "expected_result": "提示错误",
            "priority": "中",
            "adoption_status": "rejected",
        },
    ]

    result = await test_case_generation_service.update_review_cases("task-review-001", payload)
    assert result["adopted_count"] == 1
    assert result["rejected_count"] == 1

    ingest_kwargs = called["ingest_kwargs"]
    assert ingest_kwargs is not None
    assert ingest_kwargs["task_id"] == "task-review-001"
    assert len(ingest_kwargs["cases"]) == 1
    assert ingest_kwargs["cases"][0]["title"] == "成功登录"
    assert ingest_kwargs["source_type"] == "local"
    assert ingest_kwargs["file_name"] == "req.md"

    manual_review_payload = called["manual_review_payload"]
    assert manual_review_payload is not None
    assert manual_review_payload["knowledge_base"]["adopted_cases_ingested"] == 1


@pytest.mark.asyncio
async def test_submit_generation_task_uses_doc_placeholder_name_for_online_sources(monkeypatch):
    called = {"task_name": None}

    async def fake_create_task(**kwargs):
        called["task_name"] = kwargs.get("task_name")
        return "task-feishu-001"

    async def fake_start_generation_task(**kwargs):
        return {"task_id": kwargs["task_id"], "task_status": "任务已启动"}

    monkeypatch.setattr(test_case_generation_service.task_service, "create_task", fake_create_task)
    monkeypatch.setattr(test_case_generation_service, "start_generation_task", fake_start_generation_task)

    result = await test_case_generation_service.submit_generation_task(
        background_tasks=None,
        source_type="feishu",
        task_name="",
        doc_url="https://my.feishu.cn/wiki/abc123",
        manual_title=None,
        manual_description=None,
        related_project=None,
        submitter="tester",
        file=None,
    )

    assert result["task_id"] == "task-feishu-001"
    assert called["task_name"] == file_service.ONLINE_TASK_NAME_PLACEHOLDER
