import re
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def is_password_strong(password: str) -> bool:
    """
    Enforces:
    - At least 12 characters (Standard for 2026)
    - Uppercase & Lowercase
    - At least one number
    - At least one special character (@#$%^&+=, etc.)
    """
    if len(password) < 12:
        return False
    if not re.search(r"[A-Z]", password): # Uppercase
        return False
    if not re.search(r"[a-z]", password): # Lowercase
        return False
    if not re.search(r"\d", password):    # Digit
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): # Special
        return False
    return True

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)