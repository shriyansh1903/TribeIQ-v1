"""
===========================================================
TribeIQ LLM Client
===========================================================

NVIDIA API client for Mistral Medium 3.5 128B.

Responsibilities:
1. Read API configuration from environment variables
2. Send structured chat-completion requests
3. Request JSON-only responses
4. Parse and validate provider responses
5. Fail safely without breaking recommendations
===========================================================
"""

import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

import requests


load_dotenv()


# ===========================================================
# Configuration
# ===========================================================

NVIDIA_API_URL = (
    "https://integrate.api.nvidia.com/v1/chat/completions"
)

DEFAULT_MODEL = (
    "meta/llama-3.1-8b-instruct"
)

DEFAULT_TIMEOUT_SECONDS = 90

DEFAULT_MAX_TOKENS = 4096

DEFAULT_TEMPERATURE = 0.1

DEFAULT_TOP_P = 0.9


# ===========================================================
# Exceptions
# ===========================================================

class LLMClientError(Exception):
    pass


class LLMConfigurationError(LLMClientError):
    pass


class LLMRequestError(LLMClientError):
    pass


class LLMResponseError(LLMClientError):
    pass


# ===========================================================
# Helpers
# ===========================================================

def get_api_key() -> str:

    api_key = os.getenv(
        "NVIDIA_API_KEY",
        ""
    ).strip()

    if not api_key:

        raise LLMConfigurationError(
            "NVIDIA_API_KEY is not configured."
        )

    return api_key


def get_model_name() -> str:

    return os.getenv(
        "NVIDIA_MODEL",
        DEFAULT_MODEL
    ).strip() or DEFAULT_MODEL


def extract_json_text(
    content: Any
) -> str:

    if isinstance(content, dict):

        return json.dumps(content)

    if not isinstance(content, str):

        raise LLMResponseError(
            "LLM response content is not valid text."
        )

    text = content.strip()

    if text.startswith("```json"):

        text = text[7:]

    elif text.startswith("```"):

        text = text[3:]

    if text.endswith("```"):

        text = text[:-3]

    return text.strip()


def parse_json_content(
    content: Any
) -> Dict[str, Any]:

    text = extract_json_text(
        content
    )

    try:

        parsed = json.loads(text)

    except json.JSONDecodeError as error:

        raise LLMResponseError(
            "LLM returned invalid JSON."
        ) from error

    if not isinstance(parsed, dict):

        raise LLMResponseError(
            "LLM JSON response must be an object."
        )

    return parsed


# ===========================================================
# Client
# ===========================================================

class NVIDIAClient:

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS
    ):

        self.api_key = (
            api_key.strip()
            if isinstance(api_key, str)
            else get_api_key()
        )

        if not self.api_key:

            raise LLMConfigurationError(
                "NVIDIA API key is empty."
            )

        self.model = (
            model.strip()
            if isinstance(model, str) and model.strip()
            else get_model_name()
        )

        self.timeout = max(
            1,
            int(timeout)
        )

    # =======================================================
    # Headers
    # =======================================================

    def _headers(self) -> Dict[str, str]:

        return {
            "Authorization":
                f"Bearer {self.api_key}",
            "Content-Type":
                "application/json",
            "Accept":
                "application/json"
        }

    # =======================================================
    # Request Payload
    # =======================================================

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> Dict[str, Any]:

        return {
            "model":
                self.model,
            "messages":
                messages,
            "max_tokens":
                max_tokens,
            "temperature":
                temperature,
            "top_p":
                top_p,
            "stream":
                False,
            "response_format": {
                "type": "json_object"
            }
        }

    # =======================================================
    # Completion
    # =======================================================

    def complete_json(
        self,
        system_prompt: str,
        user_payload: Dict[str, Any],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P
    ) -> Dict[str, Any]:

        if not isinstance(
            user_payload,
            dict
        ):

            raise LLMRequestError(
                "user_payload must be a dictionary."
            )

        messages = [
            {
                "role": "system",
                "content": str(
                    system_prompt
                ).strip()
            },
            {
                "role": "user",
                "content": json.dumps(
                    user_payload,
                    ensure_ascii=False,
                    separators=(",", ":")
                )
            }
        ]

        payload = self._build_payload(
            messages=messages,
            max_tokens=max(
                1,
                int(max_tokens)
            ),
            temperature=max(
                0.0,
                float(temperature)
            ),
            top_p=max(
                0.0,
                min(
                    float(top_p),
                    1.0
                )
            )
        )

        try:

            response = requests.post(
                NVIDIA_API_URL,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout
            )

        except requests.RequestException as error:

            raise LLMRequestError(
                f"NVIDIA API request failed: {error}"
            ) from error

        if response.status_code >= 400:

            raise LLMRequestError(
                "NVIDIA API returned "
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        try:

            response_data = response.json()

        except ValueError as error:

            raise LLMResponseError(
                "NVIDIA API returned invalid JSON."
            ) from error

        choices = response_data.get(
            "choices",
            []
        )

        if not choices:

            raise LLMResponseError(
                "NVIDIA API returned no choices."
            )

        message = choices[0].get(
            "message",
            {}
        )

        content = message.get(
            "content"
        )

        result = parse_json_content(
            content
        )

        result.setdefault(
            "model",
            response_data.get(
                "model",
                self.model
            )
        )

        return result


# ===========================================================
# Safe Factory
# ===========================================================

def create_client() -> Optional[NVIDIAClient]:

    try:

        return NVIDIAClient()

    except LLMConfigurationError:

        return None