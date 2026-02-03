"""add quota config fields

Revision ID: 0009_app_config_quotas
Revises: 0008_app_config
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0009_app_config_quotas"
down_revision = "0008_app_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_config",
        sa.Column("max_files_per_set", sa.Integer(), nullable=False, server_default="1000"),
    )
    op.add_column(
        "app_config",
        sa.Column("max_upload_mb", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "app_config",
        sa.Column("max_pages_per_job", sa.Integer(), nullable=False, server_default="10000"),
    )
    op.add_column(
        "app_config",
        sa.Column("max_jobs_per_user_per_day", sa.Integer(), nullable=False, server_default="20"),
    )
    op.alter_column("app_config", "max_files_per_set", server_default=None)
    op.alter_column("app_config", "max_upload_mb", server_default=None)
    op.alter_column("app_config", "max_pages_per_job", server_default=None)
    op.alter_column("app_config", "max_jobs_per_user_per_day", server_default=None)


def downgrade() -> None:
    op.drop_column("app_config", "max_jobs_per_user_per_day")
    op.drop_column("app_config", "max_pages_per_job")
    op.drop_column("app_config", "max_upload_mb")
    op.drop_column("app_config", "max_files_per_set")
