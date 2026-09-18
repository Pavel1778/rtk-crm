"""Keycloak JWT verification with JWKS caching."""

from typing import Optional, Dict
from datetime import datetime, timedelta
import httpx
from jose import jwt, JWTError
from loguru import logger

from backend.app.core.config import settings


class KeycloakVerifier:
    """Keycloak JWT verifier with JWKS caching."""
    
    def __init__(self):
        self.jwks_cache: Optional[Dict] = None
        self.jwks_cache_time: Optional[datetime] = None
        self.cache_ttl = timedelta(hours=1)
    
    async def get_jwks(self) -> Dict:
        """Get JWKS from Keycloak with caching."""
        
        # Return cached JWKS if still valid
        if (
            self.jwks_cache is not None
            and self.jwks_cache_time is not None
            and datetime.utcnow() - self.jwks_cache_time < self.cache_ttl
        ):
            return self.jwks_cache
        
        # Fetch new JWKS
        jwks_url = (
            f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
        )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url, timeout=10.0)
                response.raise_for_status()
                self.jwks_cache = response.json()
                self.jwks_cache_time = datetime.utcnow()
                logger.info("JWKS fetched successfully")
                return self.jwks_cache
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            # Return cached JWKS even if expired on error
            if self.jwks_cache is not None:
                logger.warning("Using expired JWKS cache")
                return self.jwks_cache
            raise
    
    async def verify_token(self, token: str) -> Dict:
        """Verify JWT token against Keycloak JWKS."""
        
        jwks = await self.get_jwks()
        
        try:
            # Get key ID from token header
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise JWTError("No 'kid' in token header")
            
            # Find matching key in JWKS
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                raise JWTError(f"No matching key found for kid: {kid}")
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                },
                audience=settings.KEYCLOAK_CLIENT_ID,
            )
            
            return payload
            
        except JWTError as e:
            logger.error(f"Token verification failed: {e}")
            raise


# Global instance
keycloak_verifier = KeycloakVerifier()
