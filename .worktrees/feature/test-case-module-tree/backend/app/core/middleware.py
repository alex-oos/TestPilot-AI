import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestTraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tid = uuid.uuid4().hex
        request.state.tid = tid
        response = await call_next(request)
        response.headers["X-TID"] = tid
        return response
