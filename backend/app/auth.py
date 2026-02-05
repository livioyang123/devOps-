"""
Authentication and authorization utilities
Implements JWT-based authentication for the platform
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    email: Optional[str] = None


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    # Bcrypt has a 72 byte limit, truncate if necessary
    if len(password.encode()) > 72:
        password = password[:72]
    
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT access token
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData with user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("user_id") or payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
        token_data = TokenData(user_id=user_id, email=payload.get("email"))
        return token_data
        
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Dependency to get the current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials from request
        
    Returns:
        TokenData with user information
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    return decode_access_token(token)


# Optional dependency for endpoints that can work with or without auth
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[TokenData]:
    """
    Optional dependency to get current user if token is provided
    
    Args:
        credentials: Optional HTTP Bearer credentials
        
    Returns:
        TokenData if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return decode_access_token(credentials.credentials)
    except HTTPException:
        return None
