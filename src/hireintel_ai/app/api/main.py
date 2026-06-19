"""FastAPI entry point for HireIntel AI."""

from fastapi import FastAPI

from hireintel_ai.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        """Return a lightweight health response.

        Returns:
            Health status payload.
        """
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()

