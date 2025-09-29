"""Initial migration: create audit_events_log table

Revision ID: 0001
Revises: 
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_events_log table
    op.create_table('audit_events_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('process_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('events_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('process_date')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_audit_events_log_status', 'audit_events_log', ['status'])
    op.create_index('idx_audit_events_log_process_date_status', 'audit_events_log', ['process_date', 'status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_audit_events_log_process_date_status', table_name='audit_events_log')
    op.drop_index('idx_audit_events_log_status', table_name='audit_events_log')
    
    # Drop table
    op.drop_table('audit_events_log')
