"""add scoped worker credentials and lease identity

Revision ID: 20260820_03
Revises: 20260820_02
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_03"
down_revision: str | None = "20260820_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "worker_credentials",
        sa.Column("credential_id", sa.String(length=120), nullable=False),
        sa.Column("worker_id", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("label", sa.String(length=180), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("credential_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_worker_credentials_worker_id"), "worker_credentials", ["worker_id"], unique=False)
    with op.batch_alter_table("evaluation_jobs") as batch_op:
        batch_op.add_column(sa.Column("credential_id", sa.String(length=120), nullable=True))
        batch_op.create_index(batch_op.f("ix_evaluation_jobs_credential_id"), ["credential_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("evaluation_jobs") as batch_op:
        batch_op.drop_index(batch_op.f("ix_evaluation_jobs_credential_id"))
        batch_op.drop_column("credential_id")
    op.drop_index(op.f("ix_worker_credentials_worker_id"), table_name="worker_credentials")
    op.drop_table("worker_credentials")
