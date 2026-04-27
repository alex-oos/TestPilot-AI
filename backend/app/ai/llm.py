import asyncio
import base64
import random
from loguru import logger
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from openai import AsyncOpenAI

from app.ai import llm_cache, llm_concurrency
from app.ai.llm_errors import LLMError, LLMErrorCode, classify_exception


def _is_reasoning_model(model_name: str) -> bool:
    """识别 OpenAI 新一代推理/旗舰模型 (gpt-5*, o1*, o3*, o4*)。
    这类模型使用 `max_completion_tokens` 而非 `max_tokens`，
    并且只支持默认的 temperature=1。
    """
    if not model_name:
        return False
    name = model_name.lower().strip()
    return (
        name.startswith("gpt-5")
        or name.startswith("gpt5")
        or name.startswith("o1")
        or name.startswith("o3")
        or name.startswith("o4")
    )


import contextvars

# 最近一次 chat 调用的 usage（contextvar，跨 await 安全）
last_usage_ctx: contextvars.ContextVar[Optional[Dict[str, int]]] = contextvars.ContextVar(
    "llm_last_usage", default=None,
)

# 最近一次 chat 调用的元信息（cache_hit / retries / error_code / model）
last_call_meta_ctx: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "llm_last_meta", default=None,
)


def get_last_usage() -> Optional[Dict[str, int]]:
    """读取当前 task 上下文最近一次 LLM 调用的真实 token usage。"""
    return last_usage_ctx.get()


def get_last_call_meta() -> Optional[Dict[str, Any]]:
    """读取最近一次 LLM 调用的元信息（用于审计回填）。"""
    return last_call_meta_ctx.get()


async def _retry_chat(client: AsyncOpenAI, params: Dict[str, Any]) -> Tuple[Any, int]:
    """重试 + 指数退避；只对 retryable 错误重试。返回 (response, attempts)。"""
    max_attempts = max(1, int(getattr(settings, "LLM_RETRY_MAX", 3) or 1))
    base = float(getattr(settings, "LLM_RETRY_BASE_DELAY", 1.0) or 1.0)
    cap = float(getattr(settings, "LLM_RETRY_MAX_DELAY", 30.0) or 30.0)
    last_exc: Optional[LLMError] = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = await client.chat.completions.create(**params)
            return resp, attempt
        except Exception as exc:  # noqa
            err = classify_exception(exc)
            last_exc = err
            if not err.retryable or attempt == max_attempts:
                raise err
            delay = min(cap, base * (2 ** (attempt - 1)))
            delay = delay * (0.7 + 0.6 * random.random())  # jitter ±30%
            logger.warning(
                "[llm-retry] code={} attempt={}/{} delay={:.2f}s msg={}",
                err.code.value, attempt, max_attempts, delay, err.message[:120],
            )
            await asyncio.sleep(delay)
    if last_exc:
        raise last_exc
    raise LLMError(LLMErrorCode.UNKNOWN, "unreachable retry path")


