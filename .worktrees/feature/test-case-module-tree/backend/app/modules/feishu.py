import asyncio
import json
import re
import tempfile
import uuid
from typing import List, Dict, Any, Optional

from loguru import logger
from app.core.config import settings
from app.modules.mcp_docs import fetch_document_via_mcp


def _collect_text_from_obj(obj: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(obj, str):
        value = obj.strip()
        if value:
            texts.append(value)
        return texts
    if isinstance(obj, list):
        for item in obj:
            texts.extend(_collect_text_from_obj(item))
        return texts
    if isinstance(obj, dict):
        preferred_keys = ("raw_content", "text", "content", "title", "plain_text", "md_content", "markdown")
        for key in preferred_keys:
            if key in obj:
                texts.extend(_collect_text_from_obj(obj.get(key)))
        for value in obj.values():
            if isinstance(value, (dict, list)):
                texts.extend(_collect_text_from_obj(value))
        return texts
    return texts


def _parse_cli_json(stdout: str) -> dict:
    value = (stdout or "").strip()
    if not value:
        raise RuntimeError("飞书 CLI 输出为空")
    try:
        return json.loads(value)
    except Exception:
        start = value.find("{")
        end = value.rfind("}")
        if start >= 0 and end > start:
            return json.loads(value[start:end + 1])
        raise RuntimeError("飞书 CLI 输出不是合法 JSON")


async def _read_feishu_doc_via_cli(doc_url: str) -> str:
    identity = (settings.FEISHU_CLI_AS or "user").strip().lower()
    if identity not in {"user", "bot", "auto"}:
        identity = "user"
    cmd = [
        settings.FEISHU_CLI_BIN,
        "docs",
        "+fetch",
        "--doc",
        doc_url,
        "--format",
        "json",
        "--as",
        identity,
    ]
    if settings.FEISHU_CLI_PROFILE.strip():
        cmd.extend(["--profile", settings.FEISHU_CLI_PROFILE.strip()])

    logger.info("Feishu CLI fetch: {}", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=float(settings.FEISHU_CLI_TIMEOUT_SECONDS),
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("飞书 CLI 拉取文档超时")

    stdout = stdout_bytes.decode("utf-8", errors="ignore")
    stderr = stderr_bytes.decode("utf-8", errors="ignore")
    if proc.returncode != 0:
        raise RuntimeError(f"飞书 CLI 执行失败: {stderr or stdout}")

    payload = _parse_cli_json(stdout)
    texts = _collect_text_from_obj(payload)
    merged = "\n".join([t for t in texts if t.strip()])
    merged = merged.strip()
    if not merged:
        raise RuntimeError("飞书 CLI 返回中未提取到文本内容")
    return merged


async def read_feishu_doc(doc_url: str) -> str:
    """飞书模块 - 优先通过 Feishu CLI 读取，失败时回退 MCP"""
    if settings.FEISHU_USE_CLI:
        try:
            return await _read_feishu_doc_via_cli(doc_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Feishu CLI failed, fallback to MCP: {}", exc)

    return await fetch_document_via_mcp(
        provider="feishu",
        mcp_base_url=settings.FEISHU_MCP_BASE_URL,
        invoke_path=settings.FEISHU_MCP_INVOKE_PATH,
        tool_name=settings.FEISHU_MCP_TOOL_NAME,
        doc_url=doc_url,
        api_key=settings.FEISHU_MCP_API_KEY,
        timeout_seconds=settings.MCP_REQUEST_TIMEOUT_SECONDS,
    )

def _sanitize_mermaid_text(value: str, *, fallback: str = "未命名") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    # Mermaid mindmap plain node text: remove line breaks and brackets that easily break parsing.
    text = text.replace("\r", " ").replace("\n", " ")
    text = text.replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def _build_mindmap_mermaid(cases: List[Dict[str, Any]], title: str) -> str:
    root = _sanitize_mermaid_text(title, fallback="测试用例")
    module_map: dict[str, list[Dict[str, Any]]] = {}
    for item in cases:
        module = _sanitize_mermaid_text(item.get("module") or "通用", fallback="通用")
        module_map.setdefault(module, []).append(item)

    lines = [
        "mindmap",
        f"  root(({root}))",
    ]
    for module_name, module_cases in module_map.items():
        lines.append(f"    {module_name}")
        for item in module_cases:
            case_id = str(item.get("id") or "").strip()
            case_title = _sanitize_mermaid_text(item.get("title") or "未命名用例", fallback="未命名用例")
            prefix = f"用例{case_id} " if case_id else ""
            lines.append(f"      {prefix}{case_title}")

            priority = _sanitize_mermaid_text(item.get("priority") or "中", fallback="中")
            precondition = _sanitize_mermaid_text(item.get("precondition") or "无", fallback="无")
            lines.append(f"        优先级: {priority}")
            lines.append(f"        前置条件: {precondition}")

            steps = str(item.get("steps") or "").strip().splitlines()
            steps = [_sanitize_mermaid_text(step, fallback="") for step in steps if str(step).strip()]
            if steps:
                lines.append("        测试步骤")
                for idx, step in enumerate(steps[:8], start=1):
                    lines.append(f"          {idx}. {step}")

            expected_result = _sanitize_mermaid_text(item.get("expected_result") or "", fallback="")
            if expected_result:
                lines.append(f"        预期结果: {expected_result}")

    return "\n".join(lines).strip() + "\n"


def _extract_doc_url(payload: Any, fallback_url: str) -> str:
    if isinstance(payload, dict):
        for key in ("url", "doc_url", "open_url", "obj_url"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip().startswith("http"):
                return value.strip()
        for value in payload.values():
            found = _extract_doc_url(value, "")
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _extract_doc_url(item, "")
            if found:
                return found
    return fallback_url


def _extract_node(payload: Any) -> dict:
    if isinstance(payload, dict):
        node = payload.get("node")
        if isinstance(node, dict):
            return node
        data = payload.get("data")
        if isinstance(data, dict) and (
            isinstance(data.get("node_token"), str) or isinstance(data.get("obj_token"), str)
        ):
            return data
        for value in payload.values():
            found = _extract_node(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _extract_node(item)
            if found:
                return found
    return {}


def _parse_feishu_doc_url(doc_url: str) -> tuple[str, str]:
    value = (doc_url or "").strip()
    match = re.search(r"/(wiki|docx|doc|docs)/([A-Za-z0-9_-]+)", value)
    if not match:
        return "", ""
    return match.group(1), match.group(2)


async def _create_wiki_child_node(
    *,
    parent_token: str,
    title: str,
    identity: str,
    obj_type: str,
) -> tuple[str, str]:
    create_cmd = [
        settings.FEISHU_CLI_BIN,
        "wiki",
        "+node-create",
        "--parent-node-token",
        parent_token,
        "--obj-type",
        obj_type,
        "--title",
        title,
        "--as",
        identity,
    ]
    if settings.FEISHU_CLI_PROFILE.strip():
        create_cmd.extend(["--profile", settings.FEISHU_CLI_PROFILE.strip()])
    logger.info("Feishu CLI create child doc: {}", " ".join(create_cmd))
    create_proc = await asyncio.create_subprocess_exec(
        *create_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        create_stdout_bytes, create_stderr_bytes = await asyncio.wait_for(
            create_proc.communicate(),
            timeout=float(settings.FEISHU_CLI_TIMEOUT_SECONDS),
        )
    except asyncio.TimeoutError:
        create_proc.kill()
        raise RuntimeError("飞书 CLI 创建子文档超时")

    create_stdout = create_stdout_bytes.decode("utf-8", errors="ignore")
    create_stderr = create_stderr_bytes.decode("utf-8", errors="ignore")
    if create_proc.returncode != 0:
        raise RuntimeError(f"飞书 CLI 创建子文档失败: {create_stderr or create_stdout}")

    create_payload = _parse_cli_json(create_stdout)
    if not create_payload.get("ok", False):
        err = create_payload.get("error") or {}
        raise RuntimeError(f"飞书创建子文档失败: {err}")
    node = _extract_node(create_payload)
    node_token = str(node.get("node_token") or "").strip()
    if not node_token:
        raise RuntimeError("飞书创建子文档成功但未返回 node_token")
    child_doc_url = f"https://{(settings.FEISHU_DRIVE_DOMAIN or 'my.feishu.cn').strip()}/wiki/{node_token}"
    return node_token, child_doc_url


async def _append_blank_whiteboard(
    *,
    child_doc_url: str,
    identity: str,
) -> str:
    with tempfile.TemporaryDirectory(prefix="feishu-mindmap-") as tmp_dir:
        cmd = [
            settings.FEISHU_CLI_BIN,
            "docs",
            "+update",
            "--doc",
            child_doc_url,
            "--mode",
            "append",
            "--markdown",
            '<whiteboard type="blank"></whiteboard>',
            "--as",
            identity,
        ]
        if settings.FEISHU_CLI_PROFILE.strip():
            cmd.extend(["--profile", settings.FEISHU_CLI_PROFILE.strip()])

        logger.info("Feishu CLI write child doc: {}", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=tmp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(settings.FEISHU_CLI_TIMEOUT_SECONDS),
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("飞书 CLI 写入文档超时")

    stdout = stdout_bytes.decode("utf-8", errors="ignore")
    stderr = stderr_bytes.decode("utf-8", errors="ignore")
    if proc.returncode != 0:
        raise RuntimeError(f"{stderr or stdout}")

    payload = _parse_cli_json(stdout)
    if not payload.get("ok", False):
        err = payload.get("error") or {}
        raise RuntimeError(f"飞书写回失败: {err}")
    board_tokens = (((payload.get("data") or {}) if isinstance(payload, dict) else {}) or {}).get("board_tokens")
    if not isinstance(board_tokens, list) or not board_tokens:
        raise RuntimeError("飞书文档追加白板成功但未返回 board token")
    board_token = str(board_tokens[0] or "").strip()
    if not board_token:
        raise RuntimeError("飞书文档追加白板成功但 board token 为空")
    return board_token


async def _write_mermaid_to_whiteboard(
    *,
    board_token: str,
    mermaid: str,
    identity: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="feishu-mindmap-") as tmp_dir:
        mmd_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".mmd",
            prefix="mindmap-",
            encoding="utf-8",
            delete=False,
            dir=tmp_dir,
        )
        mmd_file.write(mermaid)
        mmd_file.flush()
        mmd_file.close()

        convert_cmd = [
            "npx",
            "-y",
            "@larksuite/whiteboard-cli@^0.1.0",
            "--to",
            "openapi",
            "-i",
            mmd_file.name,
            "--format",
            "json",
        ]
        logger.info("Whiteboard CLI convert mermaid: {}", " ".join(convert_cmd))
        convert_proc = await asyncio.create_subprocess_exec(
            *convert_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp_dir,
        )
        try:
            convert_stdout_bytes, convert_stderr_bytes = await asyncio.wait_for(
                convert_proc.communicate(),
                timeout=float(settings.FEISHU_CLI_TIMEOUT_SECONDS),
            )
        except asyncio.TimeoutError:
            convert_proc.kill()
            raise RuntimeError("Whiteboard CLI 转换 Mermaid 超时")

        convert_stdout = convert_stdout_bytes.decode("utf-8", errors="ignore")
        convert_stderr = convert_stderr_bytes.decode("utf-8", errors="ignore")
        if convert_proc.returncode != 0:
            raise RuntimeError(f"Whiteboard CLI 转换失败: {convert_stderr or convert_stdout}")

        update_cmd = [
            settings.FEISHU_CLI_BIN,
            "docs",
            "+whiteboard-update",
            "--whiteboard-token",
            board_token,
            "--overwrite",
            "--yes",
            "--as",
            identity,
            "--idempotent-token",
            f"task-{uuid.uuid4().hex[:24]}",
        ]
        if settings.FEISHU_CLI_PROFILE.strip():
            update_cmd.extend(["--profile", settings.FEISHU_CLI_PROFILE.strip()])
        logger.info("Feishu CLI whiteboard update: {}", " ".join(update_cmd))
        update_proc = await asyncio.create_subprocess_exec(
            *update_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp_dir,
        )
        try:
            update_stdout_bytes, update_stderr_bytes = await asyncio.wait_for(
                update_proc.communicate(input=convert_stdout_bytes),
                timeout=float(settings.FEISHU_CLI_TIMEOUT_SECONDS),
            )
        except asyncio.TimeoutError:
            update_proc.kill()
            raise RuntimeError("飞书白板写入超时")

    update_stdout = update_stdout_bytes.decode("utf-8", errors="ignore")
    update_stderr = update_stderr_bytes.decode("utf-8", errors="ignore")
    if update_proc.returncode != 0:
        raise RuntimeError(f"飞书白板写入失败: {update_stderr or update_stdout}")
    payload = _parse_cli_json(update_stdout)
    if not payload.get("ok", False):
        err = payload.get("error") or {}
        raise RuntimeError(f"飞书白板写回失败: {err}")


async def write_feishu_doc(
    doc_url: str,
    cases: List[Dict[str, Any]],
    *,
    title: str = "测试用例",
) -> str:
    """在需求文档下创建子文档，并把思维导图结构写入该新文档。"""
    if not settings.FEISHU_AUTO_WRITE_MINDMAP:
        return ""
    if not settings.FEISHU_USE_CLI:
        raise RuntimeError("FEISHU_USE_CLI=false，无法自动写回飞书文档")
    if not doc_url.strip():
        raise RuntimeError("飞书文档地址为空，无法写回")

    identity = (settings.FEISHU_CLI_AS or "user").strip().lower()
    if identity not in {"user", "bot", "auto"}:
        identity = "user"
    doc_type, token = _parse_feishu_doc_url(doc_url)
    if doc_type != "wiki" or not token:
        raise RuntimeError("当前仅支持 wiki 需求文档下自动创建测试用例子文档")

    # Whiteboard update currently requires board token and is best supported via docx container.
    obj_type = "docx"
    configured_obj_type = str(settings.FEISHU_WIKI_CHILD_OBJ_TYPE or "").strip().lower()
    if configured_obj_type and configured_obj_type != "docx":
        logger.warning("FEISHU_WIKI_CHILD_OBJ_TYPE={} ignored for whiteboard mode, use docx", configured_obj_type)

    _, child_doc_url = await _create_wiki_child_node(
        parent_token=token,
        title=title,
        identity=identity,
        obj_type=obj_type,
    )
    board_token = await _append_blank_whiteboard(
        child_doc_url=child_doc_url,
        identity=identity,
    )
    mermaid = _build_mindmap_mermaid(cases, title=title)
    await _write_mermaid_to_whiteboard(
        board_token=board_token,
        mermaid=mermaid,
        identity=identity,
    )
    return child_doc_url
