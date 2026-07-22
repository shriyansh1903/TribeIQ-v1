import time
import requests
from typing import Dict, Any, Optional
from src.config import settings, logger

class EventbriteClient:
    def __init__(self):
        self.token = getattr(settings, "EVENTBRITE_PRIVATE_TOKEN", "MOCK_TOKEN")
        self.base_url = getattr(settings, "EVENTBRITE_API_BASE_URL", "https://www.eventbriteapi.com/v3").rstrip("/")
        self.timeout = 10
        self.max_retries = 3

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        retry_count = 0
        backoff = 1.0

        while retry_count < self.max_retries:
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params,
                    timeout=self.timeout
                )

                # Rate Limit Handling (HTTP 429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", backoff))
                    logger.warning(f"Eventbrite API Rate Limited (429). Retrying after {retry_after}s...")
                    time.sleep(retry_after)
                    retry_count += 1
                    backoff *= 2
                    continue

                # Raise for standard errors
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                logger.error(f"Eventbrite HTTP Error: {str(e)}")
                if response.status_code == 404:
                    return {"error": "Not Found", "status_code": 404}
                if response.status_code in [401, 403]:
                    return {"error": "Unauthorized", "status_code": response.status_code}
                
                retry_count += 1
                time.sleep(backoff)
                backoff *= 2
            except requests.exceptions.RequestException as e:
                logger.error(f"Eventbrite Network Request Error: {str(e)}")
                retry_count += 1
                time.sleep(backoff)
                backoff *= 2

        raise Exception("Max retries exceeded for Eventbrite API connection.")

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", path, params=params)

    def post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", path, data=data)

    def patch(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PATCH", path, data=data)

    def delete(self, path: str) -> Dict[str, Any]:
        return self._request("DELETE", path)
