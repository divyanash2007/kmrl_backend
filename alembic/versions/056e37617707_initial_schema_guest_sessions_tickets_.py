"""Initial schema guest_sessions tickets audit_logs

Revision ID: 056e37617707
Revises: 
Create Date: 2026-11-09 16:14:07.529954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '056e37617707'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. guest_sessions
    op.create_table(
        'guest_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('guest_identifier', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_active', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guest_sessions_guest_identifier'), 'guest_sessions', ['guest_identifier'], unique=False)

    # 2. tickets
    op.create_table(
        'tickets',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('guest_session_id', sa.String(length=36), nullable=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('user_latitude', sa.Float(), nullable=True),
        sa.Column('user_longitude', sa.Float(), nullable=True),
        sa.Column('location_accuracy', sa.Float(), nullable=True),
        sa.Column('predicted_category', sa.String(length=100), nullable=False),
        sa.Column('classification_confidence', sa.Float(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('sla_hours', sa.Integer(), nullable=False),
        sa.Column('requires_human_intervention', sa.Boolean(), nullable=True),
        sa.Column('ai_response', sa.Text(), nullable=False),
        sa.Column('ai_referenced_docs', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('is_user_satisfied', sa.Boolean(), nullable=True),
        sa.Column('user_feedback_comment', sa.Text(), nullable=True),
        sa.Column('official_notes', sa.Text(), nullable=True),
        sa.Column('official_id', sa.String(length=50), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['guest_session_id'], ['guest_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tickets_created_at'), 'tickets', ['created_at'], unique=False)
    op.create_index(op.f('ix_tickets_id'), 'tickets', ['id'], unique=False)
    op.create_index(op.f('ix_tickets_predicted_category'), 'tickets', ['predicted_category'], unique=False)
    op.create_index(op.f('ix_tickets_priority'), 'tickets', ['priority'], unique=False)
    op.create_index(op.f('ix_tickets_status'), 'tickets', ['status'], unique=False)

    # 3. official_audit_logs
    op.create_table(
        'official_audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ticket_id', sa.String(length=32), nullable=False),
        sa.Column('official_id', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_official_audit_logs_ticket_id'), 'official_audit_logs', ['ticket_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_official_audit_logs_ticket_id'), table_name='official_audit_logs')
    op.drop_table('official_audit_logs')
    op.drop_index(op.f('ix_tickets_status'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_priority'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_predicted_category'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_created_at'), table_name='tickets')
    op.drop_table('tickets')
    op.drop_index(op.f('ix_guest_sessions_guest_identifier'), table_name='guest_sessions')
    op.drop_table('guest_sessions')
