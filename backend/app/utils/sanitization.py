"""
Input sanitization utilities for preventing injection attacks

This module provides functions for sanitizing various types of user input
to prevent SQL injection, XSS, command injection, and other security vulnerabilities.

Validates: Requirement 15.3 - Input sanitization to prevent injection attacks
"""

import re
import html
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a general string input
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length (optional)
        
    Returns:
        Sanitized string
        
    Raises:
        ValueError: If input is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Input must be a string")
    
    # Strip leading/trailing whitespace
    sanitized = value.strip()
    
    # Check length
    if max_length and len(sanitized) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length}")
    
    # HTML escape to prevent XSS
    sanitized = html.escape(sanitized)
    
    return sanitized


def sanitize_identifier(value: str, allow_dash: bool = True, allow_underscore: bool = True) -> str:
    """
    Sanitize an identifier (e.g., cluster name, deployment name)
    
    Args:
        value: Identifier to sanitize
        allow_dash: Allow dash character
        allow_underscore: Allow underscore character
        
    Returns:
        Sanitized identifier
        
    Raises:
        ValueError: If identifier is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Identifier must be a string")
    
    # Strip whitespace
    sanitized = value.strip()
    
    # Check if empty
    if not sanitized:
        raise ValueError("Identifier cannot be empty")
    
    # Build allowed pattern
    pattern = r'^[a-zA-Z0-9'
    if allow_dash:
        pattern += r'\-'
    if allow_underscore:
        pattern += r'_'
    pattern += r']+$'
    
    # Validate pattern
    if not re.match(pattern, sanitized):
        raise ValueError(
            f"Identifier contains invalid characters. "
            f"Only alphanumeric characters"
            f"{', dashes' if allow_dash else ''}"
            f"{', underscores' if allow_underscore else ''} are allowed"
        )
    
    # Check length (reasonable limits)
    if len(sanitized) > 255:
        raise ValueError("Identifier exceeds maximum length of 255 characters")
    
    return sanitized


def sanitize_yaml_content(content: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate YAML content for security issues
    
    This function performs security checks on YAML content without parsing it.
    Actual YAML parsing and validation should be done by the ParserService.
    
    Args:
        content: YAML content to validate
        
    Returns:
        Tuple of (is_valid, sanitized_content, error_message)
    """
    if not isinstance(content, str):
        return False, "", "YAML content must be a string"
    
    # Check for empty content
    if not content.strip():
        return False, "", "YAML content cannot be empty"
    
    # Check size limits (prevent DoS)
    max_size = 10 * 1024 * 1024  # 10MB
    if len(content) > max_size:
        return False, "", f"YAML content exceeds maximum size of {max_size} bytes"
    
    # Check for excessive nesting (YAML bomb protection)
    max_indent = 0
    line_count = 0
    for line in content.split('\n'):
        line_count += 1
        if line.strip():
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)
    
    if max_indent > 100:
        return False, "", "YAML content has excessive nesting depth (max 100 spaces)"
    
    if line_count > 50000:
        return False, "", "YAML content has too many lines (max 50000)"
    
    # Check for dangerous YAML tags (arbitrary code execution)
    dangerous_tags = [
        '!!python/',
        '!!ruby/',
        '!!java/',
        '!!php/',
    ]
    
    for tag in dangerous_tags:
        if tag in content:
            return False, "", f"Dangerous YAML tag detected: {tag}"
    
    # The content passes basic security checks
    # Actual YAML syntax validation happens in ParserService
    return True, content, None


def sanitize_namespace(namespace: str) -> str:
    """
    Sanitize Kubernetes namespace name
    
    Args:
        namespace: Namespace to sanitize
        
    Returns:
        Sanitized namespace
        
    Raises:
        ValueError: If namespace is invalid
    """
    if not isinstance(namespace, str):
        raise ValueError("Namespace must be a string")
    
    # Strip whitespace
    sanitized = namespace.strip().lower()
    
    # Check if empty
    if not sanitized:
        raise ValueError("Namespace cannot be empty")
    
    # Kubernetes namespace naming rules:
    # - lowercase alphanumeric characters or '-'
    # - must start and end with alphanumeric
    # - max 63 characters
    if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', sanitized):
        raise ValueError(
            "Invalid namespace format. Must contain only lowercase alphanumeric "
            "characters or '-', and must start and end with an alphanumeric character"
        )
    
    if len(sanitized) > 63:
        raise ValueError("Namespace exceeds maximum length of 63 characters")
    
    # Reserved namespaces
    reserved = ['kube-system', 'kube-public', 'kube-node-lease']
    if sanitized in reserved:
        raise ValueError(f"Cannot use reserved namespace: {sanitized}")
    
    return sanitized


