"""
Authentication router
Handles user login and token generation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from typing import Optional

from app.auth import (
    create_access_token,
    get_current_user,
    TokenData,
    Token,
    verify_password,
    get_password_hash
)
from app.config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """User registration request model"""
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserResponse(BaseModel):
    """User response model"""
    user_id: str
    email: str
    name: Optional[str] = None


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token
    
    Args:
        request: Login credentials
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: If authentication fails
    """
    # TODO: In a real implementation, verify against database
    # For now, this is a placeholder that demonstrates the flow
    
    # Example: Check credentials (replace with actual database lookup)
    # user = await get_user_by_email(request.email)
    # if not user or not verify_password(request.password, user.hashed_password):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Incorrect email or password"
    #     )
    
    # For demonstration, create a token with the email
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": "user-123", "email": request.email},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """
    Register a new user
    
    Args:
        request: Registration details
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: If registration fails
    """
    # TODO: In a real implementation, save to database
    # For now, this is a placeholder that demonstrates the flow
    
    # Example: Check if user exists
    # existing_user = await get_user_by_email(request.email)
    # if existing_user:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Email already registered"
    #     )
    
    # Hash password
    hashed_password = get_password_hash(request.password)
    
    # Example: Save user to database
    # user = await create_user(
    #     email=request.email,
    #     hashed_password=hashed_password,
    #     name=request.name
    # )
    
    # For demonstration, return a mock user
    return UserResponse(
        user_id="user-123",
        email=request.email,
        name=request.name
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user information
    
    Args:
        current_user: Current user from JWT token
        
    Returns:
        User information
    """
    # TODO: In a real implementation, fetch from database
    # user = await get_user_by_id(current_user.user_id)
    
    # For demonstration, return user from token
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email or "user@example.com",
        name="Demo User"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(get_current_user)):
    """
    Refresh JWT token
    
    Args:
        current_user: Current user from JWT token
        
    Returns:
        New JWT access token
    """
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user.user_id, "email": current_user.email},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")
