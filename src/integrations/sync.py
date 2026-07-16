import json
import time
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

from .warden_client import WardenClient
from .mapper import WardenMapper

class WardenSyncEngine:
    """
    Manages synchronization of Warden API endpoints, caching raw JSON,
    mapping data, cleaning data, updating local datasets, and refreshing downstream pipelines.
    """
    def __init__(self, client: Optional[WardenClient] = None):
        self.client = client or WardenClient()
        self.project_root = Path(__file__).resolve().parents[2]
        self.raw_cache_dir = self.project_root / "outputs" / "raw"
        self.status_file = self.project_root / "data" / "warden_sync_status.json"
        
        self.raw_cache_dir.mkdir(parents=True, exist_ok=True)

    def _save_raw_json(self, name: str, data: Any) -> None:
        """
        Saves raw JSON response to outputs/raw/ directory for audit trail.
        """
        cache_path = self.raw_cache_dir / f"{name}.json"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def load_sync_status(self) -> Dict[str, Any]:
        """
        Loads the audit tracking metadata of the last synchronization.
        """
        if self.status_file.exists():
            try:
                with open(self.status_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "status": "Never Synced",
            "last_sync_time": "N/A",
            "residents_synced": 0,
            "properties_synced": 0,
            "bookings_synced": 0,
            "health": "Unknown"
        }

    def _save_sync_status(self, status_data: Dict[str, Any]) -> None:
        """
        Saves the sync status metadata.
        """
        try:
            with open(self.status_file, "w") as f:
                json.dump(status_data, f, indent=4)
        except Exception:
            pass

    def sync_properties(self) -> Dict[str, Any]:
        """
        Synchronizes property listings, room types, and bed availability.
        """
        status = self.load_sync_status()
        try:
            raw_props = self.client.get_properties()
            self._save_raw_json("properties", raw_props)
            
            raw_room_types = self.client.get_room_types()
            self._save_raw_json("room_types", raw_room_types)
            
            raw_beds = self.client.get_bed_availability()
            self._save_raw_json("bed_availability", raw_beds)

            # Update status
            status["properties_synced"] = len(raw_props)
            status["health"] = "Healthy"
            status["status"] = "Success"
            status["last_sync_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save_sync_status(status)
            return {"success": True, "count": len(raw_props)}
        except Exception as e:
            status["status"] = f"Failed Properties Sync: {str(e)}"
            self._save_sync_status(status)
            return {"success": False, "error": str(e)}

    def sync_bookings(self) -> Dict[str, Any]:
        """
        Synchronizes bookings, room assignments, and upcoming arrivals/departures.
        """
        status = self.load_sync_status()
        try:
            raw_bookings = self.client.get_bookings()
            self._save_raw_json("bookings", raw_bookings)

            status["bookings_synced"] = len(raw_bookings)
            status["health"] = "Healthy"
            status["status"] = "Success"
            status["last_sync_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save_sync_status(status)
            return {"success": True, "count": len(raw_bookings)}
        except Exception as e:
            status["status"] = f"Failed Bookings Sync: {str(e)}"
            self._save_sync_status(status)
            return {"success": False, "error": str(e)}

    def sync_residents(self) -> Dict[str, Any]:
        """
        Synchronizes residents, transforms them into the schema, and saves to data/Residents.csv.
        """
        status = self.load_sync_status()
        try:
            raw_residents = self.client.get_residents()
            self._save_raw_json("residents", raw_residents)
            
            # Fetch bookings as well to perform join mapping
            raw_bookings = self.client.get_bookings()
            self._save_raw_json("bookings", raw_bookings)
            
            # Map raw data to Residents.csv schema
            df_mapped = WardenMapper.map_to_residents_dataframe(raw_residents, raw_bookings)
            
            # Save mapped dataframe to local data/Residents.csv
            residents_csv_path = self.project_root / "data" / "Residents.csv"
            residents_csv_path.parent.mkdir(parents=True, exist_ok=True)
            df_mapped.to_csv(residents_csv_path, index=False)

            status["residents_synced"] = len(raw_residents)
            status["health"] = "Healthy"
            status["status"] = "Success"
            status["last_sync_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save_sync_status(status)
            return {"success": True, "count": len(raw_residents)}
        except Exception as e:
            status["status"] = f"Failed Residents Sync: {str(e)}"
            self._save_sync_status(status)
            return {"success": False, "error": str(e)}

    def sync_everything(self) -> Dict[str, Any]:
        """
        Full synchronization run. Syncs residents, bookings, properties, payments, and rebuilds pipelines.
        """
        status = self.load_sync_status()
        try:
            # 1. Sync properties
            raw_props = self.client.get_properties()
            self._save_raw_json("properties", raw_props)
            
            raw_room_types = self.client.get_room_types()
            self._save_raw_json("room_types", raw_room_types)
            
            raw_beds = self.client.get_bed_availability()
            self._save_raw_json("bed_availability", raw_beds)

            # 2. Sync bookings
            raw_bookings = self.client.get_bookings()
            self._save_raw_json("bookings", raw_bookings)

            # 3. Sync residents
            raw_residents = self.client.get_residents()
            self._save_raw_json("residents", raw_residents)
            
            # 4. Map and save Residents database
            df_mapped = WardenMapper.map_to_residents_dataframe(raw_residents, raw_bookings)
            residents_csv_path = self.project_root / "data" / "Residents.csv"
            residents_csv_path.parent.mkdir(parents=True, exist_ok=True)
            df_mapped.to_csv(residents_csv_path, index=False)

            # 5. Sync payments and transactions (future financials preparation)
            raw_payments = self.client.get_payments()
            self._save_raw_json("payments", raw_payments)
            raw_txns = self.client.get_transactions()
            self._save_raw_json("transactions", raw_txns)

            # 6. Rebuild downstream databases/profiles using cleaners & generators
            import cleaner
            import feature_engineering
            import profile_generator

            cleaner.run()
            feature_engineering.run()
            profile_generator.run()

            # Update and save status
            status["properties_synced"] = len(raw_props)
            status["bookings_synced"] = len(raw_bookings)
            status["residents_synced"] = len(raw_residents)
            status["health"] = "Healthy"
            status["status"] = "Success"
            status["last_sync_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save_sync_status(status)
            
            return {"success": True, "details": status}
        except Exception as e:
            status["status"] = f"Failed Full Sync: {str(e)}"
            self._save_sync_status(status)
            return {"success": False, "error": str(e)}
