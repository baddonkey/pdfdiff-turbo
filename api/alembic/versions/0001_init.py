"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-01-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", sa.Enum("created", "running", "completed", "failed", name="jobstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.execute("DROP TYPE IF EXISTS jobstatus")