class UniversalLLMClient:
    """
    Universal Client for Large Language Models using OpenAI SDK.
    Supports any LLM on the market that provides an OpenAI-compatible `/v1/chat/completions` endpoint.
    """
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL.rstrip('/')
        self.model = settings.LLM_MODEL

        # Initialize OpenAI client
        api_key = self.api_key if self.api_key else "not-needed"
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url if self.base_url else None
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> str:
        """
        Sends a chat completion request using OpenAI SDK.
        """
        model_in_use = model or self.model
        api_key_in_use = api_key or self.api_key
        base_url_in_use = (base_url or self.base_url).rstrip("/")

        # ---- 构造调用参数 ----
        if (api_key is not None and api_key != self.api_key) or (
            base_url is not None and base_url != self.base_url
        ):
            client = AsyncOpenAI(
                api_key=api_key_in_use if api_key_in_use else "not-needed",
                base_url=base_url_in_use if base_url_in_use else None
            )
        else:
            client = self.client

        is_reasoning = _is_reasoning_model(model_in_use)
        params: Dict[str, Any] = {"model": model_in_use, "messages": messages}
        if not is_reasoning:
            params["temperature"] = temperature
            if top_p is not None:
                params["top_p"] = top_p
        if max_tokens is not None:
            if is_reasoning:
                params["max_completion_tokens"] = max_tokens
            else:
                params["max_tokens"] = max_tokens
        if response_format:
            params["response_format"] = response_format

        # ---- 缓存命中？ ----
        cache_key = llm_cache.make_cache_key(
            model=model_in_use,
            messages=messages,
            temperature=temperature if not is_reasoning else None,
            response_format=response_format,
        )
        cached = llm_cache.get(cache_key)
        if cached is not None:
            usage = cached.get("usage") or {}
            last_usage_ctx.set({
                "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or 0),
                "total_tokens": int(usage.get("total_tokens") or 0),
            })
            last_call_meta_ctx.set({
                "model": model_in_use,
                "cache_hit": True,
                "retries": 0,
                "error_code": LLMErrorCode.OK.value,
            })
            logger.info("[llm-cache] HIT model={} key={}", model_in_use, cache_key[:12])
            return cached.get("content") or ""

        # ---- 真正调用：信号量 + 重试 ----
        try:
            async with llm_concurrency.slot():
                logger.debug(
                    "Sending LLM request | Model: {} | Base: {}",
                    model_in_use, base_url_in_use,
                )
                response, attempts = await _retry_chat(client, params)

            # 记录真实 usage
            usage_data: Dict[str, int] = {}
            try:
                usage = getattr(response, "usage", None)
                if usage is not None:
                    usage_data = {
                        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
                    }
                    last_usage_ctx.set(usage_data)
                else:
                    last_usage_ctx.set(None)
            except Exception:
                last_usage_ctx.set(None)

            content = ""
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content or ""
            if not content:
                last_call_meta_ctx.set({
                    "model": model_in_use,
                    "cache_hit": False,
                    "retries": max(0, attempts - 1),
                    "error_code": LLMErrorCode.EMPTY_RESPONSE.value,
                })
                logger.error("Unexpected empty response from LLM: {}", response)
                return "Error: Unexpected response format from AI provider."

            last_call_meta_ctx.set({
                "model": model_in_use,
                "cache_hit": False,
                "retries": max(0, attempts - 1),
                "error_code": LLMErrorCode.OK.value,
            })
            llm_cache.put(cache_key, model=model_in_use, content=content, usage=usage_data)
            return content

        except LLMError as e:
            last_call_meta_ctx.set({
                "model": model_in_use,
                "cache_hit": False,
                "retries": 0,
                "error_code": e.code.value,
            })
            logger.error("[llm-error] code={} status={} msg={}", e.code.value, e.status_code, e.message)
            return e.to_legacy_string()
        except Exception as e:  # 兜底
            err = classify_exception(e)
            last_call_meta_ctx.set({
                "model": model_in_use,
                "cache_hit": False,
                "retries": 0,
                "error_code": err.code.value,
            })
            logger.error("Error occurred while calling LLM: {}", err.message)
            return err.to_legacy_string()

    async def extract_text_from_image(
        self,
        *,
        image_bytes: bytes,
        file_name: str,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        model_in_use = model or self.model
        api_key_in_use = api_key or self.api_key
        base_url_in_use = (base_url or self.base_url).rstrip("/")

        suffix = (file_name.rsplit(".", 1)[-1] if "." in file_name else "").lower()
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "bmp": "image/bmp",
            "gif": "image/gif",
        }
        mime_type = mime_map.get(suffix, "image/png")
        data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        vision_prompt = (
            prompt
            or "请提取图片中的全部可读文本，按原有结构输出。如果包含表格，请按行列清晰输出。"
        )

        try:
            if api_key_in_use or base_url_in_use:
                client = AsyncOpenAI(
                    api_key=api_key_in_use if api_key_in_use else "not-needed",
                    base_url=base_url_in_use if base_url_in_use else None,
                )
            else:
                client = self.client

            is_reasoning = _is_reasoning_model(model_in_use)
            vision_params: Dict[str, Any] = {
                "model": model_in_use,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": vision_prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
            }
            if is_reasoning:
                vision_params["max_completion_tokens"] = max_tokens or 2000
            else:
                vision_params["temperature"] = 0
                vision_params["max_tokens"] = max_tokens or 2000

            response = await client.chat.completions.create(**vision_params)
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            return "Error: OCR response content is empty."
        except Exception as e:
            logger.error(f"Error occurred while calling vision OCR via OpenAI SDK: {e}")
            return f"Error: {str(e)}"

llm_client = UniversalLLMClient()
