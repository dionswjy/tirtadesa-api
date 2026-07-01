import base64
import hashlib
from datetime import datetime, timedelta
from jose import jwt
from cryptography.fernet import Fernet

SECRET_KEY = "tirtadesa_secret"
ALGORITHM = "HS256"

# Derive a consistent Fernet key from SECRET_KEY so server reloads do not invalidate active sessions
FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest())
fernet = Fernet(FERNET_KEY)

def encrypt_data(text: str):
    return fernet.encrypt(text.encode()).decode()

def decrypt_data(token: str):
    return fernet.decrypt(token.encode()).decode()

def create_access_token(data: dict):
    to_encode = data.copy()

    if "sub" in to_encode:
        to_encode["sub"] = encrypt_data(to_encode["sub"])

    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt