"""add config retention settings

Revision ID: 0011_app_config_retention
Revises: 0010_user_quotas
Create Date: 2026-02-05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0011_app_config_retention"
down_revision = "0010_user_quotas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_config",
        sa.Column("file_retention_hours", sa.Integer(), nullable=False, server_default="24"),
    )
    op.add_column(
        "app_config",
        sa.Column("job_retention_days", sa.Integer(), nullable=False, server_default="7"),
    )
    op.alter_column("app_config", "file_retention_hours", server_default=None)
    op.alter_column("app_config", "job_retention_days", server_default=None)


def downgrade() -> None:
    op.drop_column("app_config", "job_retention_days")
    op.drop_column("app_config", "file_retention_hours")
