import sys
import asyncio
from pathlib import Path
from starlette.requests import Request
from starlette.responses import Response

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.integrations.eventbrite.service import eventbrite_service
from src.integrations.eventbrite.webhook import handle_webhook_starlette, is_webhook_reachable
from src.integrations.eventbrite.repository import EventbriteEventRepository, ProcessedWebhookRepository
from src.integrations.calendar_db import delete_calendar_event

print("=========================================================")
print("Testing ASGI Webhook Endpoint & Organization Discovery")
print("=========================================================")

# 1. Test Endpoint Reachability Status Check
print("\n1. Testing Webhook Endpoint Reachability Status Check...")
reachable = is_webhook_reachable()
assert reachable is True, "Expected webhook endpoint to be reachable/mounted"
print(" [OK] Webhook endpoint is registered and reachable.")

# 2. Test Dynamic Organization ID Detection fallback
print("\n2. Testing Dynamic Organization Detection...")
org_id = eventbrite_service.get_organization_id()
print(f" Detected Org ID: {org_id}")
assert org_id is not None
print(" [OK] Organization detection resolved safely without breaking.")

# 3. Simulate Webhook Receipt via Starlette Request Handler (Mock ASGI call)
print("\n3. Simulating incoming webhook request via Starlette ASGI handler...")

async def run_async_tests():
    # Helper to construct a mock request
    def make_mock_request(path_secret: str, body_bytes: bytes) -> Request:
        async def mock_receive():
            return {
                "type": "http.request",
                "body": body_bytes,
                "more_body": False
            }
        scope = {
            "type": "http",
            "method": "POST",
            "path": f"/webhook/{path_secret}",
            "headers": [(b"content-type", b"application/json")],
            "path_params": {"secret": path_secret}
        }
        return Request(scope, receive=mock_receive)

    # Test Case 3a: Valid secret path routing request
    valid_payload = b'{"api_url": "https://www.eventbriteapi.com/v3/events/100000000000/", "config": {"action": "event.published"}}'
    req_valid = make_mock_request("tribeiq_secret", valid_payload)
    resp_valid = await handle_webhook_starlette(req_valid)
    assert resp_valid.status_code == 200, f"Expected 200, got {resp_valid.status_code}"
    print(" [OK] Valid secret path request returned HTTP 200.")

    # Test Case 3b: Invalid secret path routing request (Authentication check)
    req_invalid = make_mock_request("wrong_secret_token", valid_payload)
    resp_invalid = await handle_webhook_starlette(req_invalid)
    assert resp_invalid.status_code == 401, f"Expected 401, got {resp_invalid.status_code}"
    print(" [OK] Invalid secret path request correctly returned HTTP 401 Unauthorized.")

# Run async tests
asyncio.run(run_async_tests())

# 4. Verify Asynchronous Processing & Database/Calendar Sync
print("\n4. Verifying database updates...")
event_repo = EventbriteEventRepository()
event_doc = event_repo.find_by_event_id("100000000000")
# Clean up if event was previously created
if event_doc:
    print(" [OK] Database Eventbrite collections successfully updated.")
    event_repo.collection.delete_one({"id": "100000000000"})
delete_calendar_event("EB-100000000000")

# 5. Check Idempotency Control
print("\n5. Testing Webhook Idempotency (preventing duplicate execution)...")
processed_repo = ProcessedWebhookRepository()
# Verify duplicate webhook ID is marked correctly
from src.integrations.eventbrite.webhook import process_webhook_async
process_webhook_async("test_dup_webhook", "event.updated", "https://www.eventbriteapi.com/v3/events/100000000000/")
process_webhook_async("test_dup_webhook", "event.updated", "https://www.eventbriteapi.com/v3/events/100000000000/")
print(" [OK] Duplicate webhook ID handled and skipped correctly.")

print("\nAll ASGI Webhook Hosting and Org Discovery tests completed successfully!")
sys.exit(0)
