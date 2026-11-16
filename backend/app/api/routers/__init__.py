from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.dependencies import get_current_admin
from backend.app.api.routers.admin_tickets import admin_ticket_router
from backend.app.api.routers.customer import customer_router
from backend.app.api.schemas.admin import (
    AdminIdentity,
    AdminLoginRequest,
    AdminTokenResponse,
)
from backend.app.core.auth import (
    AuthConfigurationError,
    authenticate_admin,
    create_access_token,
)
from backend.app.core.config import settings


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post("/login", response_model=AdminTokenResponse)
def login(request: AdminLoginRequest) -> AdminTokenResponse:
    try:
        authenticated = authenticate_admin(request.username, request.password)
    except AuthConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is unavailable.",
        ) from error

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )

    token = create_access_token(request.username)
    if settings.jwt_expiry_minutes is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is unavailable.",
        )
    return AdminTokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expiry_minutes * 60,
    )


@admin_router.get("/me", response_model=AdminIdentity)
def current_admin(
    admin: dict[str, str] = Depends(get_current_admin),
) -> AdminIdentity:
    return AdminIdentity(username=admin["username"])


__all__ = ["admin_router", "admin_ticket_router", "customer_router"]
