from __future__ import annotations

import argparse
import asyncio
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from .database import SessionLocal
from .db_models import EvaluationJobRow, LaunchCredentialRow
from .launch_auth import LAUNCH_ROLES, hash_launch_token
from .settings import get_settings


async def create_launch_credential(
    *,
    role: str = "user",
    label: str | None = None,
    concurrent_limit: int | None = None,
    daily_limit: int | None = None,
    ttl_days: int | None = None,
    token: str | None = None,
    credential_id: str | None = None,
) -> tuple[LaunchCredentialRow, str]:
    settings = get_settings()
    if role not in LAUNCH_ROLES:
        raise ValueError(f"unknown launch role: {role}")
    if ttl_days is not None and ttl_days <= 0:
        raise ValueError("ttl days must be positive")
    concurrent_limit = settings.launch_default_concurrent_limit if concurrent_limit is None else concurrent_limit
    daily_limit = settings.launch_default_daily_limit if daily_limit is None else daily_limit
    if concurrent_limit <= 0 or daily_limit <= 0:
        raise ValueError("quota limits must be positive")
    credential_id = credential_id or secrets.token_hex(8)
    token = token or f"rrl_{credential_id}.{secrets.token_urlsafe(32)}"
    if not token.startswith(f"rrl_{credential_id}."):
        raise ValueError("bootstrap token credential id does not match")
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        existing = await session.get(LaunchCredentialRow, credential_id)
        if existing is not None:
            if existing.token_hash != hash_launch_token(token):
                raise ValueError("credential identity already exists with different content")
            return existing, token
        row = LaunchCredentialRow(
            credential_id=credential_id,
            role=role,
            token_hash=hash_launch_token(token),
            label=label,
            concurrent_limit=concurrent_limit,
            daily_limit=daily_limit,
            created_at=now,
            expires_at=now + timedelta(days=ttl_days) if ttl_days is not None else None,
            revoked_at=None,
            last_used_at=None,
        )
        session.add(row)
        await session.commit()
        return row, token


async def list_launch_credentials(role: str | None = None) -> list[LaunchCredentialRow]:
    async with SessionLocal() as session:
        statement = select(LaunchCredentialRow).order_by(LaunchCredentialRow.created_at)
        if role:
            statement = statement.where(LaunchCredentialRow.role == role)
        return list((await session.scalars(statement)).all())


async def revoke_launch_credential(credential_id: str) -> LaunchCredentialRow:
    """Revoke a launch key and cancel every job it still has in flight.

    Revocation is a spend stop: queued jobs are never claimed and a worker holding a
    claimed or running job sees CANCELED on its next heartbeat and terminates.
    """
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        row = await session.get(LaunchCredentialRow, credential_id, with_for_update=True)
        if row is None:
            raise ValueError("launch credential not found")
        if row.revoked_at is None:
            row.revoked_at = now
            jobs = (
                await session.scalars(
                    select(EvaluationJobRow).where(
                        EvaluationJobRow.launch_credential_id == credential_id,
                        EvaluationJobRow.state.in_(["QUEUED", "CLAIMED", "RUNNING"]),
                    )
                )
            ).all()
            for job in jobs:
                job.state = "CANCELED"
                job.failure_kind = "canceled"
                job.failure_detail = "launch key revoked"
                job.retry_safe = False
                job.updated_at = now
        await session.commit()
        return row


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage RoboRouter launch keys (evaluation access)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--role", choices=sorted(LAUNCH_ROLES), default="user")
    create.add_argument("--label")
    create.add_argument("--concurrent-limit", type=int)
    create.add_argument("--daily-limit", type=int)
    create.add_argument("--ttl-days", type=int)
    listing = subparsers.add_parser("list")
    listing.add_argument("--role", choices=sorted(LAUNCH_ROLES))
    revoke = subparsers.add_parser("revoke")
    revoke.add_argument("credential_id")
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    if args.command == "create":
        row, token = await create_launch_credential(
            role=args.role,
            label=args.label,
            concurrent_limit=args.concurrent_limit,
            daily_limit=args.daily_limit,
            ttl_days=args.ttl_days,
        )
        print(f"credential_id={row.credential_id}")
        print(f"role={row.role}")
        print(f"quota=concurrent:{row.concurrent_limit} daily:{row.daily_limit}")
        print(f"token={token}")
        print("Store this launch key now; it cannot be recovered from the database.")
    elif args.command == "list":
        for row in await list_launch_credentials(args.role):
            print(
                f"{row.credential_id}\t{row.role}\tconcurrent={row.concurrent_limit}\tdaily={row.daily_limit}\t"
                f"expires={row.expires_at or '-'}\trevoked={row.revoked_at or '-'}\t"
                f"last_used={row.last_used_at or '-'}\tlabel={row.label or '-'}"
            )
    else:
        row = await revoke_launch_credential(args.credential_id)
        print(f"revoked credential_id={row.credential_id} role={row.role}; in-flight jobs canceled")


def run() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run()
