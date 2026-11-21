# services/backend/app/main.py
# Backend application entry point
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database.connection import engine

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api.users import router as users_router

from .api.devices import router as devices_router

from .api.challenges import router as challenges_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="Behavioral Auth Backend",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(users_router)
app.include_router(devices_router)
app.include_router(challenges_router)

@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request, _exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
            }
        },
    )

@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from None

    return {"status": "ok", "database": "ok"}