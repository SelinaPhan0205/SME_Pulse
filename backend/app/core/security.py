"""Security utilities for password hashing and JWT token generation."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import settings

# ================================
# PASSWORD HASHING (bcrypt)
# ================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

# ================================
# JWT TOKEN
# ================================
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.BACKEND_SECRET_KEY,
        algorithm=settings.BACKEND_ALGORITHM
    )
    
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode JWT token and return payload or None if invalid."""
    try:
        payload = jwt.decode(
            token,
            settings.BACKEND_SECRET_KEY,
            algorithms=[settings.BACKEND_ALGORITHM],
        )
        return payload
    except JWTError as e:
        # Log the actual error for debugging
        import logging
        logging.warning(f"JWT decode error: {e}")
        return None

