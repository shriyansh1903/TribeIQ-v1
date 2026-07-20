import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.services.health_service import HealthService
from src.database import db_manager

def main():
    print("=========================================================")
    print("TribeIQ Platform Database Connectivity & Health Check")
    print("=========================================================")
    
    app_version = HealthService.get_app_version()
    env = HealthService.get_environment()
    print(f"Application Version : {app_version}")
    print(f"Current Environment : {env.upper()}")
    
    print("\nTesting MongoDB Atlas connection status...")
    db_status = HealthService.get_database_status()
    
    if db_status["connected"]:
        print("MongoDB Status       : [CONNECTED]")
        print(f"Target Database      : {db_status['database_name']}")
        
        print("\nCollection Availability Registry:")
        for name, state in db_status["collections"].items():
            badge = "Y" if state == "Created" else "N"
            print(f" - [{badge}] {name:<18} : {state}")
            
        print("\nVerification Status  : SUCCESS")
        sys.exit(0)
    else:
        print("MongoDB Status       : [OFFLINE / DISCONNECTED]")
        print(f"Target Database      : {db_status['database_name']}")
        if "error" in db_status:
            print(f"Error Details        : {db_status['error']}")
        print("\nVerification Status  : FAILED (Fallback to CSV legacy operations active)")
        sys.exit(1)

if __name__ == "__main__":
    main()
