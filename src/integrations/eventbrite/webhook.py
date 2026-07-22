import json
import threading
import uuid
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import Optional

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

class WebhookHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to stdout
        pass

    def do_POST(self):
        trace_id = f"TR-{uuid.uuid4().hex[:8].upper()}"
        start_received = datetime.utcnow()
        
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Secret Token path routing validation: path should end with /<secret>
        configured_secret = getattr(settings, "EVENTBRITE_WEBHOOK_SECRET", "tribeiq_secret")
        
        # We expect URL to match: /webhook/{configured_secret}
        secret_received = ""
        
        # Extract secret from path /webhook/<secret>
        path_parts = [p for p in path.split("/") if p]
        if len(path_parts) >= 2 and path_parts[0] == "webhook":
            secret_received = path_parts[1]
        else:
            # Fallback checks (e.g. query param, custom headers)
            query_params = parse_qs(parsed_url.query)
            secret_received = query_params.get("secret", [""])[0]
            if not secret_received:
                secret_received = self.headers.get("X-Webhook-Secret", "")
        
        # Check authorization
        if (not path.startswith("/webhook")) or (secret_received != configured_secret):
            logger.warning(f"[{trace_id}] Unauthorized webhook request to {path}. Expected secret matching configured webhook secret.")
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized webhook request.")
            return

        # Read Payload
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            payload_str = post_data.decode('utf-8')
            payload = json.loads(payload_str)
        except Exception as e:
            logger.error(f"[{trace_id}] Failed to parse JSON payload: {str(e)}")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON payload.")
            return

        api_url = payload.get("api_url")
        action = payload.get("config", {}).get("action")
        
        if not api_url or not action:
            logger.warning(f"[{trace_id}] Missing required parameters in payload: api_url={api_url}, action={action}")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing required action or api_url parameters.")
            return

        # Acknowledge Receipt immediately with HTTP 200
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "Acknowledged"}).encode('utf-8'))
        
        logger.info(f"[{trace_id}] Webhook Received: {action} on {api_url}")

        # Queue / Save Job in MongoDB with all required fields
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

_server = None

def start_webhook_receiver(host="0.0.0.0", port=8080):
    global _server
    if _server is not None:
        return
        
    def serve():
        global _server
        try:
            _server = HTTPServer((host, port), WebhookHTTPHandler)
            logger.info(f"Eventbrite Webhook HTTP Server started on http://{host}:{port}/webhook")
            _server.serve_forever()
        except Exception as e:
            logger.error(f"Failed to start Eventbrite Webhook Server: {str(e)}")

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()
