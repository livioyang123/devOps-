"""
Tests for authentication and security features
Tests JWT authentication, encryption, rate limiting, and input sanitization
"""

import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
import time

from app.main import app
from app.auth import (
    create_access_token,
    decode_access_token,
    verify_password,
    get_password_hash,
    TokenData
)
from app.encryption import (
    EncryptionService,
    encrypt_api_key,
    decrypt_api_key,
    encrypt_credentials,
    decrypt_credentials,
    mask_api_key
)
from app.middleware import InputSanitizationMiddleware


@pytest.fixture
def client():
    """Create a fresh test client for each test"""
    return TestClient(app)


class TestJWTAuthentication:
    """Test JWT token creation and validation"""
    
    def test_create_and_decode_token(self):
        """Test creating and decoding a JWT token"""
        # Create token
        token_data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(token_data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode token
        decoded = decode_access_token(token)
        assert decoded.user_id == "user-123"
        assert decoded.email == "test@example.com"
    
    def test_token_with_expiration(self):
        """Test token with custom expiration"""
        token_data = {"sub": "user-456"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(token_data, expires_delta)
        
        assert token is not None
        decoded = decode_access_token(token)
        assert decoded.user_id == "user-456"
    
    def test_invalid_token(self):
        """Test decoding an invalid token"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("invalid-token")
        
        assert exc_info.value.status_code == 401
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "SecurePassword123"  # Shorter password to avoid bcrypt issues
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)


class TestEncryption:
    """Test AES-256 encryption for API keys and credentials"""
    
    def test_encrypt_decrypt_api_key(self):
        """Test encrypting and decrypting an API key"""
        api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
        
        # Encrypt
        encrypted = encrypt_api_key(api_key)
        assert encrypted != api_key
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == api_key
    
    def test_encrypt_decrypt_credentials(self):
        """Test encrypting and decrypting Kubernetes credentials"""
        credentials = '{"apiVersion":"v1","kind":"Config","clusters":[{"name":"test"}]}'
        
        # Encrypt
        encrypted = encrypt_credentials(credentials)
        assert encrypted != credentials
        
        # Decrypt
        decrypted = decrypt_credentials(encrypted)
        assert decrypted == credentials
    
    def test_mask_api_key(self):
        """Test API key masking for display"""
        api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
        
        masked = mask_api_key(api_key, visible_chars=4)
        
        # Should not contain the full key
        assert api_key not in masked
        
        # Should show last 4 characters
        assert masked.endswith(api_key[-4:])
        
        # Should contain asterisks
        assert "*" in masked
    
    def test_mask_short_api_key(self):
        """Test masking a short API key"""
        api_key = "abc"
        masked = mask_api_key(api_key, visible_chars=4)
        
        # Should be fully masked
        assert masked == "***"
    
    def test_encryption_service_instance(self):
        """Test EncryptionService with custom key"""
        service = EncryptionService("test-encryption-key-for-testing")
        
        plaintext = "sensitive-data-12345"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert encrypted != plaintext
        assert decrypted == plaintext


class TestRateLimiting:
    """Test rate limiting middleware"""
    
    def test_rate_limit_allows_normal_requests(self, client):
        """Test that normal request rates are allowed"""
        # Make a few requests (well under the limit)
        for _ in range(3):
            response = client.get("/")
            assert response.status_code == 200
            
            # Check rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
    
    def test_rate_limit_blocks_excessive_requests(self):
        """Test that excessive requests are blocked"""
        # Use a fresh client to avoid interference from other tests
        test_client = TestClient(app)
        
        # Note: This test might be slow as it needs to exceed rate limit
        # We'll make many requests quickly
        
        responses = []
        for _ in range(70):  # Exceed 60 requests per minute
            response = test_client.get("/")
            responses.append(response)
            
            if response.status_code == 429:
                break
        
        # Should have at least one rate limited response
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0
        
        # Check rate limit response
        if rate_limited:
            response = rate_limited[0]
            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert "rate_limit_exceeded" in response.json()["error"]
    
    def test_health_check_bypasses_rate_limit(self, client):
        """Test that health checks bypass rate limiting"""
        # Make many health check requests
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200


class TestInputSanitization:
    """Test input sanitization middleware"""
    
    def test_sql_injection_detection(self):
        """Test detection of SQL injection attempts"""
        middleware = InputSanitizationMiddleware(app)
        
        # Test various SQL injection patterns
        sql_injections = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1 UNION SELECT * FROM users",
        ]
        
        for injection in sql_injections:
            is_safe, reason = middleware.sanitize_value(injection)
            assert not is_safe
            assert "SQL injection" in reason
    
    def test_xss_detection(self):
        """Test detection of XSS attempts"""
        middleware = InputSanitizationMiddleware(app)
        
        # Test various XSS patterns
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<iframe src='malicious.com'></iframe>",
        ]
        
        for xss in xss_attempts:
            is_safe, reason = middleware.sanitize_value(xss)
            assert not is_safe
            assert "XSS" in reason
    
    def test_command_injection_detection(self):
        """Test detection of command injection attempts"""
        middleware = InputSanitizationMiddleware(app)
        
        # Test various command injection patterns
        cmd_injections = [
            "test; rm -rf /",
            "test | cat /etc/passwd",
            "test && malicious_command",
            "$(malicious_command)",
            "`malicious_command`",
        ]
        
        for injection in cmd_injections:
            is_safe, reason = middleware.sanitize_value(injection)
            assert not is_safe
            assert "command injection" in reason
    
    def test_safe_input_passes(self):
        """Test that safe input passes sanitization"""
        middleware = InputSanitizationMiddleware(app)
        
        safe_inputs = [
            "normal text",
            "user@example.com",
            "deployment-name-123",
            "This is a safe description.",
        ]
        
        for safe_input in safe_inputs:
            is_safe, reason = middleware.sanitize_value(safe_input)
            assert is_safe
            assert reason == ""


class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""
    
    def test_login_endpoint(self, client):
        """Test login endpoint"""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_register_endpoint(self, client):
        """Test registration endpoint"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "name": "New User"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["email"] == "newuser@example.com"
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
        assert "authentication_required" in response.json()["error"]
    
    def test_protected_endpoint_with_token(self, client):
        """Test accessing protected endpoint with valid token"""
        # First, login to get token
        login_response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
    
    def test_refresh_token_endpoint(self, client):
        """Test token refresh endpoint"""
        # First, login to get token
        login_response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Refresh token
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
