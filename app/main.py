from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.db.database import engine
from app.routers.invoice_templates import router as invoice_templates_router
from app.routers.ai_invoices import router as ai_invoices_router
from app.routers.clients import router as clients_router
from app.routers.dashboard import router as dashboard_router
from app.routers.invoices import router as invoices_router
from app.routers.payments import router as payments_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connected successfully.")
    yield
    print("Application shutdown.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=False,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(ai_invoices_router)
app.include_router(clients_router)
app.include_router(dashboard_router)
app.include_router(invoices_router)
app.include_router(invoice_templates_router)
app.include_router(payments_router)


def error_response(status_code: int, message: str, result=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": False,
            "message": message,
            "result": result,
        },
    )


@app.middleware("http")
async def standard_error_response_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unhandled request error")
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    response = error_response(status_code=exc.status_code, message=str(exc.detail))
    response.headers.update(exc.headers or {})
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        result=exc.errors(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error")
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error",
    )


@app.get("/")
def root():
    return {
        "status": True,
        "message": "success",
        "result": {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
        },
    }


@app.get("/health")
def health_check():
    return {
        "status": True,
        "message": "health success",
        "result": {"status": "ok"},
    }
