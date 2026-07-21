import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from src.config import settings, logger

class MongoManager:
    _instance = None
    _client = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MongoManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if client already established
        if self._client is not None:
            return
            
        try:
            logger.info("Initializing MongoDB client connection pool...")
            self._client = pymongo.MongoClient(
                settings.MONGO_URI,
                maxPoolSize=50,
                minPoolSize=0,
                serverSelectionTimeoutMS=5000
            )
            # Test ping on startup
            self.ping_check()
            logger.info("MongoDB client connected successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
            self._client = None

    def get_client(self) -> pymongo.MongoClient:
        return self._client

    def get_database(self, name: str = None) -> pymongo.database.Database:
        if self._client is None:
            return None
        db_name = name or settings.DATABASE_NAME
        return self._client[db_name]

    def get_collection(self, collection_name: str, db_name: str = None) -> pymongo.collection.Collection:
        db = self.get_database(db_name)
        if db is None:
            return None
        return db[collection_name]

    _last_ping_time = None
    _last_ping_result = False

    def ping_check(self) -> bool:
        if self._client is None:
            return False
            
        import time
        now = time.time()
        if self._last_ping_time is not None and (now - self._last_ping_time < 30):
            return self._last_ping_result
            
        try:
            # Send a ping command
            self._client.admin.command('ping')
            self._last_ping_result = True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"MongoDB ping check failed: {str(e)}")
            self._last_ping_result = False
        except Exception as e:
            logger.warning(f"MongoDB ping check encountered error: {str(e)}")
            self._last_ping_result = False
            
        self._last_ping_time = now
        return self._last_ping_result

# Global Singleton Manager
db_manager = MongoManager()
