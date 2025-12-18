#!/usr/bin/env python3
"""
Generate JWT token for testing
"""

import sys
from datetime import datetime, timedelta
from jose import jwt

# JWT config (match backend config)
SECRET_KEY = "dev-secret-key-change-in-production-use-openssl-rand-hex-32"
ALGORITHM = "HS256"
EXPIRE_MINUTES = 30

def create_test_token(user_id: int = 1, email: str = "test@example.com"):
    """Create JWT token for testing"""
    
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    print(f"JWT Token Generated:")
    print(f"User ID: {user_id}")
    print(f"Email: {email}")
    print(f"Expires: {expire}")
    print(f"\nToken:\n{token}")
    
    return token

if __name__ == "__main__":
    create_test_token()
