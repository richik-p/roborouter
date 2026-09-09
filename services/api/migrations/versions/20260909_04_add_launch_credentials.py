"""add launch credentials and evaluation ownership

Revision ID: 20260909_04
Revises: 20260820_03
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_04"
down_revision: str | None = "20260820_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "launch_credentials",
        sa.Column("credential_id", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=180), nullable=True),
        sa.Column("concurrent_limit", sa.Integer(), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("credential_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_launch_credentials_role"), "launch_credentials", ["role"], unique=False)
    with op.batch_alter_table("evaluation_jobs") as batch_op:
        batch_op.add_column(sa.Column("launch_credential_id", sa.String(length=120), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_evaluation_jobs_launch_credential_id"), ["launch_credential_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("evaluation_jobs") as batch_op:
        batch_op.drop_index(batch_op.f("ix_evaluation_jobs_launch_credential_id"))
        batch_op.drop_column("launch_credential_id")
    op.drop_index(op.f("ix_launch_credentials_role"), table_name="launch_credentials")
    op.drop_table("launch_credentials")
