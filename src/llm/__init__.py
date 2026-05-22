"""LLM module for multi-agent data analysis system.

Supports three backends:
- Ollama (local models)
- OpenAI API
- Claude API (Anthropic)
"""

from .config import LLMConfig, AVAILABLE_MODELS, BACKEND_NAMES
from .llm_client import LLMClient, LLMError, LLMConnectionError

__all__ = [
    "LLMConfig",
    "LLMClient",
    "LLMError",
    "LLMConnectionError",
    "AVAILABLE_MODELS",
    "BACKEND_NAMES",
]
