"""add per-user quotas

Revision ID: 0010_user_quotas
Revises: 0009_app_config_quotas
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0010_user_quotas"
down_revision = "0009_app_config_quotas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("max_files_per_set", sa.Integer(), nullable=False, server_default="1000"),
    )
    op.add_column(
        "users",
        sa.Column("max_upload_mb", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "users",
        sa.Column("max_pages_per_job", sa.Integer(), nullable=False, server_default="10000"),
    )
    op.add_column(
        "users",
        sa.Column("max_jobs_per_user_per_day", sa.Integer(), nullable=False, server_default="20"),
    )
    op.alter_column("users", "max_files_per_set", server_default=None)
    op.alter_column("users", "max_upload_mb", server_default=None)
    op.alter_column("users", "max_pages_per_job", server_default=None)
    op.alter_column("users", "max_jobs_per_user_per_day", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "max_jobs_per_user_per_day")
    op.drop_column("users", "max_pages_per_job")
    op.drop_column("users", "max_upload_mb")
    op.drop_column("users", "max_files_per_set")
