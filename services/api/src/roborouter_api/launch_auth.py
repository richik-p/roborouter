from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .db_models import LaunchCredentialRow
from .settings import get_settings

LAUNCH_ROLES = frozenset({"user", "operator"})


@dataclass(frozen=True)
class LaunchPrincipal:
    credential_id: str
    role: str
    concurrent_limit: int
    daily_limit: int

    @property
    def is_operator(self) -> bool:
        return self.role == "operator"


def hash_launch_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def parse_launch_token(token: str) -> str | None:
    if not token.startswith("rrl_") or "." not in token:
        return None
    credential_id, secret = token[4:].split(".", 1)
    if not credential_id or not secret:
        return None
    return credential_id


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def authenticate_launch(authorization: str | None, session: AsyncSession) -> LaunchPrincipal | None:
    """Resolve the launch key on a request.

    Returns None only when evaluation access is open and no key was sent. A key that
    is present is always validated so attribution and per-key quotas apply either way.
    """
    if authorization is None:
        if get_settings().evaluation_access == "open":
            return None
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="launch key required")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid launch key")
    token = authorization.removeprefix("Bearer ")
    credential_id = parse_launch_token(token)
    if credential_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid launch key")
    row = await session.get(LaunchCredentialRow, credential_id)
    now = datetime.now(UTC)
    if (
        row is None
        or not hmac.compare_digest(row.token_hash, hash_launch_token(token))
        or row.revoked_at is not None
        or (row.expires_at is not None and _aware(row.expires_at) <= now)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid launch key")
    row.last_used_at = now
    await session.commit()
    return LaunchPrincipal(
        credential_id=row.credential_id,
        role=row.role,
        concurrent_limit=row.concurrent_limit,
        daily_limit=row.daily_limit,
    )


async def launch_principal(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> LaunchPrincipal | None:
    return await authenticate_launch(authorization, session)
