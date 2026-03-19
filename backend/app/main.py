import uvicorn
import uuid
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.router import api_router
from app.core.response import error as error_response
from app.core.logger import setup_logger, logger
from app.core import database

# Initialize logger
setup_logger()
logger.info("Initializing FastAPI Application...")

app = FastAPI(
    title="AI Test Platform API",
    description="A centralized testing platform for AI generated content.",
    version="1.0.0"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api")

@app.middleware("http")
async def request_trace_middleware(request: Request, call_next):
    tid = uuid.uuid4().hex
    request.state.tid = tid
    response = await call_next(request)
    response.headers["X-TID"] = tid
    return response


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


@app.on_event("startup")
async def startup_event():
    database.init_db()
    logger.info("Application started up successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=True)
