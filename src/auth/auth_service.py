import bcrypt
import datetime
from typing import Optional, Tuple
from src.config import settings, logger
from src.repositories import UsersRepository

class AuthService:
    def __init__(self):
        self.users_repo = UsersRepository()
        self.lockout_minutes = 15
        self.max_failed_attempts = 5

    def hash_password(self, password: str) -> str:
        rounds = settings.BCRYPT_ROUNDS
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False

    def authenticate_user(self, username: str, password: str) -> Tuple[Optional[dict], str]:
        """
        Authenticates a user.
        Returns:
            Tuple[Optional[dict], str]: (user_document, status_message)
        """
        user = self.users_repo.find_by_username(username)
        if not user:
            logger.warning(f"Failed login attempt: User '{username}' not found.")
            return None, "Invalid username or password."

        # Check if disabled
        if user.get("status") == "Inactive":
            logger.warning(f"Failed login attempt: Account for user '{username}' is disabled.")
            return None, "This account is disabled. Please contact an administrator."

        now = datetime.datetime.now(datetime.timezone.utc)

        # Check account lock
        locked_until = user.get("locked_until")
        if locked_until:
            # Ensure locked_until is timezone-aware
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=datetime.timezone.utc)
            if now < locked_until:
                remaining_time = int((locked_until - now).total_seconds() / 60) + 1
                logger.warning(f"Failed login attempt: Account for user '{username}' is currently locked.")
                return None, f"Account is temporarily locked. Try again in {remaining_time} minute(s)."

        # Verify password
        password_hash = user.get("password_hash")
        if not password_hash or not self.verify_password(password, password_hash):
            # Increment failed attempts
            failed_attempts = user.get("failed_attempts", 0) + 1
            new_lock_until = None
            msg = "Invalid username or password."
            
            if failed_attempts >= self.max_failed_attempts:
                new_lock_until = now + datetime.timedelta(minutes=self.lockout_minutes)
                msg = f"Invalid username or password. Too many failed attempts. Account locked for {self.lockout_minutes} minutes."
                logger.warning(f"Account locked: User '{username}' reached max failed attempts.")
            else:
                logger.warning(f"Failed login attempt: Incorrect password for user '{username}'.")
                
            self.users_repo.increment_failed_attempts(username, lock_until=new_lock_until)
            return None, msg

        # Login Success
        self.users_repo.reset_failed_attempts(username)
        
        # Update last login timestamp
        update_fields = {
            "last_login": datetime.datetime.now(datetime.timezone.utc),
            "updated_at": datetime.datetime.now(datetime.timezone.utc)
        }
        self.users_repo.update(str(user["_id"]), update_fields)
        
        logger.info(f"Successful login: User '{username}' logged in.")
        # Reload latest user object
        latest_user = self.users_repo.find_by_username(username)
        return latest_user, "Success"

    def reset_password(self, user_id: str, new_password: str) -> bool:
        hashed = self.hash_password(new_password)
        update_fields = {
            "password_hash": hashed,
            "updated_at": datetime.datetime.now(datetime.timezone.utc),
            "failed_attempts": 0,
            "locked_until": None
        }
        success = self.users_repo.update(user_id, update_fields)
        if success:
            logger.info(f"Password reset success for user_id: {user_id}")
        return success

    def create_user(self, username: str, email: str, display_name: str, password: str, role: str) -> Tuple[Optional[str], str]:
        # Check duplicate
        if self.users_repo.find_by_username(username):
            return None, "Username already exists."

        hashed = self.hash_password(password)
        user_doc = {
            "username": username,
            "email": email,
            "display_name": display_name,
            "password_hash": hashed,
            "role": role,
            "status": "Active",
            "failed_attempts": 0,
            "locked_until": None,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "updated_at": datetime.datetime.now(datetime.timezone.utc)
        }
        
        inserted_id = self.users_repo.insert(user_doc)
        if inserted_id:
            logger.info(f"User created: '{username}' with role '{role}' by administrator.")
            return inserted_id, "Success"
        return None, "Failed to create user record."

# Global Singleton AuthService
auth_service = AuthService()
