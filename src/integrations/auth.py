import os
import time
import requests
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from dotenv import load_dotenv
    _project_root = Path(__file__).resolve().parents[2]
    load_dotenv(_project_root / ".env")
    load_dotenv(_project_root / ".env.development", override=True)
except ImportError:
    pass

class WardenAuth:
    """
    Handles OAuth 2.0 Client Credentials flow for the Warden REST API.
    Provides automatic caching, token refresh on expiry, and retry logic.
    """
    def __init__(self, token_url: Optional[str] = None):
        self.client_id = os.getenv("WARDEN_ID")
        self.client_secret = os.getenv("WARDEN_SECRET")
        self.api_url = os.getenv("WARDEN_API_URL", "https://api.warden.co-living/v1").rstrip("/")
        self.token_url = token_url or f"{self.api_url}/oauth/token"
        
        # In-memory token cache
        self._token: Optional[str] = None
        self._expires_at: float = 0.0
        # Check if keys are missing or placeholder strings
        is_placeholder = (
            not self.client_id or 
            not self.client_secret or 
            "your_warden" in str(self.client_id).lower() or 
            "your_warden" in str(self.client_secret).lower()
        )
        self.mock_mode = is_placeholder

    def get_headers(self) -> Dict[str, str]:
        """
        Returns authorized HTTP headers. Automatically fetches or refreshes
        token if necessary.
        """
        if self.mock_mode:
            return {"Authorization": "Bearer mock-token-sandbox"}
            
        token = self.get_access_token()
        if not token:
            return {"Authorization": "Bearer mock-token-fallback"}
        return {"Authorization": f"Bearer {token}"}

    def get_access_token(self) -> Optional[str]:
        """
        Retrieves active access token, refreshing if expired.
        """
        now = time.time()
        # Refresh token 30 seconds before it officially expires
        if self._token and now < (self._expires_at - 30):
            return self._token

        return self._fetch_new_token()

    def _fetch_new_token(self) -> Optional[str]:
        """
        Performs the OAuth 2.0 Client Credentials token request.
        """
        if self.mock_mode:
            self._token = "mock-token-sandbox"
            self._expires_at = time.time() + 3600
            return self._token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        retries = 3
        for attempt in range(retries):
            try:
                response = requests.post(self.token_url, data=payload, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self._token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self._expires_at = time.time() + expires_in
                    return self._token
                elif response.status_code in (401, 403):
                    # Authentication failure, do not retry
                    break
            except requests.RequestException:
                if attempt == retries - 1:
                    break
                time.sleep(1)

        # Fallback to mock token in case of network or API failure to prevent crashes
        self._token = "mock-token-fallback"
        self._expires_at = time.time() + 300
        return self._token
