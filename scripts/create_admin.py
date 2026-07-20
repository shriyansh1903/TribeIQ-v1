import sys
import getpass
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.repositories import UsersRepository
from src.auth.auth_service import auth_service
from src.database import db_manager

def main():
    print("=========================================================")
    print("TribeIQ Administrator Creation Bootstrap Script")
    print("=========================================================")

    # Ensure DB is reachable
    if not db_manager.ping_check():
        print("Error: MongoDB Atlas is currently offline. Cannot create administrator.")
        sys.exit(1)

    users_repo = UsersRepository()
    
    # Check if any admin exists
    try:
        admins = users_repo.find_all({"role": "Admin"})
    except Exception as e:
        print(f"Error querying database: {str(e)}")
        sys.exit(1)
        
    if len(admins) > 0:
        print(f"Safe Exit: An administrator account ('{admins[0].get('username')}') already exists.")
        print("TribeIQ does not allow overwriting administrator accounts via bootstrap.")
        sys.exit(0)

    print("\nNo administrator accounts detected. Please configure the initial admin:")
    
    username = input("Username     : ").strip()
    if not username:
        print("Error: Username is required.")
        sys.exit(1)
        
    email = input("Email        : ").strip()
    display_name = input("Display Name : ").strip()
    
    password = getpass.getpass("Password     : ")
    if not password:
        print("Error: Password is required.")
        sys.exit(1)
        
    confirm_password = getpass.getpass("Confirm Pwd  : ")
    if password != confirm_password:
        print("Error: Passwords do not match.")
        sys.exit(1)

    print("\nCreating administrator account...")
    user_id, msg = auth_service.create_user(
        username=username,
        email=email,
        display_name=display_name,
        password=password,
        role="Admin"
    )
    
    if user_id:
        print(f"Success: Administrator account '{username}' successfully created!")
        sys.exit(0)
    else:
        print(f"Error: Failed to create administrator account. Details: {msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
