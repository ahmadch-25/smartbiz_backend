"""add device id to user data

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_DEVICE_ID = "00000000-0000-0000-0000-000000000000"


def add_device_id(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column(
            "device_id",
            sa.String(length=36),
            server_default=LEGACY_DEVICE_ID,
            nullable=False,
        ),
    )
    op.create_index(
        op.f(f"ix_{table_name}_device_id"),
        table_name,
        ["device_id"],
        unique=False,
    )
    op.alter_column(table_name, "device_id", server_default=None)


def drop_device_id(table_name: str) -> None:
    op.drop_index(op.f(f"ix_{table_name}_device_id"), table_name=table_name)
    op.drop_column(table_name, "device_id")


def upgrade() -> None:
    add_device_id("clients")
    add_device_id("invoices")
    add_device_id("invoice_items")
    add_device_id("payment_records")


def downgrade() -> None:
    drop_device_id("payment_records")
    drop_device_id("invoice_items")
    drop_device_id("invoices")
    drop_device_id("clients")
