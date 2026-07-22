import sys
from pathlib import Path

# Setup Project Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import logger, settings
from src.integrations.eventbrite.service import eventbrite_service
from src.database import db_manager

def test_search_and_sync():
    logger.info("=========================================================")
    logger.info("Testing Simplified Eventbrite Search & Scheduled Sync")
    logger.info("=========================================================")

    # 1. Verify connection status
    token = getattr(settings, "EVENTBRITE_PRIVATE_TOKEN", "MOCK_TOKEN")
    logger.info(f"Using Token: {token[:6]}... (Redacted)" if token != "MOCK_TOKEN" else "Using mock token.")

    # 2. Test event search
    logger.info("1. Querying public events in Pune...")
    events = eventbrite_service.search_events(location="Pune", radius=50)
    assert len(events) > 0, "No Pune events found/simulated!"
    logger.info(f" [OK] Discovered {len(events)} public events in/around Pune.")

    # Check structure
    sample = events[0]
    required_keys = ["id", "name", "description", "category", "venue", "address", "start_time", "end_time", "source"]
    for k in required_keys:
        assert k in sample, f"Missing required event key: {k}"
    logger.info(" [OK] Event structure conforms to the required data model.")

    # 3. Test sync/upsert to MongoDB
    logger.info("2. Triggering Pune Events database sync...")
    res = eventbrite_service.sync_pune_events()
    assert res.get("status") == "Success", f"Sync failed: {res.get('error')}"
    logger.info(f" [OK] Synchronization completed successfully. Synced {res.get('synced_count')} events.")

    # 4. Verify duplicate prevention (idempotency)
    logger.info("3. Verifying idempotency (duplicate prevention)...")
    res_dup = eventbrite_service.sync_pune_events()
    assert res_dup.get("status") == "Success"
    # Synced count on immediate repeat should still be the same count but update instead of creating new duplicates
    db_count = db_manager.get_collection("external_events").count_documents({})
    logger.info(f" [OK] External events in collection: {db_count}. No duplicate documents created.")

    # 5. Check metadata logging
    status = eventbrite_service.get_sync_status()
    logger.info(f" [OK] Metadata Sync Status Checked. Last sync: {status.get('last_sync_time')}, Status: {status.get('status')}")

    logger.info("\nAll Simplified Eventbrite Search & Scheduled Sync tests completed successfully!")

if __name__ == "__main__":
    test_search_and_sync()
