"""
Middleware for authentication, rate limiting, and input sanitization
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import re
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse
    Implements token bucket algorithm per client IP
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60.0
        
        # Store: {client_ip: {"tokens": float, "last_update": float}}
        self.clients = defaultdict(lambda: {
            "tokens": float(requests_per_minute),
            "last_update": time.time()
        })
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request with rate limiting
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/detailed"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        
        # Get current time
        now = time.time()
        
        # Get client bucket
        client_data = self.clients[client_ip]
        
        # Calculate time passed and add tokens
        time_passed = now - client_data["last_update"]
        client_data["tokens"] = min(
            self.requests_per_minute,
            client_data["tokens"] + time_passed * self.requests_per_second
        )
        client_data["last_update"] = now
        
        # Check if client has tokens
        if client_data["tokens"] >= 1.0:
            client_data["tokens"] -= 1.0
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(int(client_data["tokens"]))
            
            return response
        else:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for client: {client_ip}")
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": int(1.0 / self.requests_per_second)
                },
                headers={
                    "Retry-After": str(int(1.0 / self.requests_per_second)),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to sanitize user inputs and prevent injection attacks
    """
    
    # Patterns for detecting potential injection attacks
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(--\s*$)",
        r"(;\s*DROP\b)",
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\'\s*OR\s*\'\d+\'\s*=\s*\'\d+)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",
        r"\$\([^)]*\)",
        r"`[^`]*`",
    ]
    
    def __init__(self, app):
        super().__init__(app)
        
        # Compile patterns for efficiency
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.cmd_patterns = [re.compile(p) for p in self.COMMAND_INJECTION_PATTERNS]
    
    def check_sql_injection(self, value: str) -> bool:
        """Check if value contains SQL injection patterns"""
        return any(pattern.search(value) for pattern in self.sql_patterns)
    
    def check_xss(self, value: str) -> bool:
        """Check if value contains XSS patterns"""
        return any(pattern.search(value) for pattern in self.xss_patterns)
    
    def check_command_injection(self, value: str) -> bool:
        """Check if value contains command injection patterns"""
        return any(pattern.search(value) for pattern in self.cmd_patterns)
    
    def sanitize_value(self, value: str) -> tuple[bool, str]:
        """
        Sanitize a string value
        
        Args:
            value: String to sanitize
            
        Returns:
            Tuple of (is_safe, reason)
        """
        if self.check_sql_injection(value):
            return False, "Potential SQL injection detected"
        
        if self.check_xss(value):
            return False, "Potential XSS attack detected"
        
        if self.check_command_injection(value):
            return False, "Potential command injection detected"
        
        return True, ""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request with input sanitization
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response or validation error
        """
        # Skip sanitization for health checks and static files
        if request.url.path in ["/health", "/health/detailed", "/", "/api/docs", "/api/redoc"]:
            return await call_next(request)
        
        # Check query parameters
        for key, value in request.query_params.items():
            is_safe, reason = self.sanitize_value(str(value))
            if not is_safe:
                logger.warning(f"Malicious input detected in query param '{key}': {reason}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_input",
                        "message": f"Invalid input detected: {reason}",
                        "field": key
                    }
                )
        
        # Check path parameters (basic check)
        path = request.url.path
        is_safe, reason = self.sanitize_value(path)
        if not is_safe:
            logger.warning(f"Malicious input detected in path: {reason}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "invalid_input",
                    "message": f"Invalid path detected: {reason}"
                }
            )
        
        # For POST/PUT/PATCH requests, we'll validate body in the endpoint
        # using Pydantic models, which provides additional validation
        
        return await call_next(request)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce authentication on protected endpoints
    """
    
    # Endpoints that don't require authentication
    PUBLIC_PATHS = [
        "/",
        "/health",
        "/health/detailed",
        "/api/docs",
        "/api/redoc",
        "/openapi.json",
        "/api/auth/login",
        "/api/auth/register",
    ]
    
    def __init__(self, app):
        super().__init__(app)
    
    def is_public_path(self, path: str) -> bool:
        """Check if path is public"""
        return any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request with authentication check
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response or authentication error
        """
        # Skip authentication for public paths
        if self.is_public_path(request.url.path):
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "authentication_required",
                    "message": "Authentication token is required"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Token validation will be done by the auth dependency in endpoints
        # This middleware just checks if the header exists
        
        return await call_next(request)
