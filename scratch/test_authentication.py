import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.auth.auth_service import auth_service
from src.repositories import UsersRepository

print("=========================================================")
print("Testing TribeIQ Authentication Service Operations")
print("=========================================================")

users_repo = UsersRepository()

# Cleanup test user if exists
existing = users_repo.find_by_username("test_user_auth")
if existing:
    users_repo.delete(str(existing["_id"]))

print("1. Testing User Account Registration...")
uid, msg = auth_service.create_user(
    username="test_user_auth",
    email="test@tribeiq.com",
    display_name="Test Auth User",
    password="my-secret-password-123",
    role="Community Manager"
)
assert uid is not None, f"Failed to register test user: {msg}"
print(f" [OK] User created with ID: {uid}")

print("\n2. Testing Password Verification Hashing...")
user_doc = users_repo.find_by_username("test_user_auth")
assert user_doc is not None, "Failed to locate registered user document."
assert user_doc["password_hash"] != "my-secret-password-123", "Passwords must not be stored in plaintext!"
assert auth_service.verify_password("my-secret-password-123", user_doc["password_hash"]), "Password check failed."
print(" [OK] Bcrypt hashing verified successfully.")

print("\n3. Testing Successful Authentication...")
auth_user, msg = auth_service.authenticate_user("test_user_auth", "my-secret-password-123")
assert auth_user is not None, f"Authentication failed: {msg}"
assert auth_user["failed_attempts"] == 0, "Failed attempts count should reset to 0."
print(" [OK] Authentication succeeded correctly.")

print("\n4. Testing Wrong Password Rejection & Lockout...")
for i in range(1, 5):
    res, msg = auth_service.authenticate_user("test_user_auth", "wrong-password")
    assert res is None, "Incorrect password was accepted."
    print(f" - Attempt {i} correctly failed. Message: {msg}")
    
# 5th attempt should lock the account
res, msg = auth_service.authenticate_user("test_user_auth", "wrong-password")
assert res is None, "5th attempt did not fail."
assert "lock" in msg.lower(), f"Lockout warning missing from message: {msg}"
print(" [OK] Lockout triggered and verified successfully on 5th failed attempt.")

# Cleanup test user
users_repo.delete(uid)
print("\nAll authentication service unit tests completed successfully!")
