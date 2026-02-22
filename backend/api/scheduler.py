import asyncio
import traceback
from backend.api.kserc_scraper import kserc_scraper

async def kserc_periodic_sync_loop(interval_seconds: int = 86400):
    """
    Background worker loop initialized at FastAPI startup.
    Runs every `interval_seconds` (default 24h) to pull fresh KSERC regulatory benchmarks.
    """
    while True:
        try:
            # Execute the sync logic
            await kserc_scraper.sync_benchmarks()
        except asyncio.CancelledError:
            print("KSERC Background Sync cancelled.")
            break
        except Exception as e:
            print(f"KSERC Background Sync Exception: {e}")
            traceback.print_exc()
        
        # Sleep until the next cycle (24 hours by default)
        await asyncio.sleep(interval_seconds)
