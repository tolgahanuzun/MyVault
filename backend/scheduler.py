from apscheduler.schedulers.background import BackgroundScheduler
from backend.services.fetcher import fetch_fund_prices
from backend.database import AsyncSessionLocal
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def update_prices_async():
    logger.info("Async price update started.")
    async with AsyncSessionLocal() as db:
        try:
            await fetch_fund_prices(db)
        except Exception as e:
            logger.error(f"Error in async price update: {e}")

def update_prices_job():
    logger.info("Scheduled job started: Price Update")
    try:
        # Create a new event loop for this thread to run the async task
        asyncio.run(update_prices_async())
    except Exception as e:
        logger.error(f"Scheduler job failed: {e}")
    logger.info("Scheduled job finished.")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run every day at 20:00 (TEFAS is usually updated in the evening)
    scheduler.add_job(update_prices_job, 'cron', minute=0)
    # Run once on startup (for testing)
    scheduler.add_job(update_prices_job, 'date', run_date=datetime.now() + timedelta(seconds=10)) 
    scheduler.start()
    logger.info("Scheduler started.")
