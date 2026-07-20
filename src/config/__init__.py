import sys
from pathlib import Path
from src.config.settings import settings, logger

# Establish backward compatibility with the legacy src/config.py module
try:
    import importlib.util
    legacy_config_path = Path(__file__).resolve().parents[1] / "config.py"
    if legacy_config_path.exists():
        spec = importlib.util.spec_from_file_location("legacy_config", str(legacy_config_path))
        legacy_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy_config)
        # Expose all variables from the legacy config.py module
        for attr in dir(legacy_config):
            if not attr.startswith("__"):
                globals()[attr] = getattr(legacy_config, attr)
except Exception as e:
    logger.warning(f"Failed to load backward-compatible legacy config: {str(e)}")
