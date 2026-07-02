import uuid

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from app.core.logger import logger
from app.core.response import error as error_response


def register_exception(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        tid = getattr(request.state, "tid", uuid.uuid4().hex)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.status_code, str(exc.detail), tid),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        tid = getattr(request.state, "tid", uuid.uuid4().hex)
        message = exc.errors()[0].get("msg", "请求参数校验失败") if exc.errors() else "请求参数校验失败"
        return JSONResponse(
            status_code=422,
            content=error_response(422, message, tid, data=exc.errors()),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        tid = getattr(request.state, "tid", uuid.uuid4().hex)
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=error_response(500, "internal server error", tid),
        )
