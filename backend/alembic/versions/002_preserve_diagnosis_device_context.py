"""preserve diagnosis device context

Revision ID: 002
Revises: 001
Create Date: 2026-08-15 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("diagnoses", sa.Column("device_brand", sa.String(length=100), nullable=True))
    op.add_column("diagnoses", sa.Column("device_model", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("diagnoses", "device_model")
    op.drop_column("diagnoses", "device_brand")
