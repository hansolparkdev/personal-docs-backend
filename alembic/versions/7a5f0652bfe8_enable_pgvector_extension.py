"""enable pgvector extension

Revision ID: 7a5f0652bfe8
Revises: 
Create Date: 2026-04-20 14:52:46.219237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7a5f0652bfe8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
