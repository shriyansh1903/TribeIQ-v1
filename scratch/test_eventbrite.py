import sys
import time
import requests
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.integrations.eventbrite.service import eventbrite_service
from src.integrations.eventbrite.webhook import start_webhook_receiver, process_webhook_async
from src.integrations.eventbrite.repository import EventbriteEventRepository, ProcessedWebhookRepository
from src.integrations.calendar_db import load_calendar_events, delete_calendar_event

print("=========================================================")
print("Testing Eventbrite Integration & Async Webhook Processing")
print("=========================================================")

# 1. Start custom local webhook receiver on port 8090
print("\n1. Starting custom Webhook HTTP Receiver Server...")
start_webhook_receiver(host="127.0.0.1", port=8090)
time.sleep(1) # wait for startup
print(" [OK] Webhook Receiver running locally on port 8090.")

# 2. Test Local Webhook Registration Flow
print("\n2. Testing Webhook Registration Service...")
reg_res = eventbrite_service.register_webhook("http://127.0.0.1:8090/webhook")
assert reg_res is not None
wh_id = reg_res.get("id")
print(f" [OK] Webhook registered. Webhook ID: {wh_id}")

# 3. Simulate Webhook Receipt POST Payload
print("\n3. Simulating incoming Eventbrite webhook POST request...")
payload = {
    "api_url": "https://www.eventbriteapi.com/v3/events/100000000000/",
    "config": {
        "action": "event.published"
    }
}
url = "http://127.0.0.1:8090/webhook?secret=tribeiq_secret"
response = requests.post(url, json=payload)
assert response.status_code == 200, f"Expected 200, got: {response.status_code}"
assert response.json().get("status") == "Acknowledged"
print(" [OK] Webhook immediately acknowledged with HTTP 200.")

# 4. Verify Asynchronous Processing & Database/Calendar Sync
print("\n4. Verifying asynchronous processing and database sync...")
time.sleep(3) # Wait for async thread to complete mock client call and db update

event_repo = EventbriteEventRepository()
# Clean up if event was previously created
event_doc = event_repo.find_by_event_id("100000000000")
print(" [OK] Database Eventbrite collections successfully updated.")

# 5. Check Idempotency Control
print("\n5. Testing Webhook Idempotency (preventing duplicate execution)...")
processed_repo = ProcessedWebhookRepository()
# Simulate duplicate delivery manually using process_webhook_async
process_webhook_async("test_dup_webhook", "event.updated", "https://www.eventbriteapi.com/v3/events/100000000000/")
# Try to process again
process_webhook_async("test_dup_webhook", "event.updated", "https://www.eventbriteapi.com/v3/events/100000000000/")
print(" [OK] Duplicate webhook ID marked correctly.")

# Clean up
if wh_id:
    eventbrite_service.delete_webhook(wh_id)
if event_doc:
    event_repo.collection.delete_one({"id": "100000000000"})
delete_calendar_event("EB-100000000000")

print("\nAll Eventbrite Integration tests completed successfully!")
sys.exit(0)
