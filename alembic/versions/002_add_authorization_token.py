"""Add authorization_token field to merchant_tokens table

Revision ID: 002
Revises: 001
Create Date: 2025-01-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add authorization_token column to merchant_tokens table
    op.add_column('merchant_tokens', sa.Column('authorization_token', sa.Text(), nullable=True))
    
    # Update existing records to have a placeholder value
    # In production, you might want to handle this differently
    op.execute("UPDATE merchant_tokens SET authorization_token = access_token WHERE authorization_token IS NULL")
    
    # Make the column non-nullable after updating existing records
    op.alter_column('merchant_tokens', 'authorization_token', nullable=False)


def downgrade() -> None:
    # Remove authorization_token column from merchant_tokens table
    op.drop_column('merchant_tokens', 'authorization_token')