from __future__ import annotations

import argparse
import asyncio
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from .database import SessionLocal
from .db_models import EvaluationJobRow, WorkerCredentialRow
from .worker_auth import WORKER_SCOPES, hash_worker_token


async def create_worker_credential(
    worker_id: str,
    *,
    label: str | None = None,
    scopes: list[str] | None = None,
    ttl_days: int | None = None,
    token: str | None = None,
    credential_id: str | None = None,
) -> tuple[WorkerCredentialRow, str]:
    if not worker_id.strip():
        raise ValueError("worker id cannot be empty")
    if ttl_days is not None and ttl_days <= 0:
        raise ValueError("ttl days must be positive")
    selected_scopes = sorted(set(scopes or WORKER_SCOPES))
    unknown = set(selected_scopes) - WORKER_SCOPES
    if unknown:
        raise ValueError(f"unknown worker scopes: {', '.join(sorted(unknown))}")
    credential_id = credential_id or secrets.token_hex(8)
    token = token or f"rrw_{credential_id}.{secrets.token_urlsafe(32)}"
    if not token.startswith(f"rrw_{credential_id}."):
        raise ValueError("bootstrap token credential id does not match")
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        existing = await session.get(WorkerCredentialRow, credential_id)
        if existing is not None:
            if existing.worker_id != worker_id or existing.token_hash != hash_worker_token(token):
                raise ValueError("credential identity already exists with different content")
            return existing, token
        row = WorkerCredentialRow(
            credential_id=credential_id,
            worker_id=worker_id,
            token_hash=hash_worker_token(token),
            scopes=selected_scopes,
            label=label,
            created_at=now,
            expires_at=now + timedelta(days=ttl_days) if ttl_days is not None else None,
            revoked_at=None,
            last_used_at=None,
        )
        session.add(row)
        await session.commit()
        return row, token


async def list_worker_credentials(worker_id: str | None = None) -> list[WorkerCredentialRow]:
    async with SessionLocal() as session:
        statement = select(WorkerCredentialRow).order_by(WorkerCredentialRow.created_at)
        if worker_id:
            statement = statement.where(WorkerCredentialRow.worker_id == worker_id)
        return list((await session.scalars(statement)).all())


async def revoke_worker_credential(credential_id: str) -> WorkerCredentialRow:
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        row = await session.get(WorkerCredentialRow, credential_id, with_for_update=True)
        if row is None:
            raise ValueError("worker credential not found")
        if row.revoked_at is None:
            row.revoked_at = now
            jobs = (
                await session.scalars(
                    select(EvaluationJobRow).where(
                        EvaluationJobRow.credential_id == credential_id,
                        EvaluationJobRow.state.in_(["CLAIMED", "RUNNING"]),
                    )
                )
            ).all()
            for job in jobs:
                job.state = "FAILED"
                job.failure_kind = "infrastructure"
                job.failure_detail = "worker credential revoked"
                job.retry_safe = False
                job.lease_expires_at = None
                job.updated_at = now
        await session.commit()
        return row


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage RoboRouter worker credentials")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--worker-id", required=True)
    create.add_argument("--label")
    create.add_argument("--scope", action="append", dest="scopes")
    create.add_argument("--ttl-days", type=int)
    listing = subparsers.add_parser("list")
    listing.add_argument("--worker-id")
    revoke = subparsers.add_parser("revoke")
    revoke.add_argument("credential_id")
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    if args.command == "create":
        row, token = await create_worker_credential(
            args.worker_id,
            label=args.label,
            scopes=args.scopes,
            ttl_days=args.ttl_days,
        )
        print(f"credential_id={row.credential_id}")
        print(f"worker_id={row.worker_id}")
        print(f"token={token}")
        print("Store this token now; it cannot be recovered from the database.")
    elif args.command == "list":
        for row in await list_worker_credentials(args.worker_id):
            print(
                f"{row.credential_id}\t{row.worker_id}\t{','.join(row.scopes)}\t"
                f"expires={row.expires_at or '-'}\trevoked={row.revoked_at or '-'}\tlabel={row.label or '-'}"
            )
    else:
        row = await revoke_worker_credential(args.credential_id)
        print(f"revoked credential_id={row.credential_id} worker_id={row.worker_id}")


def run() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run()
