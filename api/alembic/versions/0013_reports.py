"""reports

Revision ID: 0013_reports
Revises: 0012_text_compare
Create Date: 2026-02-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_reports"
down_revision = "0012_text_compare"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reportstatus') THEN
                CREATE TYPE reportstatus AS ENUM ('queued', 'running', 'done', 'failed');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reporttype') THEN
                CREATE TYPE reporttype AS ENUM ('visual', 'text', 'both');
            END IF;
        END$$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source_job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            report_type reporttype NOT NULL,
            status reportstatus NOT NULL DEFAULT 'queued',
            progress INTEGER NOT NULL DEFAULT 0,
            output_path VARCHAR(2048) NULL,
            output_filename VARCHAR(255) NULL,
            error VARCHAR(1024) NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_reports_user_id ON reports (user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_reports_source_job_id ON reports (source_job_id);"
    )


def downgrade() -> None:
    op.drop_index("ix_reports_source_job_id", table_name="reports")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_table("reports")
    op.execute("DROP TYPE IF EXISTS reporttype")
    op.execute("DROP TYPE IF EXISTS reportstatus")
