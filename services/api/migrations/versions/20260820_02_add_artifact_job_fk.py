"""add artifact job foreign key

Revision ID: 20260820_02
Revises: 20260820_01
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260820_02"
down_revision: str | None = "20260820_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.create_foreign_key(
            "fk_artifacts_evaluation_job_id",
            "evaluation_jobs",
            ["evaluation_job_id"],
            ["job_id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_constraint("fk_artifacts_evaluation_job_id", type_="foreignkey")
