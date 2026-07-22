import json
import uuid
import time
from datetime import datetime
from typing import Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from src.config import settings, logger
from src.integrations.eventbrite.repository import EventbriteWebhookRepository, ProcessedWebhookRepository
from src.integrations.eventbrite.dispatcher import EventbriteWebhookDispatcher
from src.utils.background_job import background_job_service

def process_webhook_async(webhook_id: str, action: str, api_url: str, trace_id: Optional[str] = None):
    """
    Asynchronously processes the queued webhook event.
    """
    if not trace_id:
        trace_id = f"TR-{uuid.uuid4().hex[:8].upper()}"

    start_time = time.time()
    logger.info(f"[{trace_id}] Processing started for webhook {webhook_id}: {action} on {api_url}")
    
    processed_repo = ProcessedWebhookRepository()
    webhook_repo = EventbriteWebhookRepository()
    
    # 1. Idempotency Check
    if processed_repo.is_processed(webhook_id):
        logger.warning(f"[{trace_id}] Aborting duplicate webhook event processing. Webhook ID '{webhook_id}' already processed.")
        try:
            webhook_repo.collection.update_one(
                {"id": webhook_id}, 
                {"$set": {
                    "status": "Duplicate", 
                    "processed_at": datetime.utcnow(),
                    "processing_duration": time.time() - start_time
                }}
            )
        except Exception:
            pass
        return

    # 2. Dispatch
    dispatcher = EventbriteWebhookDispatcher()
    success = False
    error_details = None
    
    try:
        success = dispatcher.dispatch(action, api_url)
    except Exception as e:
        error_details = str(e)
        logger.error(f"[{trace_id}] Exception occurred during dispatch: {error_details}")
    
    duration = time.time() - start_time
    
    if success:
        # Mark as processed
        processed_repo.mark_as_processed(webhook_id, action, api_url)
        try:
            webhook_repo.collection.update_one(
                {"id": webhook_id}, 
                {"$set": {
                    "status": "Processed", 
                    "processed_at": datetime.utcnow(),
                    "processing_duration": duration,
                    "error_details": None
                }}
            )
        except Exception:
            pass
        logger.info(f"[{trace_id}] Processing completed. Webhook {webhook_id} successfully processed in {duration:.4f}s.")
    else:
        # Increment retry count
        if not error_details:
            error_details = "Dispatcher failed to handle action or returned False."
        try:
            webhook_repo.collection.update_one(
                {"id": webhook_id}, 
                {"$set": {
                    "status": "Failed",
                    "processed_at": datetime.utcnow(),
                    "processing_duration": duration,
                    "error_details": error_details
                }, "$inc": {"retry_count": 1}}
            )
        except Exception:
            pass
        logger.error(f"[{trace_id}] Processing failed. Webhook {webhook_id} failed with: {error_details}")


async def handle_webhook_starlette(request: Request) -> Response:
    trace_id = f"TR-{uuid.uuid4().hex[:8].upper()}"
    start_received = datetime.utcnow()
    
    # Secret Path Routing Validation
    configured_secret = getattr(settings, "EVENTBRITE_WEBHOOK_SECRET", "tribeiq_secret")
    secret_received = request.path_params.get("secret", "")
    
    if secret_received != configured_secret:
        logger.warning(f"[{trace_id}] Unauthorized webhook request: secret path mismatch.")
        return Response("Unauthorized webhook request.", status_code=401)

    # Read Payload
    try:
        body_bytes = await request.body()
        payload_str = body_bytes.decode('utf-8')
        payload = json.loads(payload_str)
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to parse JSON payload: {str(e)}")
        return Response("Invalid JSON payload.", status_code=400)

    api_url = payload.get("api_url")
    action = payload.get("config", {}).get("action")
    
    if not api_url or not action:
        logger.warning(f"[{trace_id}] Missing required parameters in payload: api_url={api_url}, action={action}")
        return Response("Missing required action or api_url parameters.", status_code=400)

    # Acknowledge Receipt immediately with HTTP 200 JSON
    response_data = {"status": "Acknowledged"}
    response = JSONResponse(response_data, status_code=200)
    
    logger.info(f"[{trace_id}] Webhook Received: {action} on {api_url}")

    # Queue / Save Job in MongoDB
    webhook_id = f"WB-{uuid.uuid4().hex[:8].upper()}"
    webhook_doc = {
        "id": webhook_id,
        "trace_id": trace_id,
        "api_url": api_url,
        "action": action,
        "status": "Pending",
        "retry_count": 0,
        "received_at": start_received,
        "processed_at": None,
        "processing_duration": 0.0,
        "error_details": None,
        "raw_payload": payload_str,
        "payload": payload
    }
    
    try:
        repo = EventbriteWebhookRepository()
        repo.insert(webhook_doc)
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to queue webhook in MongoDB: {str(e)}")

    # Asynchronously dispatch processing to background_job_service
    try:
        background_job_service.enqueue(process_webhook_async, webhook_id, action, api_url, trace_id)
        logger.info(f"[{trace_id}] Enqueued webhook job in background service (Webhook ID: {webhook_id})")
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to enqueue background job: {str(e)}")

    return response

# Starlette application for webhook endpoint initialized with Route list
webhook_api = Starlette(routes=[
    Route("/{secret}", handle_webhook_starlette, methods=["POST"])
])

def is_webhook_reachable() -> bool:
    """
    Verifies if the webhook endpoint route is active and mounted correctly.
    """
    try:
        for route in webhook_api.routes:
            if hasattr(route, "path") and route.path == "/{secret}":
                return True
    except Exception:
        pass
    return False
