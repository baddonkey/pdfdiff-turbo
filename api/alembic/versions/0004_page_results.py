"""page results

Revision ID: 0004_page_results
Revises: 0003_jobs_files
Create Date: 2026-01-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_page_results"
down_revision = "0003_jobs_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_page_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "done",
                "failed",
                "incompatible_size",
                "missing",
                name="pagestatus",
            ),
            nullable=False,
        ),
        sa.Column("diff_score", sa.Float(), nullable=True),
        sa.Column("incompatible_size", sa.Boolean(), nullable=False),
        sa.Column("missing_in_set_a", sa.Boolean(), nullable=False),
        sa.Column("missing_in_set_b", sa.Boolean(), nullable=False),
        sa.Column("overlay_svg_path", sa.String(length=2048), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_file_id"], ["job_files.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_job_page_results_job_file_id", "job_page_results", ["job_file_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_page_results_job_file_id", table_name="job_page_results")
    op.drop_table("job_page_results")
    op.execute("DROP TYPE IF EXISTS pagestatus")
