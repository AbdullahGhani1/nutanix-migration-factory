"""Add migration execution evidence.

Revision ID: 0002_migration_execution
Revises: 0001_initial
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_migration_execution"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "migration_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("approval_id", sa.Integer(), sa.ForeignKey("migration_approvals.id"), nullable=False),
        sa.Column("wave_number", sa.Integer(), nullable=False),
        sa.Column("target_cluster_id", sa.Integer(), sa.ForeignKey("target_clusters.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("operator", sa.String(length=255), nullable=False),
        sa.Column("move_plan_name", sa.String(length=255), nullable=False),
        sa.Column("change_ticket", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cutover_duration_minutes", sa.Float(), nullable=True),
        sa.Column("uat_status", sa.String(length=32), nullable=False),
        sa.Column("rollback_executed", sa.Boolean(), nullable=False),
        sa.Column("validation_summary", sa.Text(), nullable=False),
        sa.Column("rollback_reason", sa.Text(), nullable=False),
        sa.Column("evidence_reference", sa.String(length=512), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_migration_executions_approval_id", "migration_executions", ["approval_id"])
    op.create_index("ix_migration_executions_wave_number", "migration_executions", ["wave_number"])
    op.create_index("ix_migration_executions_target_cluster_id", "migration_executions", ["target_cluster_id"])
    op.create_index("ix_migration_executions_status", "migration_executions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_migration_executions_status", table_name="migration_executions")
    op.drop_index("ix_migration_executions_target_cluster_id", table_name="migration_executions")
    op.drop_index("ix_migration_executions_wave_number", table_name="migration_executions")
    op.drop_index("ix_migration_executions_approval_id", table_name="migration_executions")
    op.drop_table("migration_executions")
