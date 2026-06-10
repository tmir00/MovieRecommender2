"""Run the health API on a background thread alongside the Kafka poll loop."""

from __future__ import annotations

import os
import threading

import uvicorn
from fastapi import FastAPI


def start_health_server(app: FastAPI) -> threading.Thread:
    """
    Start uvicorn on a daemon thread so the main thread can block on Kafka poll.

    ==================== Arguments ====================
    app: FastAPI application exposing /health/live, /health/ready, /health/startup.

    ==================== Returns ====================
    The background thread running the HTTP server.
    """
    # Get the host and port from the environment variables.
    host = os.environ.get("HEALTH_HOST", "0.0.0.0")
    port = int(os.environ.get("HEALTH_PORT", "8080"))

    # Create the uvicorn config.
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=os.environ.get("HEALTH_LOG_LEVEL", "warning"),
        access_log=False,
    )
    # Create the uvicorn server.
    server = uvicorn.Server(config)

    # Create the background thread to run the uvicorn server.
    thread = threading.Thread(target=server.run, name="health-server", daemon=True)
    
    # Start the background thread.
    thread.start()

    # Return the background thread running the HTTP server.
    return thread
