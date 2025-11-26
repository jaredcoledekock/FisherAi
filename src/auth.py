import os
from typing import Optional

import jwt
from flask import request


def get_user_id() -> Optional[str]:
    """
    Lightweight auth helper.
    - If SUPABASE_JWT_SECRET is set, attempt to verify a Bearer JWT and return sub/user_id.
    - Otherwise, allow a plain X-User-Id header as a lightweight dev override.
    """
    # Prefer Supabase-style JWT verification when a secret is available
    secret = os.getenv("SUPABASE_JWT_SECRET")
    auth_header = request.headers.get("Authorization", "")
    token = None

    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    if secret and token:
        try:
            decoded = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            # Supabase JWTs typically carry sub or user_id
            return decoded.get("sub") or decoded.get("user_id")
        except Exception:
            return None

    # Dev fallback: header override
    dev_user = request.headers.get("X-User-Id")
    if dev_user:
        return dev_user.strip()

    return None
