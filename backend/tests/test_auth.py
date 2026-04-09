"""Tests for authentication service."""

import pytest
from services.auth import (
    hash_password,
    verify_password,
    generate_api_key,
    create_jwt_token,
    decode_jwt_token
)


class TestPasswordHashing:
    """Test password hashing with bcrypt."""

    def test_hash_password_returns_different_hash(self):
        """Hash should be different from original password."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_hash_password_produces_unique_hashes(self):
        """Same password should produce different hashes (due to salt)."""
        password = "mysecretpassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Verify password should return True for correct password."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Verify password should return False for incorrect password."""
        password = "mysecretpassword"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Verify password should handle empty password gracefully."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False


class TestApiKeyGeneration:
    """Test API key generation."""

    def test_generate_api_key_length(self):
        """API key should be 64 characters (32 bytes hex)."""
        key = generate_api_key()
        assert len(key) == 64

    def test_generate_api_key_unique(self):
        """Generated API keys should be unique."""
        key1 = generate_api_key()
        key2 = generate_api_key()
        assert key1 != key2

    def test_generate_api_key_hex(self):
        """API key should be hexadecimal."""
        key = generate_api_key()
        assert all(c in '0123456789abcdef' for c in key)


class TestJwtTokens:
    """Test JWT token creation and verification."""

    def test_create_jwt_token(self):
        """Should create a valid JWT token."""
        import uuid
        user_id = uuid.uuid4()
        token = create_jwt_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_jwt_token_valid(self):
        """Should decode a valid JWT token."""
        import uuid
        user_id = uuid.uuid4()
        token = create_jwt_token(user_id)
        payload = decode_jwt_token(token)

        assert payload is not None
        assert payload["user_id"] == str(user_id)

    def test_decode_jwt_token_invalid(self):
        """Should return None for invalid token."""
        payload = decode_jwt_token("invalid.token.here")
        assert payload is None

    def test_decode_jwt_token_empty(self):
        """Should return None for empty token."""
        payload = decode_jwt_token("")
        assert payload is None


@pytest.mark.asyncio
async def test_authenticate_user_not_found():
    """Test authenticate_user with non-existent email."""
    from services.auth import authenticate_user
    from unittest.mock import AsyncMock, MagicMock

    # Create mock db session
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await authenticate_user(mock_db, "nonexistent@example.com", "password")
    assert result is None


@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    """Test create_user raises error for duplicate email."""
    from services.auth import create_user
    from unittest.mock import AsyncMock, MagicMock
    import uuid

    # Create mock db session
    mock_db = MagicMock()

    # Mock existing user found
    mock_existing_user = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_existing_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(ValueError, match="Username or email already exists"):
        await create_user(mock_db, "newuser", "existing@example.com", "password123")