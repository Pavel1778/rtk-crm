"""Audit middleware for 152-FZ compliance logging."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Awaitable
import json
from datetime import datetime
from loguru import logger

from backend.app.core.config import settings
from backend.app.core.crypto import mask_pii


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to log all mutating requests for audit trail."""
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Only log mutating methods
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)
        
        # Capture request details
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        path = request.url.path
        
        # Try to get user info from state (set by auth dependency)
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)
        
        # Log the action
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "username": mask_pii(username) if username else None,
            "action_type": request.method,
            "path": path,
            "client_ip": client_host,
            "user_agent": user_agent,
        }
        
        # Log to file/console
        logger.info(f"AUDIT: {json.dumps(log_entry, ensure_ascii=False)}")
        
        # Proceed with request
        response = await call_next(request)
        
        # Log response status
        log_entry["response_status"] = response.status_code
        logger.debug(f"AUDIT_RESPONSE: {json.dumps(log_entry, ensure_ascii=False)}")
        
        return response
