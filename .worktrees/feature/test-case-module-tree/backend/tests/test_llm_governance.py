"""LLM 治理（重试/缓存/成本/错误码/并发）单元测试。

直接 `python tests/test_llm_governance.py` 即可。
不发起真实 LLM 请求；mock AsyncOpenAI 的 chat.completions.create。
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}  -- {detail}")


def section(t: str) -> None:
    print(f"\n=== {t} ===")


# ---------------- 1. 错误码归一化 ----------------
section("1. llm_errors.classify_exception")
from app.ai.llm_errors import LLMError, LLMErrorCode, classify_exception


class _RateLimitErr(Exception):
    status_code = 429


class _AuthErr(Exception):
    status_code = 401


class _ServerErr(Exception):
    status_code = 502


class _TimeoutErr(Exception):
    pass

class _ConnErr(Exception):
    pass


_TimeoutErr.__name__ = "APITimeoutError"
_ConnErr.__name__ = "APIConnectionError"

err_rl = classify_exception(_RateLimitErr("rate limit reached"))
check("rate limit -> RATE_LIMITED", err_rl.code == LLMErrorCode.RATE_LIMITED)
check("rate limit retryable=True", err_rl.retryable is True)

err_auth = classify_exception(_AuthErr("invalid api key"))
check("401 -> AUTH_FAILED", err_auth.code == LLMErrorCode.AUTH_FAILED)
check("auth retryable=False", err_auth.retryable is False)

err_5xx = classify_exception(_ServerErr("502 bad gateway"))
check("502 -> SERVER_ERROR", err_5xx.code == LLMErrorCode.SERVER_ERROR)
check("server retryable=True", err_5xx.retryable is True)

err_to = classify_exception(_TimeoutErr("request timeout"))
check("timeout name -> TIMEOUT", err_to.code == LLMErrorCode.TIMEOUT)

err_ctx = classify_exception(Exception("This model's maximum context length is 8192 tokens."))
check("context too long", err_ctx.code == LLMErrorCode.CONTEXT_TOO_LONG)

err_unk = classify_exception(Exception("strange exotic thing"))
check("未知 -> UNKNOWN", err_unk.code == LLMErrorCode.UNKNOWN)


# ---------------- 2. 成本核算 ----------------
section("2. llm_pricing.calc_cost_usd")
from app.ai import llm_pricing

c = llm_pricing.calc_cost_usd(model="gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
check("gpt-4o-mini 总价 = 0.75 USD", abs(c["total_cost"] - 0.75) < 1e-6, str(c))

c2 = llm_pricing.calc_cost_usd(model="未知模型", prompt_tokens=1000, completion_tokens=1000)
check("未知模型成本=0（fallback）", c2["total_cost"] == 0.0, str(c2))

c3 = llm_pricing.calc_cost_usd(model="gpt-4o-2024-11-20", prompt_tokens=1_000_000, completion_tokens=0)
check("gpt-4o 前缀模糊匹配", abs(c3["prompt_cost"] - 2.50) < 1e-6, str(c3))


# ---------------- 3. 缓存 ----------------
section("3. llm_cache 内存 + SQLite")
from app.ai import llm_cache
llm_cache.init_cache_storage()

key = llm_cache.make_cache_key(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "hello"}],
    temperature=0.7,
    response_format=None,
)
key2 = llm_cache.make_cache_key(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "hello"}],
    temperature=0.7,
    response_format=None,
)
check("相同输入产出相同 key", key == key2)

llm_cache.put(key, model="gpt-4o-mini", content="cached-content",
              usage={"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12})
hit = llm_cache.get(key)
check("缓存命中", hit is not None and hit.get("content") == "cached-content")

# 第二次调用 stats 命中数 +1
_ = llm_cache.get(key)
st = llm_cache.stats()
check("stats.hits ≥ 2", st["hits"] >= 2, str(st))
check("stats.puts ≥ 1", st["puts"] >= 1)
check("stats.enabled true", st["enabled"] is True)
check("stats.mem_size ≥ 1", st["mem_size"] >= 1)


# ---------------- 4. 并发信号量 ----------------
section("4. llm_concurrency.slot")
from app.ai import llm_concurrency
from app.core.config import settings


async def _run_concurrency():
    held = []

    async def worker(i):
        async with llm_concurrency.slot():
            held.append(i)
            await asyncio.sleep(0.05)

    await asyncio.gather(*(worker(i) for i in range(settings.LLM_MAX_CONCURRENCY * 2)))


asyncio.run(_run_concurrency())
st_c = llm_concurrency.stats()
check("concurrency 峰值 ≤ max", st_c["peak"] <= settings.LLM_MAX_CONCURRENCY,
      f"peak={st_c['peak']} max={st_c['max']}")
check("总持有 ≥ 8", st_c["total_holds"] >= settings.LLM_MAX_CONCURRENCY * 2)
check("current 归零", st_c["current"] == 0)


# ---------------- 5. UniversalLLMClient.chat 集成测试（mock） ----------------
section("5. UniversalLLMClient.chat：缓存 / 重试 / 错误处理")

from app.ai.llm import UniversalLLMClient, get_last_call_meta


class _FakeChoice:
    def __init__(self, content):
        self.message = types.SimpleNamespace(content=content)


class _FakeResp:
    def __init__(self, content, usage=None):
        self.choices = [_FakeChoice(content)]
        self.usage = types.SimpleNamespace(
            prompt_tokens=(usage or {}).get("prompt_tokens", 10),
            completion_tokens=(usage or {}).get("completion_tokens", 5),
            total_tokens=(usage or {}).get("total_tokens", 15),
        )


class _FakeCompletions:
    def __init__(self, behavior):
        self._behavior = behavior  # callable(call_no) -> _FakeResp | raise
        self._call = 0

    async def create(self, **kwargs):
        self._call += 1
        return self._behavior(self._call, kwargs)


class _FakeClient:
    def __init__(self, behavior):
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(behavior))


async def _test_chat_cache_and_retry():
    client = UniversalLLMClient()

    # 5.1 cache hit：第二次同样请求不会触达 API
    api_calls = {"count": 0}

    def beh_ok(call, kwargs):
        api_calls["count"] += 1
        return _FakeResp("hello-once")

    client.client = _FakeClient(beh_ok)
    out1 = await client.chat(
        messages=[{"role": "user", "content": "你好_test_cache"}],
        temperature=0.7,
        model="gpt-4o-mini",
    )
    out2 = await client.chat(
        messages=[{"role": "user", "content": "你好_test_cache"}],
        temperature=0.7,
        model="gpt-4o-mini",
    )
    check("第一次返回真实内容", out1 == "hello-once")
    check("第二次命中缓存（API 调用数=1）", api_calls["count"] == 1, str(api_calls))
    meta2 = get_last_call_meta() or {}
    check("第二次 meta.cache_hit=True", meta2.get("cache_hit") is True)

    # 5.2 retry：先抛 5xx，第二次成功
    state = {"call": 0}

    def beh_retry(call, kwargs):
        state["call"] = call
        if call == 1:
            class _E(Exception):
                status_code = 503
            e = _E("server temporarily unavailable")
            raise e
        return _FakeResp("ok-after-retry")

    client.client = _FakeClient(beh_retry)
    out3 = await client.chat(
        messages=[{"role": "user", "content": "请重试_test"}],
        temperature=0.7,
        model="gpt-4o-mini",
    )
    check("失败后重试成功", out3 == "ok-after-retry")
    check("发生 1 次重试", state["call"] == 2)
    meta3 = get_last_call_meta() or {}
    check("meta.retries=1", meta3.get("retries") == 1, str(meta3))
    check("meta.error_code=ok", meta3.get("error_code") == "ok")

    # 5.3 不可重试错误：401
    def beh_auth(call, kwargs):
        class _E(Exception):
            status_code = 401
        raise _E("invalid api key")

    client.client = _FakeClient(beh_auth)
    out4 = await client.chat(
        messages=[{"role": "user", "content": "权限_test"}],
        temperature=0.7,
        model="gpt-4o-mini",
    )
    check("auth 错误返回 Error: 字符串", isinstance(out4, str) and out4.startswith("Error:"))
    meta4 = get_last_call_meta() or {}
    check("meta.error_code=auth_failed", meta4.get("error_code") == "auth_failed")


if __name__ == "__main__":
    asyncio.run(_test_chat_cache_and_retry())
    print(f"\n=== LLM 治理测试结果 ===")
    print(f"通过 {PASS} / 失败 {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
else:
    # pytest 兼容：作为单个 test 函数暴露
    def test_llm_governance_all() -> None:
        asyncio.run(_test_chat_cache_and_retry())
        assert FAIL == 0, f"LLM 治理测试失败 {FAIL} 项"
