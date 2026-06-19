"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for local development and deployed environments.

    Attributes:
        app_name: Display name used by API and UI entry points.
        app_version: Application version surfaced by runtime entry points.
        project_root: Repository root used to resolve local data paths.
        raw_data_dir: Local directory for unprocessed input documents.
        processed_data_dir: Local directory for generated structured artifacts.
        qdrant_url: Vector database URL for retrieval workflows.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HireIntel AI"
    app_version: str = "0.1.0"
    project_root: Path = Field(default_factory=lambda: Path.cwd())
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    qdrant_url: str = "http://localhost:6333"

    @property
    def resolved_raw_data_dir(self) -> Path:
        """Return the absolute raw data directory path.

        Returns:
            Absolute path to raw local input data.
        """
        return self._resolve_workspace_path(self.raw_data_dir)

    @property
    def resolved_processed_data_dir(self) -> Path:
        """Return the absolute processed data directory path.

        Returns:
            Absolute path to generated local processing outputs.
        """
        return self._resolve_workspace_path(self.processed_data_dir)

    def _resolve_workspace_path(self, path: Path) -> Path:
        """Resolve a relative path under the configured project root.

        Args:
            path: Absolute or project-relative filesystem path.

        Returns:
            Absolute filesystem path.
        """
        if path.is_absolute():
            return path
        return self.project_root / path


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings.

    Returns:
        Runtime settings loaded from defaults and environment variables.
    """
    return Settings()

