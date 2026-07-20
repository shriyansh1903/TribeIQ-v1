import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.database import db_manager
from src.config import settings, logger

def bootstrap():
    logger.info("Starting database bootstrap process...")
    
    if not db_manager.ping_check():
        logger.error("MongoDB Atlas connection check failed. Aborting bootstrap process.")
        print("Error: Unable to reach MongoDB. Bootstrap aborted.")
        return False
        
    db = db_manager.get_database()
    existing_collections = db.list_collection_names()
    
    collections_to_init = {
        "users": [("User ID", 1)],
        "properties": [("Property ID", 1)],
        "residents": [("Resident ID", 1), ("Property", 1)],
        "events": [("Event ID", 1)],
        "calendar_events": [("Event ID", 1), ("Date", 1)],
        "recommendations": [("Date", 1)],
        "vendors": [("Vendor ID", 1)],
        "materials": [("Category", 1)],
        "stalls": [("Stall ID", 1)],
        "external_events": [("Event ID", 1), ("Start Date", 1)],
        "settings": [("key", 1)]
    }
    
    for coll_name, index_fields in collections_to_init.items():
        if coll_name not in existing_collections:
            logger.info(f"Creating collection: {coll_name}")
            db.create_collection(coll_name)
        else:
            logger.info(f"Collection {coll_name} already exists.")
            
        # Create indices
        coll = db[coll_name]
        for field, direction in index_fields:
            index_name = f"{field}_idx"
            # Check if index already exists
            existing_indices = coll.index_information()
            if index_name not in existing_indices:
                logger.info(f"Creating index for field '{field}' on collection '{coll_name}'")
                coll.create_index([(field, direction)], name=index_name, unique=False)
                
    logger.info("Database bootstrap completed successfully.")
    print("Database bootstrap successfully completed.")
    return True

if __name__ == "__main__":
    bootstrap()
