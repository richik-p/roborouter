"""add immutable artifact records

Revision ID: 20260820_01
Revises: c9816ab7cca2
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_01"
down_revision: str | None = "c9816ab7cca2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("artifact_id", sa.String(length=120), nullable=False),
        sa.Column("evaluation_job_id", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("filename", sa.String(length=180), nullable=False),
        sa.Column("object_key", sa.String(length=700), nullable=False),
        sa.Column("uri", sa.String(length=800), nullable=False),
        sa.Column("media_type", sa.String(length=180), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("artifact_id"),
        sa.UniqueConstraint("object_key"),
        sa.UniqueConstraint("uri"),
        sa.UniqueConstraint(
            "evaluation_job_id",
            "kind",
            "filename",
            "sha256",
            "size_bytes",
            "media_type",
            name="uq_artifact_job_identity",
        ),
    )
    op.create_index(op.f("ix_artifacts_evaluation_job_id"), "artifacts", ["evaluation_job_id"], unique=False)
    op.create_index(op.f("ix_artifacts_sha256"), "artifacts", ["sha256"], unique=False)
    op.create_index(op.f("ix_artifacts_state"), "artifacts", ["state"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_artifacts_state"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_sha256"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_evaluation_job_id"), table_name="artifacts")
    op.drop_table("artifacts")
