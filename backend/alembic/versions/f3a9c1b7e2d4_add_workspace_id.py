"""add workspace_id to feedback, themes, reports

Revision ID: f3a9c1b7e2d4
Revises: d4f16d65c594
Create Date: 2026-07-22 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a9c1b7e2d4'
down_revision: Union[str, Sequence[str], None] = 'd4f16d65c594'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("feedback", "themes", "reports"):
        op.add_column(table, sa.Column("workspace_id", sa.String(length=50), nullable=False, server_default="demo"))
        op.create_index(f"ix_{table}_workspace_id", table, ["workspace_id"])


def downgrade() -> None:
    for table in ("feedback", "themes", "reports"):
        op.drop_index(f"ix_{table}_workspace_id", table_name=table)
        op.drop_column(table, "workspace_id")
