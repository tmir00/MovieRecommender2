"""FastAPI health endpoints for liveness, readiness, and startup probes."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Engine

from health.state import HealthState


def _max_poll_age_seconds() -> float:
    """Get the maximum poll age seconds from the environment variables."""
    return float(os.environ.get("HEALTH_MAX_POLL_AGE_SECONDS", "90"))


def _postgres_ok(engine: Engine) -> bool:
    """Return True when Postgres accepts a simple query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _live_check(state: HealthState) -> JSONResponse | None:
    """
    Return a 503 response when the poll loop is not alive; otherwise None.

    Shared by liveness, startup, and readiness probes.
    """
    if not state.is_alive(_max_poll_age_seconds()):
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "poll_loop_stalled_or_shutting_down"},
        )
    return None


def _startup_check(state: HealthState, engine: Engine) -> JSONResponse:
    """
    Startup probe — looser than readiness.

    Checks poll-loop liveness and Postgres only. Kafka partition assignment is
    intentionally omitted so group join / rebalance during boot does not fail
    startup; use /health/ready once the consumer should be fully serving.
    """
    # Check if the consumer is alive.
    live_failure = _live_check(state)
    if live_failure is not None:
        return JSONResponse(
            status_code=503,
            content={"status": "not_started", "reason": "poll_loop_stalled_or_shutting_down"},
        )

    # Check if Postgres is available.
    if not _postgres_ok(engine):
        return JSONResponse(
            status_code=503,
            content={"status": "not_started", "reason": "postgres_unavailable"},
        )

    # If all checks pass, return a JSON response with the status of the startup probe.
    return JSONResponse(content={"status": "started"})


def create_health_app(state: HealthState, engine: Engine) -> FastAPI:
    """
    Build the health API used by Docker Compose and Kubernetes probes.

    ==================== Arguments ====================
    state: Shared liveness state updated by the poll loop.
    engine: SQLAlchemy engine for readiness Postgres checks.
    """
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/health/live")
    def live() -> JSONResponse:
        """
        Liveness probe. Check if the consumer is still alive by checking the last poll time.
        If the last poll time is too old, the consumer is considered unhealthy and the pod will be restarted.

        ===================== Returns =====================
        A JSON response with the status of the liveness probe.
        {
            "status": "alive" | "unhealthy",
            "reason": "poll_loop_stalled_or_shutting_down",
        }
        """
        live_failure = _live_check(state)
        if live_failure is not None:
            return live_failure
        return JSONResponse(content={"status": "alive"})

    @app.get("/health/ready")
    def ready() -> JSONResponse:
        """
        Readiness probe
        Check if the consumer is ready to serve requests by checking the last poll time, Postgres, and Kafka assignment.
        If any of these checks fail, the consumer is considered not ready and the pod will not be restarted.

        ===================== Returns =====================
        A JSON response with the status of the readiness probe.
        {
            "status": "ready" | "not_ready",
            "reason": "poll_loop_stalled_or_shutting_down" | "postgres_unavailable" | "kafka_not_assigned",
        }
        """
        # Check if the consumer is alive.
        live_failure = _live_check(state)
        if live_failure is not None:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "poll_loop_stalled_or_shutting_down"},
            )

        # Check if Postgres is available.
        if not _postgres_ok(engine):
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "postgres_unavailable"},
            )

        # Check if Kafka has at least one assigned partition.
        if not state.kafka_has_assignment():
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "kafka_not_assigned"},
            )

        # If all checks pass, return a JSON response with the status of the readiness probe.
        return JSONResponse(content={"status": "ready"})

    @app.get("/health/startup")
    def startup() -> JSONResponse:
        """Startup probe
        Check if the consumer has booted enough to continue starting (poll loop + Postgres).
        Does not require Kafka partition assignment yet — group join may still be in progress.
        Pair with a generous Kubernetes startupProbe failureThreshold during deploy.

        ===================== Returns =====================
        A JSON response with the status of the startup probe.
        {
            "status": "started" | "not_started",
            "reason": "poll_loop_stalled_or_shutting_down" | "postgres_unavailable",
        }
        """
        return _startup_check(state, engine)

    return app
