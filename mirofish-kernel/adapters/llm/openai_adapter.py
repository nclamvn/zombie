"""
OpenAI LLM Adapter — Implements LLMProvider for OpenAI SDK-compatible APIs.

Works with: OpenAI, Azure OpenAI, Alibaba DashScope, DeepSeek, 
any OpenAI-format API (vLLM, Ollama with OpenAI compat, etc.)
"""

import json
import re
from typing import Dict, Any, List, Optional, AsyncIterator

from openai import OpenAI, AsyncOpenAI


class OpenAIAdapter:
    """
    OpenAI SDK adapter for the LLMProvider interface.
    
    Supports any API that follows the OpenAI chat completions format.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        
        # Strip think tags (common in some models like MiniMax, DeepSeek)
        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        
        # Clean markdown code fences
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON from LLM: {cleaned[:200]}...")
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        response = await self._async_client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def provider_name(self) -> str:
        if "dashscope" in self._base_url:
            return "alibaba_dashscope"
        if "azure" in self._base_url:
            return "azure_openai"
        if "deepseek" in self._base_url:
            return "deepseek"
        return "openai"
