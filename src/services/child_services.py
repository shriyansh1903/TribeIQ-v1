import pandas as pd
from typing import List, Dict, Any, Optional
from src.database import db_manager
from src.config import settings, logger
from src.repositories import (
    PropertiesRepository, ResidentsRepository, EventsRepository, CalendarEventsRepository,
    RecommendationsRepository, VendorsRepository, MaterialsRepository, StallsRepository,
    ExternalEventsRepository, SettingsRepository
)

# Legacy imports for fallback
import src.integrations.master_data_db as legacy_master_db
import src.integrations.calendar_db as legacy_calendar_db
import src.integrations.vendor_db as legacy_vendor_db
import src.integrations.material_db as legacy_material_db
import src.integrations.stall_db as legacy_stall_db
import src.integrations.external_events_db as legacy_external_db

class PropertyService:
    def __init__(self):
        self.repo = PropertiesRepository()

    def get_properties(self) -> pd.DataFrame:
        if db_manager.ping_check():
            try:
                docs = self.repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error fetching properties from MongoDB: {str(e)}")
        # Fallback
        return legacy_master_db.get_properties_df()

    def save_properties(self, df: pd.DataFrame) -> bool:
        if db_manager.ping_check():
            try:
                # Clear existing and insert new
                self.repo.collection.delete_many({})
                records = df.to_dict(orient="records")
                for r in records:
                    self.repo.insert(r)
                return True
            except Exception as e:
                logger.error(f"Error saving properties to MongoDB: {str(e)}")
        # Fallback
        return legacy_master_db.save_properties_df(df)

class ResidentService:
    def __init__(self):
        self.repo = ResidentsRepository()

    def get_residents(self) -> pd.DataFrame:
        if db_manager.ping_check():
            try:
                docs = self.repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error fetching residents from MongoDB: {str(e)}")
        # Fallback
        import src.loader as loader
        return loader.load_residents()

class CalendarEventService:
    def __init__(self):
        self.repo = CalendarEventsRepository()

    def get_calendar_events(self) -> pd.DataFrame:
        if db_manager.ping_check():
            try:
                docs = self.repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error fetching calendar events from MongoDB: {str(e)}")
        # Fallback
        return legacy_calendar_db.load_calendar_events_csv()

    def save_calendar_event(self, event_data: Dict[str, Any]) -> bool:
        if db_manager.ping_check():
            try:
                event_id = event_data.get("Event ID")
                if event_id:
                    existing = self.repo.collection.find_one({"Event ID": event_id})
                    if existing:
                        self.repo.collection.update_one({"Event ID": event_id}, {"$set": event_data})
                        return True
                self.repo.insert(event_data)
                return True
            except Exception as e:
                logger.error(f"Error saving calendar event to MongoDB: {str(e)}")
        # Fallback
        return legacy_calendar_db.save_calendar_event(event_data)

    def delete_calendar_event(self, event_id: str) -> bool:
        if db_manager.ping_check():
            try:
                self.repo.collection.delete_one({"Event ID": event_id})
                return True
            except Exception as e:
                logger.error(f"Error deleting calendar event from MongoDB: {str(e)}")
        # Fallback
        return legacy_calendar_db.delete_calendar_event(event_id)

class VendorService:
    def __init__(self):
        self.repo = VendorsRepository()

    def get_vendors(self) -> pd.DataFrame:
        if db_manager.ping_check():
            try:
                docs = self.repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error fetching vendors from MongoDB: {str(e)}")
        # Fallback
        return legacy_vendor_db.load_vendors_csv()

    def add_vendor(self, vendor_data: Dict[str, Any]) -> bool:
        if db_manager.ping_check():
            try:
                self.repo.insert(vendor_data)
                return True
            except Exception as e:
                logger.error(f"Error adding vendor to MongoDB: {str(e)}")
        # Fallback
        return legacy_vendor_db.add_vendor(vendor_data)

    def edit_vendor(self, vendor_id: str, vendor_data: Dict[str, Any]) -> bool:
        if db_manager.ping_check():
            try:
                self.repo.collection.update_one({"Vendor ID": vendor_id}, {"$set": vendor_data})
                return True
            except Exception as e:
                logger.error(f"Error updating vendor in MongoDB: {str(e)}")
        # Fallback
        return legacy_vendor_db.edit_vendor(vendor_id, vendor_data)

    def delete_or_deactivate_vendor(self, vendor_id: str, action: str = "deactivate") -> bool:
        if db_manager.ping_check():
            try:
                if action == "delete":
                    self.repo.collection.delete_one({"Vendor ID": vendor_id})
                else:
                    self.repo.collection.update_one({"Vendor ID": vendor_id}, {"$set": {"Active / Inactive Status": "Inactive"}})
                return True
            except Exception as e:
                logger.error(f"Error deleting/deactivating vendor in MongoDB: {str(e)}")
        # Fallback
        return legacy_vendor_db.delete_or_deactivate_vendor(vendor_id, action)

class MaterialService:
    def __init__(self):
        self.repo = MaterialsRepository()

    def get_materials(self) -> pd.DataFrame:
        if db_manager.ping_check():
            try:
                docs = self.repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error fetching materials from MongoDB: {str(e)}")
        # Fallback
        return legacy_material_db.load_materials_csv()

class StallService:
    def __init__(self):
        self.repo = StallsRepository()

    def get_stalls(self) -> pd.DataFrame:
        if db_manager.ping_check():
            try:
                docs = self.repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error fetching stalls from MongoDB: {str(e)}")
        # Fallback
        return legacy_stall_db.load_stalls_csv()

class ExternalEventService:
    def __init__(self):
        self.repo = ExternalEventsRepository()

    def get_external_events(self) -> pd.DataFrame:
        if db_manager.ping_check():
            try:
                docs = self.repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error fetching external events from MongoDB: {str(e)}")
        # Fallback
        return legacy_external_db.load_external_events_csv()

    def save_external_event(self, event_data: Dict[str, Any]) -> str:
        if db_manager.ping_check():
            try:
                event_id = event_data.get("Event ID")
                if event_id:
                    existing = self.repo.collection.find_one({"Event ID": event_id})
                    if existing:
                        self.repo.collection.update_one({"Event ID": event_id}, {"$set": event_data})
                        return event_id
                import uuid
                # Generate unique ID if not present
                if not event_id:
                    event_id = f"EXT-{uuid.uuid4().hex[:6].upper()}"
                    event_data["Event ID"] = event_id
                self.repo.insert(event_data)
                return event_id
            except Exception as e:
                logger.error(f"Error saving external event to MongoDB: {str(e)}")
        # Fallback
        return legacy_external_db.save_external_event(event_data)

    def delete_external_event(self, event_id: str) -> bool:
        if db_manager.ping_check():
            try:
                self.repo.collection.delete_one({"Event ID": event_id})
                return True
            except Exception as e:
                logger.error(f"Error deleting external event from MongoDB: {str(e)}")
        # Fallback
        return legacy_external_db.delete_external_event(event_id)

# Singleton instances of child services
property_service = PropertyService()
resident_service = ResidentService()
calendar_service = CalendarEventService()
vendor_service = VendorService()
material_service = MaterialService()
stall_service = StallService()
external_event_service = ExternalEventService()
