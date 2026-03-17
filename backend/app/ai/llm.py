import asyncio
from loguru import logger
from typing import List, Dict, Any, Optional
from app.core.config import settings
import litellm

class UniversalLLMClient:
    """
    Universal HTTP Client for Large Language Models using litellm.
    Supports any LLM on the market that provides an OpenAI-compatible `/v1/chat/completions` endpoint.
    """
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL.rstrip('/')
        self.model = settings.LLM_MODEL

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7, 
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Sends a chat completion request to the configured LLM API.
        """
        if not self.api_key:
            logger.warning("LLM_API_KEY is not set. The request will likely fail.")

        kwargs = {
            "model": self.model if "/" in self.model else f"openai/{self.model}",
            "messages": messages,
            "temperature": temperature,
            "api_key": self.api_key,
            "api_base": self.base_url,
        }
        
        # Add response_format parameter if specified
        if response_format:
            kwargs["response_format"] = response_format

        logger.debug(f"Sending LLM request via litellm | Model: {self.model} | Base: {self.base_url}")

        try:
            response = await litellm.acompletion(**kwargs)
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            else:
                logger.error(f"Unexpected response from LLM: {response}")
                return "Error: Unexpected response format from AI provider."
        except Exception as e:
            logger.error(f"Error occurred while calling LLM API via litellm: {e}")
            return f"Error: {str(e)}"

llm_client = UniversalLLMClient()
