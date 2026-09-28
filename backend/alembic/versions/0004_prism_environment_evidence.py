"""Add Prism environment evidence.

Revision ID: 0004_prism_environment_evidence
Revises: 0003_technical_validation
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_prism_environment_evidence"
down_revision: Union[str, None] = "0003_technical_validation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prism_environment_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("clusters", sa.Integer(), nullable=False),
        sa.Column("vms", sa.Integer(), nullable=False),
        sa.Column("subnets", sa.Integer(), nullable=False),
        sa.Column("target_networks", sa.Integer(), nullable=False),
        sa.Column("matched_networks", sa.Integer(), nullable=False),
        sa.Column("missing_networks", sa.Integer(), nullable=False),
        sa.Column("ambiguous_networks", sa.Integer(), nullable=False),
        sa.Column("cluster_inventory_truncated", sa.Boolean(), nullable=False),
        sa.Column("vm_inventory_truncated", sa.Boolean(), nullable=False),
        sa.Column("subnet_inventory_truncated", sa.Boolean(), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=False),
        sa.Column("network_reconciliation_json", sa.Text(), nullable=False),
        sa.Column("evidence_reference", sa.String(length=512), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_prism_environment_evidence_status",
        "prism_environment_evidence",
        ["status"],
    )
    op.create_index(
        "ix_prism_environment_evidence_captured_at",
        "prism_environment_evidence",
        ["captured_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prism_environment_evidence_captured_at",
        table_name="prism_environment_evidence",
    )
    op.drop_index(
        "ix_prism_environment_evidence_status",
        table_name="prism_environment_evidence",
    )
    op.drop_table("prism_environment_evidence")
