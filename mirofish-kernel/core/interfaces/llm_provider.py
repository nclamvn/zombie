"""
LLM Provider Protocol
Abstracts away the LLM backend — OpenAI, Anthropic, local models, etc.
"""

from typing import Protocol, Dict, Any, List, Optional, AsyncIterator, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """
    Abstract LLM provider interface.
    
    Any LLM backend (OpenAI, Anthropic, Ollama, vLLM, etc.) must implement this.
    The kernel NEVER imports openai/anthropic directly — only through adapters.
    """
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            response_format: Optional format constraint (e.g., {"type": "json_object"})
            
        Returns:
            Model response text (cleaned of any think tags, markdown fences, etc.)
        """
        ...
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Send a chat request expecting JSON response.
        
        Args:
            messages: Chat messages
            temperature: Lower default for structured output
            max_tokens: Maximum tokens
            
        Returns:
            Parsed JSON dict
            
        Raises:
            ValueError: If response is not valid JSON
        """
        ...
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion response.
        
        Yields:
            Token strings as they arrive
        """
        ...
    
    @property
    def model_name(self) -> str:
        """Current model identifier."""
        ...
    
    @property
    def provider_name(self) -> str:
        """Provider identifier (e.g., 'openai', 'anthropic', 'ollama')."""
        ...
