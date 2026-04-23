import base64
from loguru import logger
from typing import List, Dict, Any, Optional
from app.core.config import settings
from openai import AsyncOpenAI


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


def get_last_usage() -> Optional[Dict[str, int]]:
    """读取当前 task 上下文最近一次 LLM 调用的真实 token usage。"""
    return last_usage_ctx.get()


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

        try:
            # Create client with override settings if provided
            if api_key_in_use or base_url_in_use:
                client = AsyncOpenAI(
                    api_key=api_key_in_use if api_key_in_use else "not-needed",
                    base_url=base_url_in_use if base_url_in_use else None
                )
            else:
                client = self.client

            logger.debug(
                f"Sending LLM request via OpenAI SDK | Model: {model_in_use} | Base: {base_url_in_use}"
            )

            is_reasoning = _is_reasoning_model(model_in_use)

            params: Dict[str, Any] = {
                "model": model_in_use,
                "messages": messages,
            }

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

            # Send request
            response = await client.chat.completions.create(**params)

            # 记录真实 usage（供 audit 回填）
            try:
                usage = getattr(response, "usage", None)
                if usage is not None:
                    last_usage_ctx.set({
                        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
                    })
                else:
                    last_usage_ctx.set(None)
            except Exception:
                last_usage_ctx.set(None)

            # Extract content from response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                return content or ""

            logger.error(f"Unexpected response from OpenAI: {response}")
            return "Error: Unexpected response format from AI provider."

        except Exception as e:
            logger.error(f"Error occurred while calling LLM via OpenAI SDK: {e}")
            return f"Error: {str(e)}"

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
