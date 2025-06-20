"""Add KYC tier system and enhanced security features

Revision ID: 002_kyc_tiers_security
Revises: 001_initial_schema
Create Date: 2025-06-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '002_kyc_tiers_security'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to kyc_job table
    op.add_column('kyc_job', sa.Column('kyc_tier', sa.Integer(), server_default='0', nullable=False))
    op.add_column('kyc_job', sa.Column('liveness_score', sa.Float(), nullable=True))
    op.add_column('kyc_job', sa.Column('auto_approved', sa.Boolean(), server_default='False', nullable=False))
    op.add_column('kyc_job', sa.Column('risk_score', sa.Float(), nullable=True))
    op.add_column('kyc_job', sa.Column('data_retention_until', sa.DateTime(), nullable=True))
    op.add_column('kyc_job', sa.Column('deletion_requested_at', sa.DateTime(), nullable=True))
    op.add_column('kyc_job', sa.Column('encrypted_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Update status column to include new statuses
    # Note: In PostgreSQL, we need to handle ENUM updates carefully
    op.execute("ALTER TYPE kyc_status ADD VALUE 'processing'")
    op.execute("ALTER TYPE kyc_status ADD VALUE 'manual_review'")
    op.execute("ALTER TYPE kyc_status ADD VALUE 'failed'")
    
    # Create indexes for better performance
    op.create_index('idx_kyc_job_tier', 'kyc_job', ['kyc_tier'])
    op.create_index('idx_kyc_job_status_tier', 'kyc_job', ['status', 'kyc_tier'])
    op.create_index('idx_kyc_job_retention', 'kyc_job', ['data_retention_until'])
    op.create_index('idx_kyc_job_risk_score', 'kyc_job', ['risk_score'])
    
    # Create audit log table if it doesn't exist
    audit_log_table = op.create_table('audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('kyc_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['kyc_job_id'], ['kyc_job.ticket_id'], ),
    )
    
    # Create indexes for audit log
    op.create_index('idx_audit_log_action', 'audit_log', ['action'])
    op.create_index('idx_audit_log_timestamp', 'audit_log', ['timestamp'])
    op.create_index('idx_audit_log_user', 'audit_log', ['user_id'])
    op.create_index('idx_audit_log_kyc_job', 'audit_log', ['kyc_job_id'])
    
    # Add constraints for KYC tier
    op.create_check_constraint('ck_kyc_tier_valid', 'kyc_job', 'kyc_tier >= 0 AND kyc_tier <= 2')
    
    # Add constraints for scores
    op.create_check_constraint('ck_risk_score_valid', 'kyc_job', 'risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 1)')
    op.create_check_constraint('ck_face_score_valid', 'kyc_job', 'face_score IS NULL OR (face_score >= 0 AND face_score <= 1)')
    op.create_check_constraint('ck_liveness_score_valid', 'kyc_job', 'liveness_score IS NULL OR (liveness_score >= 0 AND liveness_score <= 1)')

def downgrade():
    # Remove constraints
    op.drop_constraint('ck_liveness_score_valid', 'kyc_job', type_='check')
    op.drop_constraint('ck_face_score_valid', 'kyc_job', type_='check')
    op.drop_constraint('ck_risk_score_valid', 'kyc_job', type_='check')
    op.drop_constraint('ck_kyc_tier_valid', 'kyc_job', type_='check')
    
    # Drop audit log table
    op.drop_index('idx_audit_log_kyc_job', 'audit_log')
    op.drop_index('idx_audit_log_user', 'audit_log')
    op.drop_index('idx_audit_log_timestamp', 'audit_log')
    op.drop_index('idx_audit_log_action', 'audit_log')
    op.drop_table('audit_log')
    
    # Drop indexes from kyc_job
    op.drop_index('idx_kyc_job_risk_score', 'kyc_job')
    op.drop_index('idx_kyc_job_retention', 'kyc_job')
    op.drop_index('idx_kyc_job_status_tier', 'kyc_job')
    op.drop_index('idx_kyc_job_tier', 'kyc_job')
    
    # Remove columns from kyc_job
    op.drop_column('kyc_job', 'encrypted_data')
    op.drop_column('kyc_job', 'deletion_requested_at')
    op.drop_column('kyc_job', 'data_retention_until')
    op.drop_column('kyc_job', 'risk_score')
    op.drop_column('kyc_job', 'auto_approved')
    op.drop_column('kyc_job', 'liveness_score')
    op.drop_column('kyc_job', 'kyc_tier')
    
    # Note: Removing ENUM values is complex in PostgreSQL and may require recreating the type
    # For simplicity, we'll leave the new status values in place
