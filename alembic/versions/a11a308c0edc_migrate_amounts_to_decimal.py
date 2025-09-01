"""migrate_amounts_to_decimal

Revision ID: a11a308c0edc
Revises: eb4d511e7c2a
Create Date: 2025-08-27 23:39:23.309383

"""
from typing import Sequence, Union

from alembic import op
# revision identifiers, used by Alembic.
revision: str = 'a11a308c0edc'
down_revision: Union[str, Sequence[str], None] = 'eb4d511e7c2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - migrate amounts from String to Numeric(38,8)."""
    # Convert balances.balance
    op.execute("ALTER TABLE balances ALTER COLUMN balance TYPE NUMERIC(38,8) USING balance::NUMERIC(38,8)")
    
    # Convert brc20_operations.amount
    op.execute("ALTER TABLE brc20_operations ALTER COLUMN amount TYPE NUMERIC(38,8) USING amount::NUMERIC(38,8)")
    
    # Convert deploys.max_supply
    op.execute("ALTER TABLE deploys ALTER COLUMN max_supply TYPE NUMERIC(38,8) USING max_supply::NUMERIC(38,8)")
    
    # Convert deploys.limit_per_op
    op.execute("ALTER TABLE deploys ALTER COLUMN limit_per_op TYPE NUMERIC(38,8) USING limit_per_op::NUMERIC(38,8)")


def downgrade() -> None:
    """Downgrade schema - revert amounts back to String."""
    # Convert balances.balance back to String
    op.execute("ALTER TABLE balances ALTER COLUMN balance TYPE VARCHAR USING balance::VARCHAR")
    
    # Convert brc20_operations.amount back to String
    op.execute("ALTER TABLE brc20_operations ALTER COLUMN amount TYPE VARCHAR USING amount::VARCHAR")
    
    # Convert deploys.max_supply back to String
    op.execute("ALTER TABLE deploys ALTER COLUMN max_supply TYPE VARCHAR USING max_supply::VARCHAR")
    
    # Convert deploys.limit_per_op back to String
    op.execute("ALTER TABLE deploys ALTER COLUMN limit_per_op TYPE VARCHAR USING limit_per_op::VARCHAR")