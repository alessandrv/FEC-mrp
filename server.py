#!/usr/bin/env python
import os
import sys
import uvicorn

def main():
    host = os.getenv("BACKEND_HOST", "172.16.16.27")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    reload_enabled = os.getenv("BACKEND_RELOAD", "false").lower() in ("1", "true", "yes", "on")
    workers = int(os.getenv("BACKEND_WORKERS", "1"))
    log_level = os.getenv("BACKEND_LOG_LEVEL", "info")

    if reload_enabled and workers != 1:
        workers = 1  # uvicorn does not allow reload with multiple workers

    uvicorn.run(
        "backend:app",
        host=host,
        port=port,
        reload=reload_enabled,
        workers=workers,
        log_level=log_level,
    )

if __name__ == "__main__":
    # Allow passing an optional port as first argument: python server.py 9000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        os.environ["BACKEND_PORT"] = sys.argv[1]
    main()