"""LLM 错误码归一化。

把上游 SDK / HTTP / network 抛的各种异常统一映射成 `LLMError`，
便于上层做"是否重试 / 是否计费 / 是否报警"决策，并写入审计 `error_code`。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LLMErrorCode(str, Enum):
    OK = "ok"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    AUTH_FAILED = "auth_failed"
    INVALID_REQUEST = "invalid_request"
    CONTEXT_TOO_LONG = "context_too_long"
    NETWORK = "network"
    EMPTY_RESPONSE = "empty_response"
    UNKNOWN = "unknown"


@dataclass
class LLMError(Exception):
    code: LLMErrorCode
    message: str
    raw: str = ""
    status_code: int = 0
    retryable: bool = False

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_legacy_string(self) -> str:
        """与旧调用方对齐的字符串返回（旧 chat 失败返回 'Error: ...'）。"""
        return f"Error: [{self.code.value}] {self.message}"


def classify_exception(exc: Exception) -> LLMError:
    """把任意 Exception 归一化成 LLMError。"""
    raw = repr(exc)
    msg = str(exc) or raw
    status = int(getattr(exc, "status_code", 0) or 0)
    name = type(exc).__name__.lower()
    lower_msg = msg.lower()

    # ---- OpenAI / httpx 常见类型识别 ----
    if any(k in name for k in ("ratelimit", "toomany")):
        return LLMError(LLMErrorCode.RATE_LIMITED, msg, raw, status or 429, retryable=True)
    if "ratelimit" in lower_msg or "rate limit" in lower_msg or status == 429:
        return LLMError(LLMErrorCode.RATE_LIMITED, msg, raw, status or 429, retryable=True)

    if "timeout" in name or "timeout" in lower_msg:
        return LLMError(LLMErrorCode.TIMEOUT, msg, raw, status, retryable=True)

    if any(k in name for k in ("connection", "network")) or "connection" in lower_msg:
        return LLMError(LLMErrorCode.NETWORK, msg, raw, status, retryable=True)

    if "authentication" in name or "auth" in lower_msg or status in (401, 403):
        return LLMError(LLMErrorCode.AUTH_FAILED, msg, raw, status or 401, retryable=False)

    if "context" in lower_msg and ("length" in lower_msg or "too long" in lower_msg or "tokens" in lower_msg):
        return LLMError(LLMErrorCode.CONTEXT_TOO_LONG, msg, raw, status or 400, retryable=False)

    if status and 500 <= status < 600:
        return LLMError(LLMErrorCode.SERVER_ERROR, msg, raw, status, retryable=True)
    if "internal" in lower_msg and "error" in lower_msg:
        return LLMError(LLMErrorCode.SERVER_ERROR, msg, raw, status or 500, retryable=True)

    if status and 400 <= status < 500:
        return LLMError(LLMErrorCode.INVALID_REQUEST, msg, raw, status, retryable=False)

    return LLMError(LLMErrorCode.UNKNOWN, msg, raw, status, retryable=False)
