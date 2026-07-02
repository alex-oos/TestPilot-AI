from app.core.config import settings
from app.modules.mcp_docs import fetch_document_via_mcp

async def read_dingtalk_doc(doc_url: str) -> str:
    """钉钉模块 - 通过 MCP 服务读取并解析文档"""
    return await fetch_document_via_mcp(
        provider="dingtalk",
        mcp_base_url=settings.DINGTALK_MCP_BASE_URL,
        invoke_path=settings.DINGTALK_MCP_INVOKE_PATH,
        tool_name=settings.DINGTALK_MCP_TOOL_NAME,
        doc_url=doc_url,
        api_key=settings.DINGTALK_MCP_API_KEY,
        timeout_seconds=settings.MCP_REQUEST_TIMEOUT_SECONDS,
    )
