"""Add HNM to source_enum

Revision ID: 001_add_hnm
Revises: 
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_add_hnm"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE is not transactional in PostgreSQL,
    # so we must run it outside a transaction block.
    op.execute("ALTER TYPE source_enum ADD VALUE IF NOT EXISTS 'HNM'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    # A full recreation would be needed, which is rarely worth it.
    pass
