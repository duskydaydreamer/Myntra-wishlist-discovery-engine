"""add research safety fields to observations

Revision ID: a1f0c6e3d421
Revises: 9d701427dc2b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1f0c6e3d421"
down_revision: Union[str, None] = "9d701427dc2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("observations", sa.Column("topic", sa.String(), nullable=True))
    op.add_column("observations", sa.Column("sentiment", sa.String(), nullable=True))
    op.add_column("observations", sa.Column("problem_status", sa.String(), nullable=True))
    op.add_column("observations", sa.Column("evidence_scope", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("observations", "evidence_scope")
    op.drop_column("observations", "problem_status")
    op.drop_column("observations", "sentiment")
    op.drop_column("observations", "topic")
