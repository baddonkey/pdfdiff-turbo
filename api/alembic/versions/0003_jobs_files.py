"""job files and job owner

Revision ID: 0003_jobs_files
Revises: 0002_auth
Create Date: 2026-01-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_jobs_files"
down_revision = "0002_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"], unique=False)
    op.create_foreign_key("fk_jobs_user_id_users", "jobs", "users", ["user_id"], ["id"], ondelete="CASCADE")

    op.create_table(
        "job_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("set_a_path", sa.String(length=2048), nullable=True),
        sa.Column("set_b_path", sa.String(length=2048), nullable=True),
        sa.Column("missing_in_set_a", sa.Boolean(), nullable=False),
        sa.Column("missing_in_set_b", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_job_files_job_id", "job_files", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_files_job_id", table_name="job_files")
    op.drop_table("job_files")

    op.drop_constraint("fk_jobs_user_id_users", "jobs", type_="foreignkey")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_column("jobs", "user_id")
