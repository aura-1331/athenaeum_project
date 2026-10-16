from time import perf_counter

from fastapi import APIRouter, HTTPException, Request

from app.database import get_connection

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def health_check(request: Request):
    """Public readiness check for cloud monitoring and the dashboard.

    The API process is reachable when this endpoint returns. PostgreSQL is
    verified independently with a real SELECT 1 query. This endpoint does
    not write an audit record because the health check must remain usable
    when the database itself is unavailable.
    """
    started = perf_counter()
    conn = None

    try:
        conn = get_connection()
        db_started = perf_counter()

        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()

        db_latency_ms = round((perf_counter() - db_started) * 1000, 2)

        if not result or result[0] != 1:
            raise RuntimeError("Database health query returned an unexpected result")

        total_latency_ms = round((perf_counter() - started) * 1000, 2)
        return {
            "status": "ok",
            "backend": {
                "status": "ok",
                "latency_ms": total_latency_ms,
            },
            "database": {
                "status": "ok",
                "latency_ms": db_latency_ms,
            },
        }

    except Exception:
        total_latency_ms = round((perf_counter() - started) * 1000, 2)

        # Do not expose connection details, credentials, hostnames, or driver errors.
        # HTTP 503 lets monitoring distinguish a degraded service from a healthy one.
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "backend": {
                    "status": "ok",
                    "latency_ms": total_latency_ms,
                },
                "database": {
                    "status": "error",
                    "latency_ms": None,
                },
            },
        )
    finally:
        if conn:
            conn.close()
