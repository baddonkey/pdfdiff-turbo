"""add app config

Revision ID: 0008_app_config
Revises: 0007_job_has_diffs
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008_app_config"
down_revision = "0007_job_has_diffs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("allow_registration", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enable_dropzone", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.execute("INSERT INTO app_config (id, allow_registration, enable_dropzone) VALUES (1, true, true)")
    op.alter_column("app_config", "allow_registration", server_default=None)
    op.alter_column("app_config", "enable_dropzone", server_default=None)


def downgrade() -> None:
    op.drop_table("app_config")
