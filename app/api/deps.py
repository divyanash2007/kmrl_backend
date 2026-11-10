from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db


def verify_safe_key(
    x_safe_key: Optional[str] = Header(None, alias="X-Safe-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Validates official authentication via either:
    1. 'X-Safe-Key: <key>' header
    2. 'Authorization: Bearer <key_or_token>' header
    """
    provided_key = None

    if x_safe_key:
        provided_key = x_safe_key.strip()
    elif authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            provided_key = parts[1].strip()
        else:
            provided_key = authorization.strip()

    if not provided_key or provided_key != settings.SAFE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing KMRL Safe Key credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return provided_key

