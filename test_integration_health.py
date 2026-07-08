"""
===========================================================
TribeIQ Integration Health Test
===========================================================
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from integration_health import get_integration_health


def run_test():

    print(
        "Testing TribeIQ integration health...\n"
    )

    health = get_integration_health()

    assert isinstance(
        health,
        dict
    )

    assert health.get(
        "healthy"
    ) is True, (
        "Integration health check failed: "
        + " | ".join(
            health.get(
                "errors",
                []
            )
        )
    )

    assert health.get(
        "resident_count",
        0
    ) > 0

    assert health.get(
        "property_count",
        0
    ) > 0

    assert health.get(
        "event_count",
        0
    ) > 0

    print(
        "Integration health test passed.\n"
    )

    print(
        f"Residents: "
        f"{health['resident_count']}"
    )

    print(
        f"Properties: "
        f"{health['property_count']}"
    )

    print(
        f"Events: "
        f"{health['event_count']}"
    )

    print(
        f"History records: "
        f"{health['history_count']}"
    )

    print(
        "\nTribeIQ integration is healthy."
    )


if __name__ == "__main__":

    run_test()