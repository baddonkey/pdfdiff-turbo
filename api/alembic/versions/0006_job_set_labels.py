"""add job set labels

Revision ID: 0006_job_set_labels
Revises: 0005_cancel_and_taskid
Create Date: 2026-01-30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_job_set_labels"
down_revision = "0005_cancel_and_taskid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("set_a_label", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("set_b_label", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "set_b_label")
    op.drop_column("jobs", "set_a_label")
