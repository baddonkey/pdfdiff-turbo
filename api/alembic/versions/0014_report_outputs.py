"""report outputs

Revision ID: 0014_report_outputs
Revises: 0013_reports
Create Date: 2026-02-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_report_outputs"
down_revision = "0013_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("visual_path", sa.String(length=2048), nullable=True))
    op.add_column("reports", sa.Column("visual_filename", sa.String(length=255), nullable=True))
    op.add_column("reports", sa.Column("text_path", sa.String(length=2048), nullable=True))
    op.add_column("reports", sa.Column("text_filename", sa.String(length=255), nullable=True))
    op.add_column("reports", sa.Column("bundle_path", sa.String(length=2048), nullable=True))
    op.add_column("reports", sa.Column("bundle_filename", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "bundle_filename")
    op.drop_column("reports", "bundle_path")
    op.drop_column("reports", "text_filename")
    op.drop_column("reports", "text_path")
    op.drop_column("reports", "visual_filename")
    op.drop_column("reports", "visual_path")