def sanitize_url(url: str, allowed_schemes: Optional[list] = None) -> str:
    """
    Sanitize and validate URL
    
    Args:
        url: URL to sanitize
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
        
    Returns:
        Sanitized URL
        
    Raises:
        ValueError: If URL is invalid
    """
    if not isinstance(url, str):
        raise ValueError("URL must be a string")
    
    # Strip whitespace
    sanitized = url.strip()
    
    # Check if empty
    if not sanitized:
        raise ValueError("URL cannot be empty")
    
    # Default allowed schemes
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    # Basic URL validation
    url_pattern = r'^(https?|wss?)://[^\s/$.?#].[^\s]*$'
    if not re.match(url_pattern, sanitized, re.IGNORECASE):
        raise ValueError("Invalid URL format")
    
    # Check scheme
    scheme = sanitized.split('://')[0].lower()
    if scheme not in allowed_schemes:
        raise ValueError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'javascript:',
        r'data:',
        r'file:',
        r'<script',
        r'onerror=',
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise ValueError(f"URL contains suspicious pattern: {pattern}")
    
    return sanitized


def sanitize_email(email: str) -> str:
    """
    Sanitize and validate email address
    
    Args:
        email: Email address to sanitize
        
    Returns:
        Sanitized email
        
    Raises:
        ValueError: If email is invalid
    """
    if not isinstance(email, str):
        raise ValueError("Email must be a string")
    
    # Strip whitespace and convert to lowercase
    sanitized = email.strip().lower()
    
    # Check if empty
    if not sanitized:
        raise ValueError("Email cannot be empty")
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, sanitized):
        raise ValueError("Invalid email format")
    
    # Check length
    if len(sanitized) > 254:  # RFC 5321
        raise ValueError("Email exceeds maximum length of 254 characters")
    
    return sanitized


def sanitize_json_field(value: str, field_name: str) -> str:
    """
    Sanitize a JSON field value
    
    Args:
        value: Field value to sanitize
        field_name: Name of the field (for error messages)
        
    Returns:
        Sanitized value
        
    Raises:
        ValueError: If value is invalid
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    
    # Strip whitespace
    sanitized = value.strip()
    
    # HTML escape to prevent XSS
    sanitized = html.escape(sanitized)
    
    # Check for null bytes
    if '\x00' in sanitized:
        raise ValueError(f"{field_name} contains null bytes")
    
    return sanitized


def validate_no_path_traversal(path: str) -> bool:
    """
    Check if path contains path traversal attempts
    
    Args:
        path: Path to validate
        
    Returns:
        True if path is safe, False otherwise
    """
    # Check for path traversal patterns
    dangerous_patterns = [
        '..',
        '~/',
        '/etc/',
        '/proc/',
        '/sys/',
        '\\\\',
        '%2e%2e',  # URL encoded ..
        '%252e',   # Double URL encoded .
    ]
    
    path_lower = path.lower()
    for pattern in dangerous_patterns:
        if pattern in path_lower:
            logger.warning(f"Path traversal attempt detected: {pattern} in {path}")
            return False
    
    return True


def sanitize_search_query(query: str, max_length: int = 500) -> str:
    """
    Sanitize search query for log search
    
    Args:
        query: Search query to sanitize
        max_length: Maximum query length
        
    Returns:
        Sanitized query
        
    Raises:
        ValueError: If query is invalid
    """
    if not isinstance(query, str):
        raise ValueError("Search query must be a string")
    
    # Strip whitespace
    sanitized = query.strip()
    
    # Check length
    if len(sanitized) > max_length:
        raise ValueError(f"Search query exceeds maximum length of {max_length}")
    
    # Escape special regex characters to prevent regex injection
    # Allow basic regex but escape dangerous patterns
    special_chars = ['(', ')', '[', ']', '{', '}', '\\', '^', '$']
    for char in special_chars:
        if char in sanitized and not sanitized.count(char) % 2 == 0:
            # Unbalanced special characters - escape them
            sanitized = sanitized.replace(char, '\\' + char)
    
    return sanitized
