"""LLM configuration and credentials management."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


AVAILABLE_MODELS = {
    "ollama": [
        "phi4:mini",
        "gemma4:e4b",
        "qwen2.5-coder:14b",
        "phi4:14b",
    ],
    "ollama_paid": [
        "qwen3-coder-next:cloud",
        "gemma4:31b-cloud",
        "llama3.3-70b:cloud",
        "deepseek-coder-v2:cloud",
        "kimi-k2.5:cloud",
        "minimax-m2.7:cloud",
        "glm-5.1:cloud"
    ],
    "openai": [
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.4-nano"
    ],
    "claude": [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5"
    ],
}

BACKEND_NAMES = {
    "ollama": "Ollama (Local - Free)",
    "ollama_paid": "Ollama (Cloud - Paid)",
    "openai": "OpenAI API (Paid)",
    "claude": "Claude API (Paid - Anthropic)",
}


class LLMConfig:
    """Manages LLM configuration and secure credentials."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config"

        self.config_dir = config_dir
        self.config_file = config_dir / "llm_config.yaml"
        self.credentials_file = config_dir / "llm_credentials.yaml"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Dict[str, Any]:
        """Load LLM configuration."""
        if not self.config_file.exists():
            return self._create_default_config()

        with open(self.config_file) as f:
            data = yaml.safe_load(f)
            return data if data else self._create_default_config()

    def save_config(self, config: Dict[str, Any]):
        """Save LLM configuration."""
        with open(self.config_file, "w") as f:
            yaml.dump(config, f, indent=2, default_flow_style=False)

    def load_credentials(self) -> Dict[str, Any]:
        """Load API credentials."""
        if not self.credentials_file.exists():
            return {}

        with open(self.credentials_file) as f:
            data = yaml.safe_load(f)
            return data if data else {}

    def save_credential(self, backend: str, api_key: str):
        """Save a single API credential."""
        credentials = self.load_credentials()

        if backend == "openai":
            credentials["openai"] = {"api_key": api_key}
        elif backend == "claude":
            credentials["claude"] = {"api_key": api_key}
        elif backend in ("ollama", "ollama_paid"):
            credentials["ollama"] = {"api_key": api_key}

        with open(self.credentials_file, "w") as f:
            yaml.dump(credentials, f, indent=2, default_flow_style=False)

    def get_api_key(self, backend: str) -> Optional[str]:
        """Get API key for a backend."""
        # Environment variable takes precedence
        if backend == "openai":
            env_key = os.getenv("OPENAI_API_KEY")
            if env_key:
                return env_key
        elif backend == "claude":
            env_key = os.getenv("ANTHROPIC_API_KEY")
            if env_key:
                return env_key
        elif backend in ("ollama", "ollama_paid"):
            env_key = os.getenv("OLLAMA_API_KEY")
            if env_key:
                return env_key

        # Then check credentials file
        credentials = self.load_credentials()
        # Map ollama_paid back to ollama in the credentials file
        cred_key = "ollama" if backend == "ollama_paid" else backend
        if cred_key in credentials:
            return credentials[cred_key].get("api_key")

        return None

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration."""
        default = {
            "backend": "ollama",
            "ollama": {
                "host": "http://localhost:11434",
                "model": "qwen3-coder-next:cloud",
            },
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-5.4",
            },
            "claude": {
                "model": "claude-opus-4-6",
            },
        }
        self.save_config(default)
        return default

    def has_api_key(self, backend: str) -> bool:
        """Check if API key is configured for backend."""
        return self.get_api_key(backend) is not None

    def get_current_config(self) -> Dict[str, Any]:
        """Get current active configuration summary."""
        config = self.load_config()
        backend = config.get("backend", "ollama")
        backend_config = config.get(backend, {})

        host = backend_config.get("host", "http://localhost:11434")
        if not host or host == "N/A":
            host = "http://localhost:11434"

        result = {
            "backend": backend,
            "model": backend_config.get("model", "unknown"),
            "host": host,
            "has_api_key": self.has_api_key(backend),
        }

        # Add base_url for openai
        if backend == "openai":
            result["base_url"] = backend_config.get("base_url", "https://api.openai.com/v1")

        return result

    def update_backend(self, backend: str):
        """Update the active backend."""
        config = self.load_config()
        config["backend"] = backend
        self.save_config(config)

    def update_model(self, backend: str, model: str):
        """Update the model for a backend."""
        config = self.load_config()
        if backend not in config:
            config[backend] = {}
        config[backend]["model"] = model
        self.save_config(config)

    def update_host(self, host: str):
        """Update Ollama host."""
        config = self.load_config()
        if "ollama" not in config:
            config["ollama"] = {}
        config["ollama"]["host"] = host
        self.save_config(config)
