from loguru import logger
from typing import List, Dict, Any, Optional
from app.core.config import settings
import httpx

class UniversalLLMClient:
    """
    Universal HTTP Client for Large Language Models.
    Supports any LLM on the market that provides an OpenAI-compatible `/v1/chat/completions` endpoint.
    """
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL.rstrip('/')
        self.model = settings.LLM_MODEL

    async def _fetch_available_model(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Optional[str]:
        """Fetch first non-embedding model from /models."""
        base = (base_url or self.base_url).rstrip("/")
        endpoint = f"{base}/models"
        headers = {"Content-Type": "application/json"}
        key = api_key if api_key is not None else self.api_key
        if key:
            headers["Authorization"] = f"Bearer {key}"
        resp = await client.get(endpoint, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data") or []
        for item in models:
            model_id = (item or {}).get("id")
            if not model_id:
                continue
            lower = model_id.lower()
            if "embed" in lower or "embedding" in lower:
                continue
            return model_id
        return None

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
        Sends a chat completion request to OpenAI-compatible LLM API.
        """
        api_key_in_use = self.api_key if api_key is None else api_key
        base_url_in_use = (base_url or self.base_url).rstrip("/")
        if not api_key_in_use:
            logger.warning("LLM_API_KEY is not set. Will continue for local providers like LM Studio.")

        endpoint = f"{base_url_in_use}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key_in_use:
            headers["Authorization"] = f"Bearer {api_key_in_use}"

        model_in_use = model or self.model
        last_error = ""

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for attempt in range(2):
                    payload: Dict[str, Any] = {
                        "model": model_in_use,
                        "messages": messages,
                        "temperature": temperature,
                    }
                    if max_tokens is not None:
                        payload["max_tokens"] = max_tokens
                    if top_p is not None:
                        payload["top_p"] = top_p
                    if response_format:
                        payload["response_format"] = response_format

                    logger.debug(
                        f"Sending LLM request via OpenAI-compatible API | Model: {model_in_use} | Base: {base_url_in_use}"
                    )

                    try:
                        resp = await client.post(endpoint, json=payload, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()
                        choices = data.get("choices") or []
                        if choices:
                            message = choices[0].get("message") or {}
                            return message.get("content") or ""
                        logger.error(f"Unexpected response from LLM: {data}")
                        return "Error: Unexpected response format from AI provider."
                    except httpx.HTTPStatusError as e:
                        status_code = e.response.status_code
                        body = e.response.text
                        last_error = f"HTTP {status_code}: {body}"
                        logger.error(f"LLM HTTP error: {last_error}")

                        # Auto-recover: if configured model is invalid for current LM Studio session,
                        # fetch available models and retry once with first non-embedding model.
                        if status_code == 400 and attempt == 0:
                            fallback = await self._fetch_available_model(
                                client,
                                base_url=base_url_in_use,
                                api_key=api_key_in_use,
                            )
                            if fallback and fallback != model_in_use:
                                logger.warning(
                                    f"Configured model '{model_in_use}' unavailable, retrying with '{fallback}'"
                                )
                                model_in_use = fallback
                                self.model = fallback
                                continue
                        break
                    except Exception as e:
                        last_error = str(e)
                        logger.error(f"Error occurred while calling OpenAI-compatible LLM API: {e}")
                        break
        except Exception as e:
            last_error = str(e)
            logger.error(f"LLM client initialization/call failed: {e}")

        return f"Error: {last_error or 'LLM request failed'}"

llm_client = UniversalLLMClient()
