"""
Scheduled Data Sync Jobs
Runs periodic data synchronization from Amazon APIs
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from data_sync import run_daily_sync
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_scheduler():
    """
    Initialize and start the scheduler
    
    Returns:
        BackgroundScheduler instance
    """
    scheduler = BackgroundScheduler()
    
    # Daily sync at 2 AM
    scheduler.add_job(
        run_daily_sync,
        CronTrigger(hour=2, minute=0),
        id='daily_sync',
        name='Daily Amazon Data Sync',
        replace_existing=True
    )
    
    # You can add more scheduled jobs here
    # Example: Hourly sync for real-time data
    # scheduler.add_job(
    #     run_hourly_sync,
    #     CronTrigger(minute=0),
    #     id='hourly_sync',
    #     name='Hourly Amazon Data Sync',
    #     replace_existing=True
    # )
    
    return scheduler


def start_scheduler():
    """Start the scheduler"""
    scheduler = init_scheduler()
    scheduler.start()
    logger.info("Scheduler started successfully")
    logger.info(f"Scheduled jobs: {[job.name for job in scheduler.get_jobs()]}")
    return scheduler


if __name__ == "__main__":
    # Run scheduler standalone
    import time
    
    scheduler = start_scheduler()
    
    try:
        # Keep the script running
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped")



