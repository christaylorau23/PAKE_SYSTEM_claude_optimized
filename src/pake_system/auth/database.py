"""
User database operations
Handles user storage and retrieval
"""

from typing import Optional

from .models import User, UserInDB

# In-memory user database (for demonstration)
# In production, this would be replaced with actual database queries
# using the existing MultiTenantPostgreSQLService or SQLAlchemy
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "disabled": False,
    },
    "testuser": {
        "username": "testuser",
        "full_name": "Test User",
        "email": "test@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "disabled": False,
    }
}


async def get_user(username: str) -> Optional[User]:
    """
    Retrieve a user from the database by username.

    Args:
        username: The username to look up

    Returns:
        User object if found, None otherwise

    Example:
        >>> user = await get_user("admin")
        >>> user.username
        'admin'
    """
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None


async def create_user(username: str, email: str, hashed_password: str, full_name: Optional[str] = None) -> User:
    """
    Create a new user in the database.

    Args:
        username: Unique username
        email: User email address
        hashed_password: Bcrypt hashed password
        full_name: Optional full name

    Returns:
        The created User object

    Example:
        >>> from .security import create_password_hash
        >>> hashed = create_password_hash("password123")
        >>> user = await create_user("newuser", "new@example.com", hashed)
    """
    user_dict = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "full_name": full_name,
        "disabled": False,
    }
    fake_users_db[username] = user_dict
    return User(**user_dict)


async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    Authenticate a user with username and password.

    This is a convenience function that combines user lookup and password verification.

    Args:
        username: The username
        password: The plaintext password

    Returns:
        UserInDB object if authentication successful, None otherwise

    Example:
        >>> user = await authenticate_user("admin", "secret")
        >>> user.username if user else None
        'admin'
    """
    from .security import verify_password

    user = await get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
