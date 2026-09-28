"""Add technical validation evidence.

Revision ID: 0003_technical_validation
Revises: 0002_migration_execution
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_technical_validation"
down_revision: Union[str, None] = "0002_migration_execution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "technical_validation_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "execution_id",
            sa.Integer(),
            sa.ForeignKey("migration_executions.id"),
            nullable=False,
        ),
        sa.Column("tool", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("hosts_total", sa.Integer(), nullable=False),
        sa.Column("hosts_passed", sa.Integer(), nullable=False),
        sa.Column("hosts_failed", sa.Integer(), nullable=False),
        sa.Column("prism_validation", sa.String(length=32), nullable=False),
        sa.Column("guest_validation", sa.String(length=32), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("evidence_reference", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_technical_validation_records_execution_id",
        "technical_validation_records",
        ["execution_id"],
    )
    op.create_index(
        "ix_technical_validation_records_status",
        "technical_validation_records",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_technical_validation_records_status",
        table_name="technical_validation_records",
    )
    op.drop_index(
        "ix_technical_validation_records_execution_id",
        table_name="technical_validation_records",
    )
    op.drop_table("technical_validation_records")
