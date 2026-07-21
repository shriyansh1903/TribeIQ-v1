import sys
import os
import time
import datetime
import pandas as pd
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.database import db_manager
from src.repositories import (
    PropertiesRepository, ResidentsRepository, EventsRepository, CalendarEventsRepository,
    VendorsRepository, MaterialsRepository, StallsRepository, ExternalEventsRepository
)

def run_migration():
    print("=========================================================")
    print("TribeIQ Legacy CSV to MongoDB Migration Framework")
    print("=========================================================")
    
    if not db_manager.ping_check():
        print("Warning: MongoDB Atlas is currently offline. Creating standby migration report.")
        # Save Standby report
        artifact_dir = Path("C:/Users/shriy/.gemini/antigravity/brain/e556d5bf-cb49-4724-bb0b-803504332787")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        report_path = artifact_dir / "migration_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# TribeIQ Migration Execution Report\n\nStatus: **STANDBY** (MongoDB Atlas is currently unreachable. Fallback CSV Mode is active.)")
        print(f"Standby report saved to: {report_path}")
        sys.exit(0)
        
    start_time = time.time()
    
    # Repositories
    repos = {
        "properties": (PropertiesRepository(), PROJECT_ROOT / "data" / "properties.csv", "Property ID"),
        "residents": (ResidentsRepository(), PROJECT_ROOT / "data" / "Residents.csv", "Resident ID"),
        "events": (EventsRepository(), PROJECT_ROOT / "data" / "events.csv", "Event ID"),
        "calendar_events": (CalendarEventsRepository(), PROJECT_ROOT / "data" / "planned_calendar.csv", "Event ID"),
        "vendors": (VendorsRepository(), PROJECT_ROOT / "data" / "vendors.csv", "Vendor ID"),
        "materials": (MaterialsRepository(), PROJECT_ROOT / "data" / "materials.csv", "Category"),
        "stalls": (StallsRepository(), PROJECT_ROOT / "data" / "stalls.csv", "Stall ID"),
        "external_events": (ExternalEventsRepository(), PROJECT_ROOT / "data" / "external_events.csv", "Event ID")
    }
    
    report_lines = []
    report_lines.append("# TribeIQ Migration Execution Report")
    report_lines.append(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("---")
    
    for coll_name, (repo, csv_path, id_field) in repos.items():
        print(f"\nProcessing collection: '{coll_name}'...")
        if not csv_path.exists():
            print(f" - Warning: CSV file '{csv_path.name}' does not exist. Skipping.")
            continue
            
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f" - Error: Failed to read CSV '{csv_path.name}': {str(e)}")
            continue
            
        records_migrated = 0
        records_skipped = 0
        validation_errors = 0
        duplicates = 0
        
        # Clear existing MongoDB data to prevent duplicate accumulation during re-runs
        repo.collection.delete_many({})
        
        seen_ids = set()
        for idx, row in df.iterrows():
            row_dict = row.dropna().to_dict()
            
            # Clean fields: convert float representation of ints/ids
            cleaned_row = {}
            for k, v in row_dict.items():
                if isinstance(v, float) and v.is_integer():
                    cleaned_row[k] = int(v)
                elif pd.isna(v) or v == "":
                    continue
                else:
                    cleaned_row[k] = v
                    
            doc_id = cleaned_row.get(id_field)
            
            # 1. Validation
            if not doc_id:
                validation_errors += 1
                records_skipped += 1
                continue
                
            # Convert ID to string format
            doc_id_str = str(doc_id).strip()
            
            # 2. Check duplicates in CSV file itself
            if doc_id_str in seen_ids:
                duplicates += 1
                records_skipped += 1
                continue
            seen_ids.add(doc_id_str)
            
            # 3. Insert record
            try:
                repo.insert(cleaned_row)
                records_migrated += 1
            except Exception as e:
                print(f"   - Failed to insert record ID '{doc_id_str}': {str(e)}")
                records_skipped += 1
                
        print(f" - Completed: Migrated={records_migrated}, Skipped={records_skipped}, ValErrors={validation_errors}, Duplicates={duplicates}")
        
        report_lines.append(f"### Collection: `{coll_name}`")
        report_lines.append(f"- **CSV Source**: `{csv_path.name}`")
        report_lines.append(f"- **Migrated**: {records_migrated}")
        report_lines.append(f"- **Skipped**: {records_skipped}")
        report_lines.append(f"- **Validation Errors**: {validation_errors}")
        report_lines.append(f"- **Duplicates**: {duplicates}")
        report_lines.append("")
        
    execution_time = time.time() - start_time
    report_lines.append(f"**Total Migration Time**: {execution_time:.2f} seconds")
    
    # Save Migration Report to brain artifacts directory
    artifact_dir = Path("C:/Users/shriy/.gemini/antigravity/brain/e556d5bf-cb49-4724-bb0b-803504332787")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifact_dir / "migration_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"\nMigration completed successfully in {execution_time:.2f} seconds.")
    print(f"Migration report saved to: {report_path}")

if __name__ == "__main__":
    run_migration()
