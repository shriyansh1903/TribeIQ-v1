from src.config import settings
from src.database import db_manager

class HealthService:
    @staticmethod
    def get_app_version() -> str:
        return "v2.2.0 Platform Foundation"

    @staticmethod
    def get_environment() -> str:
        return settings.ENV

    @staticmethod
    def get_database_status() -> dict:
        is_connected = db_manager.ping_check()
        db_name = settings.DATABASE_NAME
        
        status = {
            "connected": is_connected,
            "database_name": db_name,
            "environment": settings.ENV,
            "collections": {}
        }
        
        if is_connected:
            try:
                db = db_manager.get_database()
                collections = db.list_collection_names()
                for coll in ["users", "properties", "residents", "events", "calendar_events", "recommendations", "vendors", "materials", "stalls", "external_events", "settings"]:
                    status["collections"][coll] = "Created" if coll in collections else "Missing"
            except Exception as e:
                status["error"] = str(e)
                
        return status
