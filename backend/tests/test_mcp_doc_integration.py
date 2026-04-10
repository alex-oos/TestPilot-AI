import pytest

from app.modules import dingtalk, feishu, mcp_docs


def test_extract_text_from_mcp_response_supports_nested_result():
    payload = {
        "result": {
            "content": [
                {"type": "text", "text": "第一段需求"},
                {"type": "text", "text": "第二段需求"},
            ]
        }
    }
    text = mcp_docs._extract_text_from_mcp_response(payload)
    assert "第一段需求" in text
    assert "第二段需求" in text


@pytest.mark.asyncio
async def test_fetch_document_via_mcp_parses_response(monkeypatch):
    called = {"url": "", "json": None, "headers": None}

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"text": "来自MCP的需求文档内容"}}

    class _FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            called["url"] = url
            called["json"] = json
            called["headers"] = headers
            return _FakeResponse()

    monkeypatch.setattr(mcp_docs.httpx, "AsyncClient", _FakeAsyncClient)

    text = await mcp_docs.fetch_document_via_mcp(
        provider="feishu",
        mcp_base_url="http://127.0.0.1:19001",
        invoke_path="/invoke",
        tool_name="read_feishu_doc",
        doc_url="https://feishu.cn/docx/abc",
        api_key="token-x",
        timeout_seconds=10,
    )

    assert text == "来自MCP的需求文档内容"
    assert called["url"] == "http://127.0.0.1:19001/invoke"
    assert called["json"]["tool"] == "read_feishu_doc"
    assert called["json"]["arguments"]["url"] == "https://feishu.cn/docx/abc"
    assert called["headers"]["Authorization"] == "Bearer token-x"


@pytest.mark.asyncio
async def test_feishu_and_dingtalk_modules_read_via_mcp(monkeypatch):
    calls = []

    async def fake_fetch_document_via_mcp(**kwargs):
        calls.append(kwargs)
        return f"ok-{kwargs['provider']}"

    monkeypatch.setattr(feishu, "fetch_document_via_mcp", fake_fetch_document_via_mcp)
    monkeypatch.setattr(dingtalk, "fetch_document_via_mcp", fake_fetch_document_via_mcp)
    monkeypatch.setattr(feishu.settings, "FEISHU_USE_CLI", False)

    monkeypatch.setattr(feishu.settings, "FEISHU_MCP_BASE_URL", "http://mcp-feishu")
    monkeypatch.setattr(feishu.settings, "FEISHU_MCP_INVOKE_PATH", "/invoke")
    monkeypatch.setattr(feishu.settings, "FEISHU_MCP_TOOL_NAME", "read_feishu_doc")
    monkeypatch.setattr(feishu.settings, "FEISHU_MCP_API_KEY", "feishu-key")
    monkeypatch.setattr(feishu.settings, "MCP_REQUEST_TIMEOUT_SECONDS", 15)

    monkeypatch.setattr(dingtalk.settings, "DINGTALK_MCP_BASE_URL", "http://mcp-dingtalk")
    monkeypatch.setattr(dingtalk.settings, "DINGTALK_MCP_INVOKE_PATH", "/invoke")
    monkeypatch.setattr(dingtalk.settings, "DINGTALK_MCP_TOOL_NAME", "read_dingtalk_doc")
    monkeypatch.setattr(dingtalk.settings, "DINGTALK_MCP_API_KEY", "dingtalk-key")
    monkeypatch.setattr(dingtalk.settings, "MCP_REQUEST_TIMEOUT_SECONDS", 15)

    feishu_text = await feishu.read_feishu_doc("https://feishu.cn/docx/123")
    dingtalk_text = await dingtalk.read_dingtalk_doc("https://alidocs.dingtalk.com/i/xyz")

    assert feishu_text == "ok-feishu"
    assert dingtalk_text == "ok-dingtalk"
    assert len(calls) == 2
    assert calls[0]["provider"] == "feishu"
    assert calls[1]["provider"] == "dingtalk"


@pytest.mark.asyncio
async def test_feishu_read_prefers_cli(monkeypatch):
    async def fake_cli(doc_url: str):
        assert doc_url == "https://feishu.cn/docx/abc"
        return "cli-doc-content"

    async def fake_mcp(**kwargs):
        raise AssertionError("Should not call MCP when CLI succeeds")

    monkeypatch.setattr(feishu.settings, "FEISHU_USE_CLI", True)
    monkeypatch.setattr(feishu, "_read_feishu_doc_via_cli", fake_cli)
    monkeypatch.setattr(feishu, "fetch_document_via_mcp", fake_mcp)

    text = await feishu.read_feishu_doc("https://feishu.cn/docx/abc")
    assert text == "cli-doc-content"


@pytest.mark.asyncio
async def test_feishu_read_fallback_to_mcp_when_cli_fails(monkeypatch):
    async def fake_cli(doc_url: str):
        raise RuntimeError("cli failed")

    async def fake_mcp(**kwargs):
        assert kwargs["provider"] == "feishu"
        return "mcp-fallback-content"

    monkeypatch.setattr(feishu.settings, "FEISHU_USE_CLI", True)
    monkeypatch.setattr(feishu, "_read_feishu_doc_via_cli", fake_cli)
    monkeypatch.setattr(feishu, "fetch_document_via_mcp", fake_mcp)

    text = await feishu.read_feishu_doc("https://feishu.cn/docx/abc")
    assert text == "mcp-fallback-content"


def test_parse_feishu_doc_url_supports_underscore_token():
    doc_type, token = feishu._parse_feishu_doc_url("https://my.feishu.cn/wiki/AbC_123-xYz")
    assert doc_type == "wiki"
    assert token == "AbC_123-xYz"


