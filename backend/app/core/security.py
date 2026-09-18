"""Security utilities for authentication and authorization."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from backend.app.core.config import settings


security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Current authenticated user model."""
    id: int
    username: str
    role: str  # "user", "manager", "admin"
    
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
    
    @property
    def is_manager(self) -> bool:
        return self.role in ("admin", "manager")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CurrentUser:
    """Get current authenticated user from JWT token."""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    if settings.MOCK_MODE:
        # Mock mode: accept any valid-looking JWT or use demo users
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            user_id: Optional[int] = payload.get("sub")
            username: Optional[str] = payload.get("username")
            role: Optional[str] = payload.get("role")
            
            if user_id is None or username is None or role is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token claims",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return CurrentUser(id=user_id, username=username, role=role)
            
        except JWTError:
            # In mock mode, also accept demo credentials embedded in token
            # This is for development only
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        # Production mode: verify with Keycloak
        # For now, use standard JWT verification
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            user_id: Optional[int] = payload.get("sub")
            username: Optional[str] = payload.get("username")
            role: Optional[str] = payload.get("role")
            
            if user_id is None or username is None or role is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token claims",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return CurrentUser(id=user_id, username=username, role=role)
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )


def require_role(required_role: str):
    """Dependency factory to require specific role."""
    
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)):
        role_hierarchy = {"user": 0, "manager": 1, "admin": 2}
        
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )
        
        return current_user
    
    return role_checker


# Convenience dependencies
AdminUser = Depends(require_role("admin"))
ManagerUser = Depends(require_role("manager"))
