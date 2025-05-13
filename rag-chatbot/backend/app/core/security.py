# filepath: backend/core/security.py
"""
Security utilities and middleware.

This module provides security-related functionality, including:
- API key validation
- Authentication
- Rate limiting
- Password hashing
- JWT token handling
"""
import os
import time
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from fastapi import Depends, HTTPException, Security, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from passlib.context import CryptContext

from app.core.logging import get_logger
from app.config import Settings, get_settings

# Setup logging
logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# API key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# OAuth2 with Password flow (if needed)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

# In-memory rate limiting store (should be replaced with Redis in production)
rate_limit_store: Dict[str, List[float]] = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: The plain-text password
        hashed_password: The hashed password
        
    Returns:
        True if the password matches the hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: The plain-text password
        
    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    settings: Settings = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The data to encode in the token
        expires_delta: How long the token should be valid for
        settings: Application settings
        
    Returns:
        The encoded JWT token
    """
    if settings is None:
        settings = get_settings()
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    # Use a secure random key for JWT encoding if not provided
    secret_key = settings.secret_key or secrets.token_hex(32)
    
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


def decode_access_token(
    token: str,
    settings: Settings = None
) -> Dict[str, Any]:
    """
    Decode a JWT access token.
    
    Args:
        token: The JWT token to decode
        settings: Application settings
        
    Returns:
        The decoded token data
        
    Raises:
        HTTPException: If the token is invalid or expired
    """
    if settings is None:
        settings = get_settings()
    
    # Use a secure random key for JWT decoding if not provided
    secret_key = settings.secret_key or secrets.token_hex(32)
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def validate_api_key(
    api_key: str = Security(api_key_header),
    settings: Settings = Depends(get_settings)
) -> bool:
    """
    Validate an API key.
    
    Args:
        api_key: The API key to validate
        settings: Application settings
        
    Returns:
        True if the API key is valid
        
    Raises:
        HTTPException: If the API key is invalid
    """
    if not api_key:
        return False
    
    # Check against configured API keys
    valid_keys = settings.api_keys or []
    
    # No API keys configured means API key validation is disabled
    if not valid_keys:
        return True
    
    # Securely compare the API key to avoid timing attacks
    for valid_key in valid_keys:
        if secrets.compare_digest(api_key, valid_key):
            return True
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "APIKey"},
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Get the current user from a JWT token.
    
    Args:
        token: The JWT token
        settings: Application settings
        
    Returns:
        The user data from the token
        
    Raises:
        HTTPException: If the token is invalid or the user is not found
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = decode_access_token(token, settings)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # In a real application, you would look up the user in a database here
        # For this example, we just return the username
        return {"username": username}
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def rate_limit(
    request: Request,
    limit: int = 100,
    window: int = 60,
    key_func: Callable[[Request], str] = None
) -> None:
    """
    Apply rate limiting to a request.
    
    Args:
        request: The FastAPI request
        limit: Maximum number of requests allowed in the window
        window: Time window in seconds
        key_func: Function to generate a key from the request (defaults to IP address)
        
    Raises:
        HTTPException: If the rate limit is exceeded
    """
    # Default key function uses the client IP
    if key_func is None:
        key_func = lambda r: r.client.host if r.client else "unknown"
    
    # Generate key for this request
    key = key_func(request)
    
    # Get current time
    now = time.time()
    
    # Get the list of request timestamps for this key
    request_times = rate_limit_store.get(key, [])
    
    # Remove timestamps outside the window
    window_start = now - window
    request_times = [t for t in request_times if t > window_start]
    
    # Check if limit is exceeded
    if len(request_times) >= limit:
        logger.warning(
            f"Rate limit exceeded for {key}",
            extra={"key": key, "limit": limit, "window": window}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {limit} requests per {window} seconds.",
            headers={"Retry-After": str(window)}
        )
    
    # Add current request timestamp
    request_times.append(now)
    
    # Update store
    rate_limit_store[key] = request_times
    
    # Cleanup old keys (in a real application, this would be done periodically)
    if len(rate_limit_store) > 1000:  # Arbitrary limit to prevent memory leaks
        keys_to_remove = []
        for k, times in rate_limit_store.items():
            if not any(t > window_start for t in times):
                keys_to_remove.append(k)
        
        for k in keys_to_remove:
            del rate_limit_store[k]


def hash_data(data: str) -> str:
    """
    Create a SHA-256 hash of data.
    
    Args:
        data: The data to hash
        
    Returns:
        The hex digest of the hash
    """
    return hashlib.sha256(data.encode()).hexdigest()


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: The length of the token in bytes
        
    Returns:
        A secure random token as a hex string
    """
    return secrets.token_hex(length)