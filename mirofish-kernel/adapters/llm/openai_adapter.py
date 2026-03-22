"""
OpenAI LLM Adapter — Implements LLMProvider for OpenAI SDK-compatible APIs.

Works with: OpenAI, Azure OpenAI, Alibaba DashScope, DeepSeek,
any OpenAI-format API (vLLM, Ollama with OpenAI compat, etc.)

Includes: retry with exponential backoff for rate limits and timeouts.
"""

import os
import json
import re
import time
import logging
from typing import Dict, Any, List, Optional, AsyncIterator

from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger("mirofish.llm.openai")

_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))
_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "60"))
_RETRY_BASE = float(os.environ.get("LLM_RETRY_BASE_DELAY", "2"))


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
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=_TIMEOUT)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=_TIMEOUT)

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

        last_error = None
        for attempt in range(_MAX_RETRIES):
            t0 = time.time()
            try:
                response = self._client.chat.completions.create(**kwargs)
                latency = int((time.time() - t0) * 1000)
                content = response.choices[0].message.content or ""
                content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()

                tokens_in = getattr(response.usage, "prompt_tokens", 0) if response.usage else 0
                tokens_out = getattr(response.usage, "completion_tokens", 0) if response.usage else 0
                logger.debug(f"LLM call: {latency}ms, {tokens_in}+{tokens_out} tokens")

                return content

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                latency = int((time.time() - t0) * 1000)

                # Classify error
                err_str = str(e).lower()
                if "rate" in err_str or "429" in err_str:
                    wait = _RETRY_BASE * (3 ** attempt)
                    logger.warning(f"LLM rate limited — retry {attempt+1}/{_MAX_RETRIES} in {wait:.0f}s")
                    time.sleep(wait)
                    continue
                elif "timeout" in error_type.lower() or "timeout" in err_str:
                    wait = _RETRY_BASE * (2 ** attempt)
                    logger.warning(f"LLM timeout ({latency}ms) — retry {attempt+1}/{_MAX_RETRIES} in {wait:.0f}s")
                    time.sleep(wait)
                    continue
                elif "auth" in err_str or "401" in err_str:
                    logger.error(f"LLM auth failed: {e}")
                    raise
                else:
                    if attempt < _MAX_RETRIES - 1:
                        wait = _RETRY_BASE * (2 ** attempt)
                        logger.warning(f"LLM error ({error_type}) — retry {attempt+1}/{_MAX_RETRIES} in {wait:.0f}s: {e}")
                        time.sleep(wait)
                        continue
                    raise

        raise RuntimeError(f"LLM failed after {_MAX_RETRIES} attempts: {last_error}")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        for attempt in range(2):  # 1 retry for JSON parse failures
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            cleaned = response.strip()
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)
            cleaned = cleaned.strip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning(f"LLM returned invalid JSON — retrying with stricter prompt")
                    messages = messages + [{"role": "user", "content": "Your response was not valid JSON. Please respond with ONLY valid JSON, no explanation."}]
                    continue
                raise ValueError(f"Invalid JSON from LLM after retry: {cleaned[:200]}...")

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

    def ping(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Quick health check — send minimal request, return latency."""
        t0 = time.time()
        try:
            self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                timeout=timeout,
            )
            return {"status": "ok", "latency_ms": int((time.time() - t0) * 1000)}
        except Exception as e:
            err_str = str(e).lower()
            if "auth" in err_str or "401" in err_str:
                error_type = "auth_failed"
            elif "rate" in err_str or "429" in err_str:
                error_type = "rate_limited"
            elif "timeout" in err_str:
                error_type = "timeout"
            else:
                error_type = str(e)[:100]
            return {"status": "error", "error": error_type, "latency_ms": int((time.time() - t0) * 1000)}

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
