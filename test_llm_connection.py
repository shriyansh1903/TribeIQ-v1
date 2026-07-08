"""
===========================================================
TribeIQ NVIDIA LLM Connection Test
===========================================================
"""

import sys
from pathlib import Path


# ===========================================================
# Project Paths
# ===========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================
# Project Imports
# ===========================================================

from intelligence.llm_client import (
    NVIDIAClient,
    LLMClientError
)


# ===========================================================
# Test
# ===========================================================

def run_test():

    print(
        "Testing NVIDIA LLM connection...\n"
    )

    try:

        client = NVIDIAClient()

        response = client.complete_json(
            system_prompt=(
                "Return valid JSON only."
            ),
            user_payload={
                "task":
                    "Return a connection test response.",
                "required_response": {
                    "status": "connected",
                    "message":
                        "TribeIQ LLM connection successful"
                }
            },
            max_tokens=200,
            temperature=0.0
        )

        assert isinstance(
            response,
            dict
        )

        print(
            "LLM connection test passed."
        )

        print(
            f"Model: {client.model}"
        )

        print(
            f"Response: {response}"
        )

    except LLMClientError as error:

        print(
            "LLM connection test failed."
        )

        print(
            f"Error: {error}"
        )

        raise


if __name__ == "__main__":

    run_test()