@pytest.mark.asyncio
async def test_write_feishu_doc_creates_docx_and_updates_whiteboard(monkeypatch):
    calls = []

    class _FakeProc:
        def __init__(self, stdout_text: str, returncode: int = 0):
            self._stdout = stdout_text
            self._stderr = ""
            self.returncode = returncode

        async def communicate(self, input=None):
            return self._stdout.encode("utf-8"), self._stderr.encode("utf-8")

        def kill(self):
            return None

    async def fake_create_subprocess_exec(*cmd, **kwargs):
        calls.append(list(cmd))
        if "wiki" in cmd and "+node-create" in cmd:
            return _FakeProc(
                '{"ok":true,"data":{"node_token":"node_token_123","obj_type":"docx"}}'
            )
        if "docs" in cmd and "+update" in cmd:
            return _FakeProc(
                '{"ok":true,"data":{"board_tokens":["board_token_123"]}}'
            )
        if "docs" in cmd and "+whiteboard-update" in cmd:
            return _FakeProc('{"ok":true,"data":{"deleted_nodes_num":"0"}}')
        if cmd and cmd[0] == "npx":
            return _FakeProc('{"code":0,"data":{"to":"openapi","result":{"nodes":[]}}}')
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(feishu.settings, "FEISHU_AUTO_WRITE_MINDMAP", True)
    monkeypatch.setattr(feishu.settings, "FEISHU_USE_CLI", True)
    monkeypatch.setattr(feishu.settings, "FEISHU_CLI_BIN", "lark-cli")
    monkeypatch.setattr(feishu.settings, "FEISHU_CLI_PROFILE", "")
    monkeypatch.setattr(feishu.settings, "FEISHU_CLI_AS", "user")
    monkeypatch.setattr(feishu.settings, "FEISHU_CLI_TIMEOUT_SECONDS", 10)
    monkeypatch.setattr(feishu.settings, "FEISHU_DRIVE_DOMAIN", "my.feishu.cn")
    monkeypatch.setattr(feishu.settings, "FEISHU_WIKI_CHILD_OBJ_TYPE", "mindnote")
    monkeypatch.setattr(feishu.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    output_url = await feishu.write_feishu_doc(
        doc_url="https://my.feishu.cn/wiki/PARENT_NODE_001",
        cases=[{"id": 1, "module": "登录", "title": "成功登录", "steps": "输入账号密码", "expected_result": "成功"}],
        title="登录需求测试用例",
    )

    assert output_url == "https://my.feishu.cn/wiki/node_token_123"
    assert len(calls) == 4
    create_cmd = calls[0]
    assert "--obj-type" in create_cmd
    assert create_cmd[create_cmd.index("--obj-type") + 1] == "docx"
    update_cmd = next(cmd for cmd in calls if "docs" in cmd and "+whiteboard-update" in cmd)
    assert "--whiteboard-token" in update_cmd
    assert update_cmd[update_cmd.index("--whiteboard-token") + 1] == "board_token_123"


@pytest.mark.asyncio
async def test_write_feishu_doc_raise_when_whiteboard_update_fails(monkeypatch):
    calls = []

    class _FakeProc:
        def __init__(self, stdout_text: str, stderr_text: str = "", returncode: int = 0):
            self._stdout = stdout_text
            self._stderr = stderr_text
            self.returncode = returncode

        async def communicate(self, input=None):
            return self._stdout.encode("utf-8"), self._stderr.encode("utf-8")

        def kill(self):
            return None

    async def fake_create_subprocess_exec(*cmd, **kwargs):
        calls.append(list(cmd))
        if "wiki" in cmd and "+node-create" in cmd:
            return _FakeProc('{"ok":true,"data":{"node_token":"docx_node"}}')
        if "docs" in cmd and "+update" in cmd:
            return _FakeProc('{"ok":true,"data":{"board_tokens":["board_token_002"]}}')
        if cmd and cmd[0] == "npx":
            return _FakeProc('{"code":0,"data":{"to":"openapi","result":{"nodes":[]}}}')
        if "docs" in cmd and "+whiteboard-update" in cmd:
            return _FakeProc('{"ok":false}', stderr_text="record missing", returncode=1)
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(feishu.settings, "FEISHU_AUTO_WRITE_MINDMAP", True)
    monkeypatch.setattr(feishu.settings, "FEISHU_USE_CLI", True)
    monkeypatch.setattr(feishu.settings, "FEISHU_CLI_BIN", "lark-cli")
    monkeypatch.setattr(feishu.settings, "FEISHU_CLI_PROFILE", "")
    monkeypatch.setattr(feishu.settings, "FEISHU_CLI_AS", "user")
    monkeypatch.setattr(feishu.settings, "FEISHU_CLI_TIMEOUT_SECONDS", 10)
    monkeypatch.setattr(feishu.settings, "FEISHU_DRIVE_DOMAIN", "my.feishu.cn")
    monkeypatch.setattr(feishu.settings, "FEISHU_WIKI_CHILD_OBJ_TYPE", "mindnote")
    monkeypatch.setattr(feishu.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    with pytest.raises(RuntimeError):
        await feishu.write_feishu_doc(
            doc_url="https://my.feishu.cn/wiki/PARENT_NODE_002",
            cases=[{"id": 1, "module": "灰度控制", "title": "验证灰度开关", "steps": "开启总开关", "expected_result": "成功"}],
            title="灰度需求测试用例",
        )

    create_obj_types = [cmd[cmd.index("--obj-type") + 1] for cmd in calls if "wiki" in cmd and "+node-create" in cmd]
    assert create_obj_types == ["docx"]
