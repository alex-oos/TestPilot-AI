import typer
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.application import app_settings
from app.application.urls import urlpatterns
from app.core.event import lifespan
from app.core.exception import register_exception
from app.core.logger import logger, setup_logger
from app.core.middleware import RequestTraceMiddleware

shell_app = typer.Typer()


def create_app() -> FastAPI:
    setup_logger()
    logger.info("Initializing FastAPI Application...")

    app = FastAPI(
        title=app_settings.title,
        description=app_settings.description,
        version=app_settings.version,
        docs_url=app_settings.docs_url,
        redoc_url=app_settings.redoc_url,
        openapi_url=app_settings.openapi_url,
        lifespan=lifespan,
    )

    if app_settings.cors_origin_enable:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(app_settings.allow_origins),
            allow_credentials=app_settings.allow_credentials,
            allow_methods=list(app_settings.allow_methods),
            allow_headers=list(app_settings.allow_headers),
        )
    app.add_middleware(RequestTraceMiddleware)
    register_exception(app)

    for item in urlpatterns:
        app.include_router(
            item["ApiRouter"],
            prefix=f"{app_settings.api_prefix}{item['prefix']}",
            tags=item["tags"],
        )
    return app


app = create_app()


@shell_app.command()
def run(
    host: str = typer.Option(default=app_settings.host, help="监听主机IP"),
    port: int = typer.Option(default=app_settings.port, help="监听端口"),
    reload: bool = typer.Option(default=app_settings.reload, help="是否开启热重载"),
):
    uvicorn.run("app.main:create_app", host=host, port=port, factory=True, reload=reload)


if __name__ == "__main__":
    shell_app()
