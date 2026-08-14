"""initial_schema

Revision ID: 001
Revises: 
Create Date: 2026-08-14 19:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('purchase_date', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_devices_user_id', 'devices', ['user_id'])
    op.create_index('ix_devices_category', 'devices', ['category'])

    # Create diagnoses table
    op.create_table(
        'diagnoses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('device_category', sa.String(length=50), nullable=False),
        sa.Column('problem_summary', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, default='medium'),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('technician_required', sa.Boolean(), nullable=False, default=False),
        sa.Column('technician_reason', sa.Text(), nullable=True),
        sa.Column('ai_provider', sa.String(length=50), nullable=True),
        sa.Column('ai_model', sa.String(length=100), nullable=True),
        sa.Column('ai_latency_ms', sa.Integer(), nullable=True),
        sa.Column('ai_input_tokens', sa.Integer(), nullable=True),
        sa.Column('ai_output_tokens', sa.Integer(), nullable=True),
        sa.Column('ai_estimated_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_diagnoses_user_id', 'diagnoses', ['user_id'])
    op.create_index('ix_diagnoses_device_id', 'diagnoses', ['device_id'])
    op.create_index('ix_diagnoses_device_category', 'diagnoses', ['device_category'])
    op.create_index('ix_diagnoses_status', 'diagnoses', ['status'])
    op.create_index('ix_diagnoses_created_at', 'diagnoses', ['created_at'])

    # Create diagnosis_messages table
    op.create_table(
        'diagnosis_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('diagnosis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnoses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_diagnosis_messages_diagnosis_id', 'diagnosis_messages', ['diagnosis_id'])

    # Create diagnosis_results table
    op.create_table(
        'diagnosis_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('diagnosis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('possible_causes', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('safe_steps', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('risks', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('follow_up_questions', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('disclaimer', sa.Text(), nullable=False),
        sa.Column('raw_ai_response', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnoses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_diagnosis_results_diagnosis_id', 'diagnosis_results', ['diagnosis_id'])

    # Create diagnosis_feedback table
    op.create_table(
        'diagnosis_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('diagnosis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('was_helpful', sa.Boolean(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnoses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_diagnosis_feedback_diagnosis_id', 'diagnosis_feedback', ['diagnosis_id'])
    op.create_index('ix_diagnosis_feedback_user_id', 'diagnosis_feedback', ['user_id'])

    # Create ai_request_logs table
    op.create_table(
        'ai_request_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('diagnosis_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('prompt_version', sa.String(length=50), nullable=True),
        sa.Column('request_payload', postgresql.JSONB(), nullable=False),
        sa.Column('response_payload', postgresql.JSONB(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnoses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_request_logs_diagnosis_id', 'ai_request_logs', ['diagnosis_id'])
    op.create_index('ix_ai_request_logs_provider', 'ai_request_logs', ['provider'])
    op.create_index('ix_ai_request_logs_created_at', 'ai_request_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('ai_request_logs')
    op.drop_table('diagnosis_feedback')
    op.drop_table('diagnosis_results')
    op.drop_table('diagnosis_messages')
    op.drop_table('diagnoses')
    op.drop_table('devices')
    op.drop_table('users')