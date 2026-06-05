"""allow ai draft invoice without client

Revision ID: c1d2e3f4a5b6
Revises: 9b7a0c4d2e13
Create Date: 2026-06-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "9b7a0c4d2e13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "invoices",
        "client_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "invoices",
        "client_name",
        existing_type=sa.String(length=150),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "invoices",
        "client_name",
        existing_type=sa.String(length=150),
        nullable=False,
    )
    op.alter_column(
        "invoices",
        "client_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
