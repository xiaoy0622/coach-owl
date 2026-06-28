"""Unified error body ``{error:{code,message,details?}}`` + exception handlers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Domain error carrying an HTTP status + machine-readable code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


def not_implemented() -> None:
    """Raise a uniform 501 for placeholder (Wave 2+) endpoints."""
    raise AppError(
        "Not implemented yet",
        code="not_implemented",
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
    )


def _body(code: str, message: str, details: Any | None = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"error": err}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            status.HTTP_401_UNAUTHORIZED: "unauthorized",
            status.HTTP_403_FORBIDDEN: "forbidden",
            status.HTTP_404_NOT_FOUND: "not_found",
            status.HTTP_501_NOT_IMPLEMENTED: "not_implemented",
        }.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(code, str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_body("validation_error", "Invalid request", exc.errors()),
        )
