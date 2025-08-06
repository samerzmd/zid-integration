"""add store_id to zid_credentials

Revision ID: c30ebf96137e
Revises: 001
Create Date: 2025-08-06 15:53:20.906344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c30ebf96137e'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # Add store_id as nullable initially
    op.add_column(
        'zid_credentials',
        sa.Column('store_id', sa.Integer(), nullable=True),
    )
    # If you want an index on store_id for faster lookups, uncomment:
    # op.create_index('idx_zid_credentials_store_id', 'zid_credentials', ['store_id'])

def downgrade():
    # If you created an index, drop it first:
    # op.drop_index('idx_zid_credentials_store_id', table_name='zid_credentials')
    op.drop_column('zid_credentials', 'store_id')