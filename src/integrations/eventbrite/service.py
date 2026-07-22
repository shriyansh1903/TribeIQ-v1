import datetime
from typing import Dict, Any, List
from src.config import settings, logger
from src.integrations.eventbrite.client import EventbriteClient
from src.integrations.eventbrite.repository import EventbriteEventRepository, EventbriteWebhookRepository
from src.integrations.eventbrite.handlers import EventbriteWebhookHandlers
from src.integrations.provider import ExternalEventProvider, provider_registry

class EventbriteService(ExternalEventProvider):
    def __init__(self):
        self.client = EventbriteClient()
        self.event_repo = EventbriteEventRepository()
        self.webhook_repo = EventbriteWebhookRepository()
        self.handlers = EventbriteWebhookHandlers()
        self._cached_org_id = None

    @property
    def name(self) -> str:
        return "eventbrite"

    def get_organization_id(self) -> str:
        """
        Dynamically detects and caches the Eventbrite Organization ID.
        If the organization list is empty, falls back to using the User ID as the default organization context.
        """
        org_id = getattr(settings, "EVENTBRITE_ORGANIZATION_ID", None)
        if org_id and org_id != "MOCK_ORG" and str(org_id).strip().isdigit():
            return str(org_id).strip()
            
        if self._cached_org_id:
            return self._cached_org_id
            
        if self.client.token == "MOCK_TOKEN" or not self.client.token:
            return "No Eventbrite Organization Found"
            
        try:
            res = self.client.get("/users/me/organizations/")
            if isinstance(res, dict) and "error" in res:
                logger.error(f"Error querying organizations: {res.get('error')}")
            else:
                organizations = res.get("organizations", [])
                if organizations:
                    self._cached_org_id = str(organizations[0].get("id"))
                    logger.info(f"Discovered Eventbrite Organization ID dynamically: {self._cached_org_id}")
                    return self._cached_org_id

            # Fallback: Query user details and use User ID as Organization ID context
            user_res = self.client.get("/users/me/")
            if isinstance(user_res, dict) and "error" not in user_res:
                user_id = user_res.get("id")
                if user_id:
                    self._cached_org_id = str(user_id)
                    logger.info(f"Fallback: Discovered Eventbrite User ID dynamically for Org context: {self._cached_org_id}")
                    return self._cached_org_id

        except Exception as e:
            logger.error(f"Failed to dynamically discover Eventbrite organization/user context: {str(e)}")
            
        return "No Eventbrite Organization Found"

    def register_webhook(self, endpoint_url: str, actions: List[str] = None) -> Dict[str, Any]:
        """
        Registers a webhook endpoint with the Eventbrite REST API.
        """
        logger.info(f"Registering webhook endpoint {endpoint_url} on Eventbrite...")
        
        # URL Validation
        from urllib.parse import urlparse
        parsed = urlparse(endpoint_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid Webhook Target URL: '{endpoint_url}'. Scheme (http/https) and domain name are required.")

        org_id = self.get_organization_id()
        secret = getattr(settings, "EVENTBRITE_WEBHOOK_SECRET", "tribeiq_secret")
        
        # Append secret path routing parameter
        base_endpoint = endpoint_url.rstrip("/")
        full_endpoint = f"{base_endpoint}/{secret}"
        actions = actions or ["event.published", "event.updated", "event.unpublished", "order.placed", "attendee.updated"]
        
        payload = {
            "endpoint_url": full_endpoint,
            "actions": ",".join(actions),
            "event_filter": "all"
        }
        
        # Mock connection fallback if token is default or no organization is resolved
        if self.client.token == "MOCK_TOKEN" or org_id == "No Eventbrite Organization Found" or org_id == "MOCK_ORG":
            logger.info("Operating in Mock / Standby Mode. Registering mock webhook.")
            mock_id = "mock_web_123"
            doc = {
                "id": mock_id,
                "endpoint_url": full_endpoint,
                "actions": actions,
                "status": "Active",
                "registered_at": datetime.datetime.utcnow().isoformat() if "datetime" in globals() else None
            }
            # Save to MongoDB
            try:
                self.webhook_repo.collection.update_one({"id": mock_id}, {"$set": doc}, upsert=True)
            except Exception:
                pass
            return {"id": mock_id, "status": "Active", "actions": actions}

        try:
            # Post registration to Eventbrite API
            path = f"/organizations/{org_id}/webhooks/"
            response = self.client.post(path, payload)
            
            if "error" in response:
                error_msg = response.get("error")
                error_desc = response.get("details", {}).get("error_description")
                full_error = f"{error_msg} - {error_desc}" if error_desc else error_msg
                logger.error(f"Eventbrite webhook registration failed: {full_error}")
                raise Exception(f"Eventbrite API Error: {full_error}")
                
            webhook_id = response.get("id")
            
            # Save webhook state
            doc = {
                "id": webhook_id,
                "endpoint_url": full_endpoint,
                "actions": actions,
                "status": "Active",
                "registered_at": datetime.datetime.utcnow().isoformat() if "datetime" in globals() else None
            }
            self.webhook_repo.collection.update_one({"id": webhook_id}, {"$set": doc}, upsert=True)
            return response
        except Exception as e:
            logger.error(f"Failed to register webhook: {str(e)}")
            raise e

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        Lists registered webhooks from local DB or Eventbrite organization.
        """
        org_id = self.get_organization_id()
        if self.client.token == "MOCK_TOKEN" or org_id == "No Eventbrite Organization Found" or org_id == "MOCK_ORG":
            try:
                return list(self.webhook_repo.collection.find({}))
            except Exception:
                return []

        try:
            path = f"/organizations/{org_id}/webhooks/"
            res = self.client.get(path)
            if isinstance(res, dict) and "error" in res:
                # Fallback to local DB webhooks if the GET API endpoint is deprecated/failed
                logger.warning(f"Failed to list webhooks from API: {res.get('error')}. Falling back to local database.")
                return list(self.webhook_repo.collection.find({}))
            return res.get("webhooks", [])
        except Exception as e:
            logger.error(f"Failed to list webhooks: {str(e)}")
            try:
                return list(self.webhook_repo.collection.find({}))
            except Exception:
                return []

    def delete_webhook(self, webhook_id: str) -> bool:
        """
        Deletes a registered webhook from Eventbrite.
        """
        logger.info(f"Deleting Eventbrite webhook ID: {webhook_id}")
        org_id = self.get_organization_id()
        
        # Local state cleanup
        try:
            self.webhook_repo.collection.delete_one({"id": webhook_id})
        except Exception:
            pass

        if self.client.token == "MOCK_TOKEN" or org_id == "No Eventbrite Organization Found" or org_id == "MOCK_ORG":
            return True

        try:
            res = self.client.delete(f"/webhooks/{webhook_id}/")
            if isinstance(res, dict) and "error" in res:
                logger.warning(f"Eventbrite API webhook delete returned error: {res.get('error')}. Local deletion completed.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete webhook from Eventbrite API: {str(e)}")
            return True

    def sync_all_events(self) -> Dict[str, Any]:
        """
        Performs manual sync of all published events from Eventbrite organization.
        """
        logger.info("Executing manual synchronization of Eventbrite events...")
        org_id = self.get_organization_id()
        
        if self.client.token == "MOCK_TOKEN" or org_id == "No Eventbrite Organization Found" or org_id == "MOCK_ORG":
            logger.info("Eventbrite Token missing or organization not set. Manual sync operating in standby.")
            return {"status": "Standby", "synced_count": 0}

        try:
            path = f"/organizations/{org_id}/events/"
            res = self.client.get(path)
            events = res.get("events", [])
            
            synced_count = 0
            for ev in events:
                # Trigger handlers to published format
                api_url = f"https://www.eventbriteapi.com/v3/events/{ev.get('id')}/"
                self.handlers.handle_event_published(api_url)
                synced_count += 1
                
            return {"status": "Completed", "synced_count": synced_count}
        except Exception as e:
            logger.error(f"Failed to sync all events: {str(e)}")
            return {"status": "Error", "message": str(e), "synced_count": 0}
            
# Singleton service instance
eventbrite_service = EventbriteService()
provider_registry.register(eventbrite_service)
