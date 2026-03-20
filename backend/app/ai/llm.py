from loguru import logger
from typing import List, Dict, Any, Optional
from app.core.config import settings
from openai import AsyncOpenAI

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

            # Prepare completion parameters
            params: Dict[str, Any] = {
                "model": model_in_use,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens is not None:
                params["max_tokens"] = max_tokens

            if top_p is not None:
                params["top_p"] = top_p

            if response_format:
                params["response_format"] = response_format

            # Send request
            response = await client.chat.completions.create(**params)

            # Extract content from response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                return content or ""

            logger.error(f"Unexpected response from OpenAI: {response}")
            return "Error: Unexpected response format from AI provider."

        except Exception as e:
            logger.error(f"Error occurred while calling LLM via OpenAI SDK: {e}")
            return f"Error: {str(e)}"

llm_client = UniversalLLMClient()
