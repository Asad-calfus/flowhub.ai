"""add corrections table

Revision ID: b9f4d21a7c58
Revises: a7c3e91f2b6d
Create Date: 2026-07-22 00:00:00.000001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9f4d21a7c58'
down_revision: Union[str, Sequence[str], None] = 'a7c3e91f2b6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'corrections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=50), server_default='demo', nullable=False),
        sa.Column('feedback_id', sa.String(length=20), nullable=False),
        sa.Column('field', sa.String(length=30), nullable=False),
        sa.Column('original_value', sa.String(length=60), nullable=False),
        sa.Column('corrected_value', sa.String(length=60), nullable=False),
        sa.Column('corrected_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['feedback_id'], ['feedback.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_corrections_workspace_id'), 'corrections', ['workspace_id'])
    op.create_index(op.f('ix_corrections_feedback_id'), 'corrections', ['feedback_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_corrections_feedback_id'), table_name='corrections')
    op.drop_index(op.f('ix_corrections_workspace_id'), table_name='corrections')
    op.drop_table('corrections')
