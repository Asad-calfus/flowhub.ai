"""add churn_reviews table

Revision ID: c1d8e4f9a2b3
Revises: b9f4d21a7c58
Create Date: 2026-07-22 00:00:00.000002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d8e4f9a2b3'
down_revision: Union[str, Sequence[str], None] = 'b9f4d21a7c58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'churn_reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=50), server_default='demo', nullable=False),
        sa.Column('customer_id', sa.String(length=30), nullable=False),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'customer_id', name='uq_churn_review_customer'),
    )
    op.create_index(op.f('ix_churn_reviews_workspace_id'), 'churn_reviews', ['workspace_id'])
    op.create_index(op.f('ix_churn_reviews_customer_id'), 'churn_reviews', ['customer_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_churn_reviews_customer_id'), table_name='churn_reviews')
    op.drop_index(op.f('ix_churn_reviews_workspace_id'), table_name='churn_reviews')
    op.drop_table('churn_reviews')
