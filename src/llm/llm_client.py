"""
LLM Client - Supports ONE active backend at a time.

Backends: ollama | openai | claude
Configuration: config/llm_config.yaml
Credentials: config/llm_credentials.yaml
"""

from pathlib import Path
from typing import Optional, Dict, Any

from .config import LLMConfig


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMConnectionError(LLMError):
    """Raised when connection to LLM fails."""
    pass


class LLMClient:
    """
    Unified LLM client for a single active backend.

    Configuration is loaded from config/llm_config.yaml.
    Use interactive menu for first-time setup.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize LLM client.

        Args:
            config: Optional LLMConfig instance (created if not provided)
        """
        self.config = config or LLMConfig()
        self.reload_config()

    def reload_config(self):
        """Reload configuration from disk."""
        self._config_data = self.config.load_config()
        self.backend = self._config_data.get("backend")
        
        if not self.backend:
            raise LLMError("LLM is not configured in configuration.")

        # Get model for active backend
        backend_config = self._config_data.get(self.backend, {})
        self.model = backend_config.get("model")
        
        if not self.model:
            raise LLMError("LLM model is not configured.")

        self._client = None

    def _get_client(self):
        """Lazy-load the appropriate client for the active backend."""
        if self._client is None:
            backend_config = self._config_data.get(self.backend, {})

            if self.backend in ("ollama", "ollama_paid"):
                try:
                    from ollama import Client
                    host = backend_config.get("host", "http://localhost:11434")
                    if not host or host == "N/A":
                        host = "http://localhost:11434"

                    # For ollama_paid, the API key is mandatory. For ollama, it's optional.
                    api_key = self.config.get_api_key("ollama") or backend_config.get("api_key", "")
                    if self.backend == "ollama_paid" and not api_key:
                        raise LLMError("Ollama Cloud API key not configured. Please provide one in settings.")

                    if api_key:
                        self._client = Client(host=host, headers={"Authorization": f"Bearer {api_key}"})
                    else:
                        self._client = Client(host=host)
                except ImportError:
                    raise LLMError("Ollama not installed. Run: pip install ollama")

            elif self.backend == "openai":
                try:
                    from openai import OpenAI
                    base_url = backend_config.get("base_url", "https://api.openai.com/v1")
                    api_key = self.config.get_api_key("openai") or backend_config.get("api_key", "")
                    if not api_key:
                        raise LLMError("OpenAI API key not configured. Run setup or set OPENAI_API_KEY env var.")
                    self._client = OpenAI(base_url=base_url, api_key=api_key)
                except ImportError:
                    raise LLMError("OpenAI not installed. Run: pip install openai")

            elif self.backend == "claude":
                try:
                    from anthropic import Anthropic
                    api_key = self.config.get_api_key("claude") or backend_config.get("api_key", "")
                    if not api_key:
                        raise LLMError("Anthropic API key not configured. Run setup or set ANTHROPIC_API_KEY env var.")
                    self._client = Anthropic(api_key=api_key)
                except ImportError:
                    raise LLMError("Anthropic not installed. Run: pip install anthropic")

        return self._client

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """
        Generate text from the configured LLM.

        Args:
            prompt: User prompt/message
            system: Optional system prompt
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            LLMConnectionError: If connection to LLM fails
            LLMError: If generation fails
        """
        try:
            client = self._get_client()
        except Exception as e:
            raise LLMConnectionError(f"Failed to initialize {self.backend} client: {str(e)}")

        try:
            if self.backend in ("ollama", "ollama_paid"):
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                response = client.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": temperature},
                )
                return response["message"]["content"]

            elif self.backend == "openai":
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return response.choices[0].message.content

            elif self.backend == "claude":
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system or "",
                    messages=[{"role": "user", "content": prompt}],
                    **kwargs
                )
                return response.content[0].text

            raise LLMError(f"Unknown backend: {self.backend}")

        except Exception as e:
            if isinstance(e, (LLMError, LLMConnectionError)):
                raise
            raise LLMError(f"Generation failed: {str(e)}")

    def get_embeddings(self, text: str, model: str = "qwen3-embedding:0.6b") -> list:
        """
        Generate vector embeddings for a given text.

        Args:
            text: Text to embed
            model: Embedding model name (defaults to qwen3-embedding:0.6b)

        Returns:
            List of floats representing the embedding vector
        """
        try:
            client = self._get_client()
        except Exception as e:
            raise LLMConnectionError(f"Failed to initialize {self.backend} client: {str(e)}")

        try:
            if self.backend in ("ollama", "ollama_paid"):
                backend_config = self._config_data.get(self.backend, {})
                emb_model = backend_config.get("embedding_model", model)
                response = client.embeddings(
                    model=emb_model,
                    prompt=text
                )
                return response.get("embedding", [])

            elif self.backend == "openai":
                response = client.embeddings.create(
                    input=[text],
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding

            elif self.backend == "claude":
                # Claude doesn't offer embedding endpoints directly
                raise LLMError("Claude backend does not support embeddings. Please use Ollama or configure OpenAI.")

            raise LLMError(f"Unsupported backend for embeddings: {self.backend}")
        except Exception as e:
            raise LLMError(f"Failed to generate embeddings: {str(e)}")

    def generate_code(
        self,
        prompt: str,
        skills: str = "",
        language: str = "python",
        **kwargs
    ) -> str:
        """
        Generate code with skill context.

        Args:
            prompt: Code generation request
            skills: Skills/context from skill.md file
            language: Target programming language

        Returns:
            Generated code
        """
        system_prompt = f"""You are a {language} code generation assistant.
{skills}

## Output Rules:
- Return ONLY {language} code, no explanations
- Code must be executable and complete
- Include error handling where appropriate
- Use clear variable names
"""

        temperature = kwargs.pop("temperature", 0.1)

        return self.generate(
            prompt=f"Generate {language} code for: {prompt}",
            system=system_prompt,
            temperature=temperature,
            **kwargs
        )

    def explain_results(
        self,
        results: Dict[str, Any],
        context: str = "",
        **kwargs
    ) -> str:
        """
        Generate natural language explanation of results.

        Args:
            results: Analysis results dictionary
            context: Additional context about the analysis
            **kwargs: Additional generation options

        Returns:
            Natural language explanation
        """
        prompt = f"""Explain these analysis results in clear, concise language:

{results}

{context}

Provide:
1. Key findings
2. Notable patterns or trends
3. Any anomalies or concerns
"""

        return self.generate(prompt, temperature=0.3, **kwargs)

    def get_info(self) -> dict:
        """Return current configuration info."""
        return {
            "backend": self.backend,
            "model": self.model,
            "host": self._config_data.get(self.backend, {}).get("host", "N/A"),
            "has_api_key": self.config.has_api_key(self.backend),
        }

    def test_connection(self) -> tuple:
        """
        Test connection to the LLM provider.

        Returns:
            (success: bool, message: str)
        """
        try:
            response = self.generate("Respond with exactly: CONNECTION_TEST_OK")
            if "CONNECTION_TEST_OK" in response:
                return True, "Connection successful"
            return True, f"Connected (response: {response[:50]}...)"
        except Exception as e:
            return False, str(e)
