"""
Anthropic LLM Adapter — Implements LLMProvider for Claude API.

Supports: Claude Opus, Sonnet, Haiku via the Anthropic Python SDK.
"""

import json
import re
from typing import Dict, Any, List, Optional, AsyncIterator


class AnthropicAdapter:
    """
    Anthropic SDK adapter for the LLMProvider interface.
    
    Maps kernel LLM calls to Claude's messages API.
    Handles system prompt extraction (Claude uses a separate system param).
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ):
        try:
            from anthropic import Anthropic, AsyncAnthropic
        except ImportError:
            raise ImportError(
                "anthropic package required: pip install anthropic"
            )
        
        self._api_key = api_key
        self._model = model
        self._client = Anthropic(api_key=api_key)
        self._async_client = AsyncAnthropic(api_key=api_key)
    
    def _extract_system(
        self, messages: List[Dict[str, str]]
    ) -> tuple:
        """
        Extract system message from messages list.
        Claude API takes system as a separate parameter.
        
        Returns: (system_str_or_None, remaining_messages)
        """
        system = None
        filtered = []
        for msg in messages:
            if msg.get("role") == "system":
                system = msg["content"]
            else:
                filtered.append(msg)
        return system, filtered
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        system, msgs = self._extract_system(messages)
        
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        
        response = self._client.messages.create(**kwargs)
        
        # Extract text from content blocks
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        
        return content.strip()
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        # Add JSON instruction to system prompt
        system, msgs = self._extract_system(messages)
        json_system = (system or "") + "\n\nRespond with valid JSON only. No markdown fences, no explanation."
        
        # Rebuild messages with enhanced system
        enhanced = [{"role": "system", "content": json_system}] + msgs
        
        response = self.chat(
            messages=enhanced,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Clean markdown fences
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON from Claude: {cleaned[:200]}...")
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        system, msgs = self._extract_system(messages)
        
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        
        async with self._async_client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
    
    def ping(self, timeout: float = 5.0) -> dict:
        """Quick health check."""
        import time
        t0 = time.time()
        try:
            self._client.messages.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return {"status": "ok", "latency_ms": int((time.time() - t0) * 1000)}
        except Exception as e:
            err_str = str(e).lower()
            error_type = "auth_failed" if "auth" in err_str else "timeout" if "timeout" in err_str else str(e)[:100]
            return {"status": "error", "error": error_type, "latency_ms": int((time.time() - t0) * 1000)}

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "anthropic"
