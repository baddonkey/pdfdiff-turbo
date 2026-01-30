"""add has_diffs flags

Revision ID: 0007_job_has_diffs
Revises: 0006_job_set_labels
Create Date: 2026-01-30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_job_has_diffs"
down_revision = "0006_job_set_labels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("has_diffs", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("job_files", sa.Column("has_diffs", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("jobs", "has_diffs", server_default=None)
    op.alter_column("job_files", "has_diffs", server_default=None)


def downgrade() -> None:
    op.drop_column("job_files", "has_diffs")
    op.drop_column("jobs", "has_diffs")
