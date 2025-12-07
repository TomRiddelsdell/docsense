import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_CTX_KEY = "request_id"
request_id_ctx_var: ContextVar[str] = ContextVar(REQUEST_ID_CTX_KEY, default="")


def get_request_id() -> str:
    return request_id_ctx_var.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_ctx_var.set(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
