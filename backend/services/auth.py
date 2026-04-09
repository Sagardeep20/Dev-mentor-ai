import secrets
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from models import User

logger = logging.getLogger("devmentor.auth")


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_hex(32)


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode('utf-8'))
    except Exception:
        return False


def create_jwt_token(user_id: uuid.UUID) -> str:
    """Create JWT token for user."""
    payload = {
        "user_id": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


async def create_user(db: AsyncSession, username: str, email: str, password: str, groq_api_key: str) -> User:
    """Create a new user with API key and Groq key."""
    result = await db.execute(select(User).where((User.username == username) | (User.email == email)))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("Username or email already exists")

    api_key = generate_api_key()
    password_hash = hash_password(password)
    user = User(
        username=username,
        email=email,
        api_key=api_key,
        password_hash=password_hash,
        groq_api_key=groq_api_key,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Created user: {username} with API key: {api_key[:8]}...")
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user by email and password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None
    # Verify password with bcrypt
    if user.password_hash and verify_password(password, user.password_hash):
        return user
    # Legacy fallback: check if password matches sha256 (old hash format)
    # This is for migration - can be removed after all users have bcrypt hashes
    import hashlib
    if not user.password_hash:
        legacy_hash = hashlib.sha256(password.encode()).hexdigest()
        # Compare only first 64 chars since api_key is 64 chars hex
        if legacy_hash == user.api_key[:64]:
            # Upgrade to bcrypt on successful login
            user.password_hash = hash_password(password)
            user.last_active_at = datetime.now(timezone.utc)
            await db.commit()
            return user
    return None


async def get_user_by_api_key(db: AsyncSession, api_key: str) -> Optional[User]:
    """Get user by API key."""
    result = await db.execute(select(User).where(User.api_key == api_key))
    user = result.scalar_one_or_none()
    if user:
        user.last_active_at = datetime.now(timezone.utc)
        await db.commit()
    return user


async def get_user_by_jwt(db: AsyncSession, token: str) -> Optional[User]:
    """Get user from JWT token."""
    payload = decode_jwt_token(token)
    if not payload:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    try:
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if user:
            user.last_active_at = datetime.now(timezone.utc)
            await db.commit()
        return user
    except Exception:
        return None


async def regenerate_api_key(db: AsyncSession, user_id: uuid.UUID) -> Optional[str]:
    """Regenerate API key for a user. Returns new key or None if user not found."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    new_key = generate_api_key()
    user.api_key = new_key
    user.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(f"Regenerated API key for user: {user.username}")
    return new_key