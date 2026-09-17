"""add configurable Web App start message and photo

Revision ID: 0022_webapp_start
Revises: 0021_panel_user_id
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0022_webapp_start"
down_revision: Union[str, Sequence[str], None] = "0021_panel_user_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("site_settings", sa.Column("webapp_start_message", sa.Text(), nullable=True))
    op.add_column("site_settings", sa.Column("webapp_start_photo_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("site_settings", "webapp_start_photo_url")
    op.drop_column("site_settings", "webapp_start_message")
