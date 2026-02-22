"""
Enterprise Startup Script for Windows Server Environments.
Configures Uvicorn programmatically to allocate CPU cores dynamically.
"""

import os
import multiprocessing
import uvicorn

def main():
    # Attempt to derive optimal worker counts based on CPU cores.
    # Uvicorn doc recommends (NUM_CORES * 2) + 1 for standard ASGI scaling.
    cores = multiprocessing.cpu_count()
    workers = (cores * 2) + 1

    # In extremely high-core machines, cap at a reasonable number for AI bound tasks to avoid excessive memory exhaustion
    if workers > 8:
        workers = 8

    print(f"⚖️ Booting ARR Truing-Up Engine on Windows.")
    print(f"🚀 Scaling out with {workers} asynchronous Uvicorn workers.")

    # In production, we assume we run behind a proxy like IIS or NGINX. 
    # Enable proxy headers and keep-alive configuration.
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        workers=workers,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
        timeout_keep_alive=65
    )

if __name__ == "__main__":
    main()
