from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class AppSettings:
    title: str = "AI Test Platform API"
    description: str = "A centralized testing platform for AI generated content."
    version: str = "1.0.0"
    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"
    openapi_url: str | None = "/openapi.json"
    api_prefix: str = "/api"

    cors_origin_enable: bool = True
    allow_origins: tuple[str, ...] = ("*",)
    allow_credentials: bool = True
    allow_methods: tuple[str, ...] = ("*",)
    allow_headers: tuple[str, ...] = ("*",)

    host: str = "0.0.0.0"
    port: int = 8001
    reload: bool = True


app_settings = AppSettings(
    version="1.0.0",
    host="0.0.0.0",
    port=8001,
    reload=True,
)

# Re-export legacy runtime settings so service code can keep using one place.
runtime_settings = settings
