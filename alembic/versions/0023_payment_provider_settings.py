"""store payment provider settings in the database

Revision ID: 0023_payment_provider_settings
Revises: 0022_webapp_start
Create Date: 2026-09-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0023_payment_provider_settings"
down_revision: Union[str, Sequence[str], None] = "0022_webapp_start"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_provider_configs",
        sa.Column("config_encrypted", sa.Text(), nullable=True),
    )
    op.execute(
        """
        INSERT INTO payment_provider_configs (provider_key, display_name, is_enabled, sort_order)
        VALUES ('nalogo', 'Чеки для самозанятого', false, 8)
        ON CONFLICT (provider_key) DO NOTHING
        """
    )
    op.execute("UPDATE payment_provider_configs SET display_name = 'СБП' WHERE provider_key = 'freekassa' AND display_name = 'FreeKassa'")
    op.execute("UPDATE payment_provider_configs SET display_name = 'Картой или СБП' WHERE provider_key = 'platega' AND display_name = 'Platega'")
    op.execute("UPDATE payment_provider_configs SET display_name = 'Картой или СБП' WHERE provider_key = 'severpay' AND display_name = 'SeverPay'")
    op.execute("UPDATE payment_provider_configs SET display_name = 'Картой или СБП' WHERE provider_key = 'yookassa' AND display_name = 'ЮKassa'")
    op.execute("UPDATE payment_provider_configs SET display_name = 'Картой или СБП' WHERE provider_key = 'lavapay' AND display_name = 'LavaPay'")
    op.execute("UPDATE payment_provider_configs SET display_name = 'Криптовалютой' WHERE provider_key = 'cryptopay' AND display_name = 'CryptoPay'")


def downgrade() -> None:
    op.execute("DELETE FROM payment_provider_configs WHERE provider_key = 'nalogo'")
    op.drop_column("payment_provider_configs", "config_encrypted")
