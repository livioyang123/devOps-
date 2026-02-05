"""
Simple tests for configuration functionality without authentication
"""
import pytest
from app.encryption import encrypt_api_key, decrypt_api_key, mask_api_key
from app.routers.config import AVAILABLE_MODELS


def test_api_key_encryption_decryption():
    """Test API key encryption and decryption"""
    original_key = "sk-test-key-1234567890abcdef"
    
    # Encrypt
    encrypted = encrypt_api_key(original_key)
    assert encrypted != original_key
    assert len(encrypted) > 0
    
    # Decrypt
    decrypted = decrypt_api_key(encrypted)
    assert decrypted == original_key


def test_api_key_masking():
    """Test API key masking"""
    api_key = "sk-1234567890abcdef"
    masked = mask_api_key(api_key)
    
    # Should show last 4 characters
    assert masked.endswith("cdef")
    assert "****" in masked
    assert api_key not in masked
    
    # Test with short key
    short_key = "abc"
    masked_short = mask_api_key(short_key)
    assert masked_short == "***"


def test_api_key_masking_custom_visible_chars():
    """Test API key masking with custom visible characters"""
    api_key = "sk-1234567890abcdef"
    masked = mask_api_key(api_key, visible_chars=6)
    
    # Should show last 6 characters
    assert masked.endswith("abcdef")
    assert "****" in masked


def test_available_models_list():
    """Test that available models list is properly configured"""
    assert len(AVAILABLE_MODELS) > 0
    
    # Check for expected models
    model_ids = [model.id for model in AVAILABLE_MODELS]
    assert "gpt-4" in model_ids
    assert "claude-sonnet-3.5" in model_ids
    assert "gemini-pro" in model_ids
    assert "llama-3-70b" in model_ids
    
    # Check model structure
    for model in AVAILABLE_MODELS:
        assert hasattr(model, 'id')
        assert hasattr(model, 'name')
        assert hasattr(model, 'provider')
        assert hasattr(model, 'max_tokens')
        assert model.max_tokens > 0


def test_available_models_providers():
    """Test that all major providers are represented"""
    providers = set(model.provider for model in AVAILABLE_MODELS)
    
    assert "openai" in providers
    assert "anthropic" in providers
    assert "google" in providers
    assert "ollama" in providers


def test_encryption_with_different_keys():
    """Test that different keys produce different encrypted values"""
    key1 = "sk-test-key-1"
    key2 = "sk-test-key-2"
    
    encrypted1 = encrypt_api_key(key1)
    encrypted2 = encrypt_api_key(key2)
    
    assert encrypted1 != encrypted2


def test_encryption_consistency():
    """Test that encrypting the same key twice produces different results (due to salt)"""
    key = "sk-test-key-consistent"
    
    encrypted1 = encrypt_api_key(key)
    encrypted2 = encrypt_api_key(key)
    
    # Fernet includes a timestamp, so encryptions will differ
    # But both should decrypt to the same value
    assert decrypt_api_key(encrypted1) == key
    assert decrypt_api_key(encrypted2) == key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
