import json
import time
import os
import shutil
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

from .warden_client import WardenClient
from .mapper import WardenMapper

# -----------------------------------------------------------
# Setup warden_sync.log with security masking
# -----------------------------------------------------------
log_dir = Path("outputs/logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "warden_sync.log"

logger = logging.getLogger("warden_sync")
logger.setLevel(logging.INFO)
logger.handlers = []

file_handler = logging.FileHandler(log_file, encoding="utf-8")
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def safe_log(msg: str, level: str = "info"):
    masked_msg = msg
    for secret_env in ["WARDEN_SECRET", "WARDEN_ID"]:
        secret_val = os.getenv(secret_env)
        if secret_val and secret_val in masked_msg:
            masked_msg = masked_msg.replace(secret_val, "********")
    
    # Mask any Bearer tokens
    if "Bearer " in masked_msg:
        import re
        masked_msg = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer ********", masked_msg)

    if level.lower() == "info":
        logger.info(masked_msg)
    elif level.lower() == "warning":
        logger.warning(masked_msg)
    elif level.lower() == "error":
        logger.error(masked_msg)


class WardenSyncEngine:
    """
    Production-ready synchronization engine for the Warden API.
    Provides auto-sync status checks, change detection, timestamped backups,
    safe transaction rollbacks, and secure performance auditing.
    """
    def __init__(self, client: Optional[WardenClient] = None):
        self.client = client or WardenClient()
        self.project_root = Path(__file__).resolve().parents[2]
        self.raw_cache_dir = self.project_root / "outputs" / "raw"
        self.status_file = self.project_root / "data" / "warden_sync_status.json"
        
        self.raw_cache_dir.mkdir(parents=True, exist_ok=True)

    def _save_raw_json(self, name: str, data: Any) -> None:
        cache_path = self.raw_cache_dir / f"{name}.json"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            safe_log(f"Failed to cache raw json {name}: {str(e)}", "warning")

    def load_sync_status(self) -> Dict[str, Any]:
        if self.status_file.exists():
            try:
                with open(self.status_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "status": "Offline Mode",
            "last_successful_sync": "N/A",
            "last_failed_sync": "N/A",
            "sync_duration_seconds": 0.0,
            "residents_imported": 0,
            "properties_imported": 0,
            "bookings_imported": 0,
            "health": "Unknown",
            "api_response_time_ms": 0,
            "auto_sync_on_startup": False
        }

    def save_sync_status(self, status_data: Dict[str, Any]) -> None:
        try:
            with open(self.status_file, "w") as f:
                json.dump(status_data, f, indent=4)
        except Exception as e:
            safe_log(f"Failed to save sync status: {str(e)}", "error")

    def test_connection(self) -> Dict[str, Any]:
        """
        Runs a lightweight connection check without performing a full sync.
        """
        start_time = time.time()
        safe_log("Starting connection test to Warden API...")
        try:
            # Fetch lightweight properties endpoint
            props = self.client.get_properties()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Update API response status
            status = self.load_sync_status()
            status["health"] = "Healthy"
            status["api_response_time_ms"] = response_time_ms
            status["status"] = "Connected"
            self.save_sync_status(status)
            
            safe_log(f"Connection test successful. Response time: {response_time_ms} ms.")
            return {"success": True, "response_time_ms": response_time_ms}
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            safe_log(f"Connection test failed: {str(e)}", "error")
            
            status = self.load_sync_status()
            status["health"] = "Unhealthy"
            status["status"] = "Connection Failed"
            self.save_sync_status(status)
            return {"success": False, "error": str(e), "response_time_ms": response_time_ms}

    def _create_backup(self) -> None:
        residents_csv_path = self.project_root / "data" / "Residents.csv"
        if not residents_csv_path.exists():
            return
            
        backup_dir = self.project_root / "outputs" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y-%m-%d_%H%M")
        backup_file = backup_dir / f"Residents_{timestamp}.csv"
        
        try:
            shutil.copy2(residents_csv_path, backup_file)
            safe_log(f"Created backup of Residents.csv at {backup_file.name}")
            
            # Prune to keep only latest 20 backups
            backups = sorted(list(backup_dir.glob("Residents_*.csv")), key=lambda p: p.stat().st_mtime)
            if len(backups) > 20:
                for old_backup in backups[:-20]:
                    old_backup.unlink()
                    safe_log(f"Pruned old backup file: {old_backup.name}")
        except Exception as e:
            safe_log(f"Failed during backup creation/pruning: {str(e)}", "warning")

    def _has_changed(self, old_path: Path, new_df: pd.DataFrame) -> bool:
        if not old_path.exists():
            return True
        try:
            old_df = pd.read_csv(old_path)
            # Remove non-content tracking columns to verify if core resident attributes changed
            ignore_cols = ["Last Modified Timestamp", "Created Timestamp", "Logged Timestamp", "Logged Date", "Logged Time"]
            old_cmp = old_df.drop(columns=ignore_cols, errors="ignore")
            new_cmp = new_df.drop(columns=ignore_cols, errors="ignore")
            return not old_cmp.equals(new_cmp)
        except Exception:
            return True

    def sync_everything(self, progress_callback=None) -> Dict[str, Any]:
        """
        Executes safe sync transaction. Supports UI progress reporting and automatic rollback.
        """
        start_sync_time = time.time()
        safe_log("Synchronization process started.")
        status = self.load_sync_status()
        
        residents_csv_path = self.project_root / "data" / "Residents.csv"
        backup_created = False
        temp_backup_path = self.project_root / "data" / "Residents.csv.bak"

        try:
            if progress_callback:
                progress_callback("Authenticating...")
            
            # Reuses token via client auth cache
            token = self.client.auth.get_access_token()
            if not token:
                raise Exception("Failed to retrieve API access token.")

            if progress_callback:
                progress_callback("Downloading Properties...")
            raw_props = self.client.get_properties()
            self._save_raw_json("properties", raw_props)
            
            # Secondary property configs
            raw_room_types = self.client.get_room_types()
            self._save_raw_json("room_types", raw_room_types)
            raw_beds = self.client.get_bed_availability()
            self._save_raw_json("bed_availability", raw_beds)

            if progress_callback:
                progress_callback("Downloading Bookings...")
            raw_bookings = self.client.get_bookings()
            self._save_raw_json("bookings", raw_bookings)

            if progress_callback:
                progress_callback("Downloading Residents...")
            raw_residents = self.client.get_residents()
            self._save_raw_json("residents", raw_residents)

            if progress_callback:
                progress_callback("Mapping Data...")
            df_mapped = WardenMapper.map_to_residents_dataframe(raw_residents, raw_bookings)

            if progress_callback:
                progress_callback("Checking for changes...")
            
            if residents_csv_path.exists():
                # Perform change detection before modifying any local datasets
                if not self._has_changed(residents_csv_path, df_mapped):
                    duration = round(time.time() - start_sync_time, 2)
                    safe_log(f"Sync complete. No resident changes detected. Duration: {duration} s.")
                    status["last_successful_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    status["sync_duration_seconds"] = duration
                    status["status"] = "No resident changes detected"
                    status["health"] = "Healthy"
                    self.save_sync_status(status)
                    if progress_callback:
                        progress_callback("Completed. No resident changes detected.")
                    return {"success": True, "changed": False, "details": status}

                # Create backup before replacing
                self._create_backup()
                
                # Make local rollback safety copy
                shutil.copy2(residents_csv_path, temp_backup_path)
                backup_created = True

            if progress_callback:
                progress_callback("Updating Resident Database...")
            
            residents_csv_path.parent.mkdir(parents=True, exist_ok=True)
            df_mapped.to_csv(residents_csv_path, index=False)

            # Map future financial models
            raw_payments = self.client.get_payments()
            self._save_raw_json("payments", raw_payments)
            raw_txns = self.client.get_transactions()
            self._save_raw_json("transactions", raw_txns)

            if progress_callback:
                progress_callback("Refreshing Profiles & Rebuilding Pipelines...")
            
            # Execute downstream pipeline updates
            import cleaner
            import feature_engineering
            import profile_generator

            cleaner.run()
            feature_engineering.run()
            profile_generator.run()

            # Clean rollback backup on successful run
            if temp_backup_path.exists():
                temp_backup_path.unlink()

            duration = round(time.time() - start_sync_time, 2)
            safe_log(f"Sync complete. New data written. Residents: {len(raw_residents)}, Bookings: {len(raw_bookings)}. Duration: {duration} s.")
            
            # Update sync status
            status["last_successful_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
            status["sync_duration_seconds"] = duration
            status["residents_imported"] = len(raw_residents)
            status["properties_imported"] = len(raw_props)
            status["bookings_imported"] = len(raw_bookings)
            status["status"] = "Success"
            status["health"] = "Healthy"
            self.save_sync_status(status)

            if progress_callback:
                progress_callback("Completed.")

            return {"success": True, "changed": True, "details": status}

        except Exception as e:
            duration = round(time.time() - start_sync_time, 2)
            safe_log(f"Sync failed: {str(e)}. Attempting rollback...", "error")
            
            # Rollback to keep previous data if sync failed
            if backup_created and temp_backup_path.exists():
                try:
                    shutil.copy2(temp_backup_path, residents_csv_path)
                    temp_backup_path.unlink()
                    safe_log("Rollback successful. Restored previous Residents.csv.")
                except Exception as rollback_err:
                    safe_log(f"Rollback failed: {str(rollback_err)}", "error")

            status["last_failed_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
            status["status"] = f"Failed: {str(e)}"
            status["health"] = "Unhealthy"
            self.save_sync_status(status)
            
            if progress_callback:
                progress_callback(f"Failed: {str(e)}")

            return {"success": False, "error": str(e), "details": status}
