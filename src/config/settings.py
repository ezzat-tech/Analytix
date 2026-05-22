"""Configuration management using pydantic settings."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration.

    Can be set via environment variables with AGENT_ prefix
    or via .env file.
    """

    # ===== Paths =====
    base_dir: Path = Path(__file__).parent.parent.parent
    state_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    logs_dir: Optional[Path] = None
    data_dir: Optional[Path] = None

    # ===== Agent Settings =====
    agent_timeout: float = 60.0
    max_retries: int = 3
    enable_caching: bool = True

    # ===== Visualization Settings =====
    viz_format: str = "png"
    viz_dpi: int = 150
    viz_style: str = "seaborn-v0_8"

    # ===== Logging =====
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ===== Model / API (for future LLM integration) =====
    anthropic_api_key: Optional[str] = None
    default_model: str = "claude-sonnet-4-5-20250929"

    # ===== Feature Flags =====
    enable_parallel_execution: bool = False
    enable_state_persistence: bool = True
    enable_human_in_loop: bool = False

    model_config = {
        "env_prefix": "AGENT_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def model_post_init(self, __context) -> None:
        """Set default paths after initialization."""
        if self.state_dir is None:
            self.state_dir = self.base_dir / "state"
        if self.output_dir is None:
            self.output_dir = self.base_dir / "outputs"
        if self.logs_dir is None:
            self.logs_dir = self.base_dir / "logs"
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"

        # Ensure directories exist
        for dir_path in [self.state_dir, self.output_dir, self.logs_dir, self.data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Set log file default
        if self.log_file is None:
            self.log_file = self.logs_dir / "orchestrator.log"

    def setup_logging(self):
        """Configure logging based on settings."""
        import logging

        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format,
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(),
            ]
        )

        return logging.getLogger(__name__)


# Global settings instance
settings = Settings()
