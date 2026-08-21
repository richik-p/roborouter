from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .db_models import WorkerCredentialRow

WORKER_SCOPES = frozenset(
    {
        "worker:register",
        "job:claim",
        "job:heartbeat",
        "artifact:write",
        "job:complete",
        "job:fail",
    }
)


@dataclass(frozen=True)
class WorkerPrincipal:
    credential_id: str
    worker_id: str
    scopes: frozenset[str]


def hash_worker_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def parse_worker_token(token: str) -> str | None:
    if not token.startswith("rrw_") or "." not in token:
        return None
    credential_id, secret = token[4:].split(".", 1)
    if not credential_id or not secret:
        return None
    return credential_id


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def authenticate_worker(
    authorization: str | None,
    required_scope: str,
    session: AsyncSession,
) -> WorkerPrincipal:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid worker token")
    token = authorization.removeprefix("Bearer ")
    credential_id = parse_worker_token(token)
    if credential_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid worker token")
    row = await session.get(WorkerCredentialRow, credential_id)
    now = datetime.now(UTC)
    if (
        row is None
        or not hmac.compare_digest(row.token_hash, hash_worker_token(token))
        or row.revoked_at is not None
        or (row.expires_at is not None and _aware(row.expires_at) <= now)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid worker token")
    if required_scope not in row.scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="worker token lacks required scope")
    row.last_used_at = now
    await session.commit()
    return WorkerPrincipal(
        credential_id=row.credential_id,
        worker_id=row.worker_id,
        scopes=frozenset(row.scopes),
    )


def require_worker_scope(required_scope: str):
    async def dependency(
        session: Annotated[AsyncSession, Depends(get_session)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> WorkerPrincipal:
        return await authenticate_worker(authorization, required_scope, session)

    return dependency
