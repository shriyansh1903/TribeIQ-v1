import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure Central Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).resolve().parents[2] / "outputs" / "platform.log", mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("TribeIQPlatform")

class Settings:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        
        # Load environment order:
        # 1. System/Pre-loaded env
        # 2. .env
        # 3. .env.production or .env.development based on TRIBEIQ_ENV or ENV
        # 4. .env.example
        
        # Initially load general .env
        load_dotenv(self.project_root / ".env")
        
        # Determine environment
        env = os.getenv("ENV", os.getenv("TRIBEIQ_ENV", "development")).lower()
        if env == "production":
            load_dotenv(self.project_root / ".env.production", override=True)
            logger.info("Loaded production environment configurations.")
        else:
            load_dotenv(self.project_root / ".env.development", override=True)
            logger.info("Loaded development environment configurations.")
            
        # Centralized Properties
        self.MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/tribeiq")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME", "TribeIQ")
        self.SESSION_SECRET = os.getenv("SESSION_SECRET", "default-secret-session-key")
        
        try:
            self.BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))
        except ValueError:
            self.BCRYPT_ROUNDS = 12
            
        self.APP_NAME = os.getenv("APP_NAME", "TribeIQ")
        self.ENV = os.getenv("ENV", "development")
        self.TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
        
        # Parse feature flags
        self.FEATURE_FLAGS = {}
        flags_str = os.getenv("FEATURE_FLAGS", "")
        if flags_str:
            for part in flags_str.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    self.FEATURE_FLAGS[k.strip()] = v.strip().lower() in ("true", "1", "yes")
        
        # Eventbrite Settings Centralization
        self.EVENTBRITE_PRIVATE_TOKEN = os.getenv("EVENTBRITE_PRIVATE_TOKEN", "MOCK_TOKEN")
        self.EVENTBRITE_API_BASE_URL = os.getenv("EVENTBRITE_API_BASE_URL", "https://www.eventbriteapi.com/v3")

# Singleton instance
settings = Settings()
