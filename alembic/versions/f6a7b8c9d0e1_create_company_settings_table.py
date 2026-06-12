"""create company settings table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("company_name", sa.String(length=150), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("tax_number", sa.String(length=100), nullable=True),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("default_currency", sa.String(length=3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", name="uq_company_settings_device_id"),
    )
    op.create_index(op.f("ix_company_settings_id"), "company_settings", ["id"])
    op.create_index(
        op.f("ix_company_settings_device_id"),
        "company_settings",
        ["device_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_company_settings_device_id"), table_name="company_settings")
    op.drop_index(op.f("ix_company_settings_id"), table_name="company_settings")
    op.drop_table("company_settings")
