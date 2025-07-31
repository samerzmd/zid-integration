"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create merchant_tokens table
    op.create_table('merchant_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('merchant_id', sa.String(), nullable=False),
    sa.Column('access_token', sa.Text(), nullable=False),
    sa.Column('refresh_token', sa.Text(), nullable=False),
    sa.Column('expires_in', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_merchant_tokens_id'), 'merchant_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_merchant_tokens_merchant_id'), 'merchant_tokens', ['merchant_id'], unique=True)
    
    # Create webhook_events table
    op.create_table('webhook_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('event_id', sa.String(), nullable=True),
    sa.Column('merchant_id', sa.String(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('processed', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_events_event_id'), 'webhook_events', ['event_id'], unique=True)
    op.create_index(op.f('ix_webhook_events_event_type'), 'webhook_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_webhook_events_id'), 'webhook_events', ['id'], unique=False)
    op.create_index(op.f('ix_webhook_events_merchant_id'), 'webhook_events', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_webhook_events_processed'), 'webhook_events', ['processed'], unique=False)


def downgrade() -> None:
    # Drop webhook_events table
    op.drop_index(op.f('ix_webhook_events_processed'), table_name='webhook_events')
    op.drop_index(op.f('ix_webhook_events_merchant_id'), table_name='webhook_events')
    op.drop_index(op.f('ix_webhook_events_id'), table_name='webhook_events')
    op.drop_index(op.f('ix_webhook_events_event_type'), table_name='webhook_events')
    op.drop_index(op.f('ix_webhook_events_event_id'), table_name='webhook_events')
    op.drop_table('webhook_events')
    
    # Drop merchant_tokens table
    op.drop_index(op.f('ix_merchant_tokens_merchant_id'), table_name='merchant_tokens')
    op.drop_index(op.f('ix_merchant_tokens_id'), table_name='merchant_tokens')
    op.drop_table('merchant_tokens')