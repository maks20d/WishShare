from collections import defaultdict
from collections.abc import AsyncGenerator
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.routes import auth, og, wishlists, ws
from app.core.config import settings
from app.core.logger import configure_logging
from app.db.session import Base, engine


logger = configure_logging()

app = FastAPI(title=settings.app_name)

metrics = {
    "requests_total": 0,
    "errors_total": 0,
    "latency_total_ms": 0.0,
    "by_path": defaultdict(
        lambda: {"count": 0, "errors": 0, "latency_total_ms": 0.0}
    ),
}


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    start = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - start) * 1000.0
        metrics["requests_total"] += 1
        metrics["errors_total"] += 1
        metrics["latency_total_ms"] += duration_ms
        path_metrics = metrics["by_path"][request.url.path]
        path_metrics["count"] += 1
        path_metrics["errors"] += 1
        path_metrics["latency_total_ms"] += duration_ms
        logger.exception(
            "Request failed id=%s method=%s path=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (perf_counter() - start) * 1000.0
    metrics["requests_total"] += 1
    metrics["latency_total_ms"] += duration_ms
    path_metrics = metrics["by_path"][request.url.path]
    path_metrics["count"] += 1
    path_metrics["latency_total_ms"] += duration_ms
    logger.info(
        "Request completed id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-Id"] = request_id
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "connect-src 'self' http: https: ws: wss:; "
        "font-src 'self' data: https:;"
    )
    return response


@app.on_event("startup")
async def on_startup() -> None:
    try:
        import asyncio

        loop = asyncio.get_running_loop()
        loop.set_exception_handler(_handle_async_exception)
    except RuntimeError:
        logger.warning("No running event loop during startup")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # lightweight, idempotent migration for public_token
        try:
            await conn.exec_driver_sql("ALTER TABLE wishlists ADD COLUMN public_token VARCHAR(36)")
        except Exception:
            # column may already exist or ALTER not supported; ignore
            pass
        # ensure unique index (best-effort)
        try:
            await conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_wishlists_public_token ON wishlists(public_token)"
            )
        except Exception:
            pass
        # backfill tokens where missing
        try:
            result = await conn.exec_driver_sql("SELECT id FROM wishlists WHERE public_token IS NULL OR public_token = ''")
            rows = result.fetchall()
            for (wid,) in rows:
                await conn.exec_driver_sql(
                    "UPDATE wishlists SET public_token = :token WHERE id = :id",
                    {"token": str(uuid4()), "id": wid},
                )
        except Exception:
            logger.warning("Failed to backfill public_token values", exc_info=True)

        # gifts: add unavailability columns (best-effort)
        try:
            await conn.exec_driver_sql("ALTER TABLE gifts ADD COLUMN is_unavailable BOOLEAN DEFAULT 0")
        except Exception:
            pass
        try:
            await conn.exec_driver_sql("ALTER TABLE gifts ADD COLUMN unavailable_reason VARCHAR(255)")
        except Exception:
            pass

        # archive table (best-effort)
        try:
            await conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS wishlist_items_archive (
                    id SERIAL PRIMARY KEY,
                    wishlist_id INTEGER REFERENCES wishlists(id),
                    gift_id INTEGER,
                    title VARCHAR(255) NOT NULL,
                    image_url VARCHAR(2048),
                    last_price NUMERIC(12,2),
                    reason VARCHAR(255),
                    archived_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
        except Exception:
            pass

        # donation ledger (best-effort)
        try:
            await conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS wishlist_donations (
                    id SERIAL PRIMARY KEY,
                    wishlist_id INTEGER REFERENCES wishlists(id),
                    gift_id INTEGER,
                    user_id INTEGER REFERENCES users(id),
                    amount NUMERIC(12,2) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
        except Exception:
            pass


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(wishlists.router)
app.include_router(wishlists.compat_router)
app.include_router(ws.router)
app.include_router(og.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def get_metrics() -> dict[str, object]:
    by_path = {
        path: {
            "count": data["count"],
            "errors": data["errors"],
            "avg_latency_ms": (
                data["latency_total_ms"] / data["count"] if data["count"] else 0.0
            ),
        }
        for path, data in metrics["by_path"].items()
    }
    return {
        "requests_total": metrics["requests_total"],
        "errors_total": metrics["errors_total"],
        "avg_latency_ms": (
            metrics["latency_total_ms"] / metrics["requests_total"]
            if metrics["requests_total"]
            else 0.0
        ),
        "by_path": by_path,
    }


def _handle_async_exception(loop, context) -> None:
    message = context.get("message", "Async error")
    exc = context.get("exception")
    if exc:
        logger.exception("Async error: %s", message, exc_info=exc)
    else:
        logger.error("Async error: %s", message)
