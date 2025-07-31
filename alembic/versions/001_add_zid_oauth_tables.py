"""Add Zid OAuth authentication tables

Revision ID: 001
Revises: 
Create Date: 2025-07-31 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create zid_credentials table
    op.create_table('zid_credentials',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('merchant_id', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('authorization_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('merchant_id')
    )
    
    # Create indexes for zid_credentials
    op.create_index('idx_merchant_active', 'zid_credentials', ['merchant_id', 'is_active'])
    op.create_index('idx_expires_at', 'zid_credentials', ['expires_at'])
    op.create_index(op.f('ix_zid_credentials_merchant_id'), 'zid_credentials', ['merchant_id'])
    
    # Create oauth_states table
    op.create_table('oauth_states',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('state_hash', sa.String(), nullable=False),
        sa.Column('merchant_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('state_hash')
    )
    
    # Create indexes for oauth_states
    op.create_index('idx_state_expires', 'oauth_states', ['state_hash', 'expires_at'])
    op.create_index('idx_expires_cleanup', 'oauth_states', ['expires_at'])
    op.create_index(op.f('ix_oauth_states_state_hash'), 'oauth_states', ['state_hash'])
    
    # Create token_audit_logs table
    op.create_table('token_audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('merchant_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for token_audit_logs
    op.create_index('idx_merchant_timestamp', 'token_audit_logs', ['merchant_id', 'timestamp'])
    op.create_index('idx_action_timestamp', 'token_audit_logs', ['action', 'timestamp'])
    op.create_index(op.f('ix_token_audit_logs_merchant_id'), 'token_audit_logs', ['merchant_id'])

def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_token_audit_logs_merchant_id'), table_name='token_audit_logs')
    op.drop_index('idx_action_timestamp', table_name='token_audit_logs')
    op.drop_index('idx_merchant_timestamp', table_name='token_audit_logs')
    
    op.drop_index(op.f('ix_oauth_states_state_hash'), table_name='oauth_states')
    op.drop_index('idx_expires_cleanup', table_name='oauth_states')
    op.drop_index('idx_state_expires', table_name='oauth_states')
    
    op.drop_index(op.f('ix_zid_credentials_merchant_id'), table_name='zid_credentials')
    op.drop_index('idx_expires_at', table_name='zid_credentials')
    op.drop_index('idx_merchant_active', table_name='zid_credentials')
    
    # Drop tables
    op.drop_table('token_audit_logs')
    op.drop_table('oauth_states')
    op.drop_table('zid_credentials')