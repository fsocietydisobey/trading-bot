import os
import jwt
from typing import Dict, Any, Optional
from config.settings import settings


class AuthError(Exception):
    pass


def verify_jwt(token: Optional[str]) -> Dict[str, Any]:
    if not token:
        raise AuthError("Missing token")

    options = {"require": ["exp", "iat", "sub"], "verify_signature": True}
    audience = settings.JWT_AUDIENCE or None
    issuer = settings.JWT_ISSUER or None

    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET or settings.SECRET_KEY,  # support either setting name
            algorithms=["HS256"],
            audience=audience,
            issuer=issuer,
            options=options,
        )
        return claims
    except Exception as e:
        raise AuthError(f"Invalid token: {e}") from e