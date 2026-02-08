"""text compare fields

Revision ID: 0012_text_compare
Revises: 0011_app_config_retention
Create Date: 2026-02-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_text_compare"
down_revision = "0011_app_config_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    text_status = sa.Enum(
        "pending",
        "running",
        "done",
        "missing",
        "failed",
        name="textstatus",
    )
    bind = op.get_bind()
    text_status.create(bind, checkfirst=True)

    op.add_column(
        "job_files",
        sa.Column("text_status", text_status, nullable=False, server_default="pending"),
    )
    op.add_column(
        "job_files",
        sa.Column("text_set_a_path", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "job_files",
        sa.Column("text_set_b_path", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "job_files",
        sa.Column("text_error", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_files", "text_error")
    op.drop_column("job_files", "text_set_b_path")
    op.drop_column("job_files", "text_set_a_path")
    op.drop_column("job_files", "text_status")
    op.execute("DROP TYPE IF EXISTS textstatus")
