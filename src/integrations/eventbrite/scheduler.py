import time
import threading
from src.config import logger
from src.integrations.eventbrite.service import eventbrite_service

class EventbriteScheduler:
    def __init__(self, interval_seconds: int = 3600):
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        
        def run_loop():
            logger.info("Eventbrite Background Sync Scheduler Thread started.")
            while self.running:
                try:
                    res = eventbrite_service.sync_all_events()
                    logger.info(f"Scheduled Eventbrite Sync completed. Status: {res.get('status')}, Synced count: {res.get('synced_count')}")
                except Exception as e:
                    logger.error(f"Scheduled Eventbrite Sync encountered error: {str(e)}")
                    
                # Sleep in increments of 5 seconds to respond quickly to termination
                slept = 0
                while self.running and slept < self.interval_seconds:
                    time.sleep(5)
                    slept += 5

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("Eventbrite Background Sync Scheduler Thread stopped.")

# Singleton Scheduler
eventbrite_scheduler = EventbriteScheduler()
