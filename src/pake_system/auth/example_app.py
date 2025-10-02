"""Example FastAPI application demonstrating OAuth2 authentication

This example shows how to:
1. Set up the authentication system
2. Protect endpoints with dependencies
3. Access user information in protected routes

Run with:
    uvicorn src.pake_system.auth.example_app:app --reload

Test the authentication:
    # Login to get token
    curl -X POST "http://localhost:8000/token" \\
         -H "Content-Type: application/x-www-form-urlencoded" \\
         -d "username=admin&password=secret"

    # Access protected endpoint
    curl "http://localhost:8000/auth/me" \\
         -H "Authorization: Bearer <your_token_here>"
"""

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from .dependencies import get_current_active_user
from .models import User
from .router import router as auth_router

# Create FastAPI application
app = FastAPI(
    title="PAKE System Authentication Example",
    description="OAuth2 authentication with JWT tokens",
    version="1.0.0",
)

# Include authentication routes
# This makes the /token and /auth/me endpoints available
app.include_router(auth_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Public endpoint - no authentication required.

    Returns:
        Welcome message and authentication instructions
    """
    return {
        "message": "Welcome to PAKE System",
        "docs": "/docs",
        "authentication": {
            "login": "POST /token with username and password",
            "me": "GET /auth/me with Bearer token",
        },
        "test_credentials": {"username": "admin", "password": "secret"},
    }


@app.get("/protected")
async def protected_route(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict[str, str]:
    """Protected endpoint - requires authentication.

    This demonstrates how to use the authentication dependency
    to protect any endpoint. FastAPI will automatically:
    1. Extract the token from the Authorization header
    2. Validate the token
    3. Fetch the user
    4. Inject the user into the function

    If any step fails, FastAPI returns 401 Unauthorized.

    Args:
        current_user: Automatically injected authenticated user

    Returns:
        Personalized message for the authenticated user
    """
    return {
        "message": f"Hello, {current_user.username}!",
        "email": current_user.email,
        "full_name": current_user.full_name,
    }


@app.get("/admin")
async def admin_route(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict[str, str]:
    """Admin-only endpoint.

    This is a simple example. In production, you would add
    role-based access control by checking current_user.role
    or implementing a separate dependency.

    Args:
        current_user: Automatically injected authenticated user

    Returns:
        Admin panel information
    """
    # In production, check user role:
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="Admin access required")

    return {
        "message": "Welcome to the admin panel",
        "user": current_user.username,
        "admin_features": [
            "User management",
            "System configuration",
            "Analytics dashboard",
        ],
    }


# Error handlers for better UX


@app.exception_handler(401)
async def unauthorized_handler(request, exc):
    """Custom handler for unauthorized errors"""
    return JSONResponse(
        status_code=401,
        content={
            "detail": "Authentication required. Please login at /token",
            "instructions": {
                "step1": "POST /token with username and password",
                "step2": "Include 'Authorization: Bearer <token>' header in requests",
            },
        },
    )


if __name__ == "__main__":
    import uvicorn

    # Run the application
    # Access the interactive docs at http://localhost:8000/docs
    uvicorn.run(
        "example_app:app",
        host="127.0.0.1",  # Secure local binding instead of 0.0.0.0
        port=8000,
        reload=True,
        log_level="info",
    )
