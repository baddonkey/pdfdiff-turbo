"""cancel status and task id

Revision ID: 0005_cancel_and_taskid
Revises: 0004_page_results
Create Date: 2026-01-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_cancel_and_taskid"
down_revision = "0004_page_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'cancelled'")
    op.add_column("job_page_results", sa.Column("task_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("job_page_results", "task_id")