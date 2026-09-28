"""Initial Migration Factory schema.

Revision ID: 0001_initial
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "target_clusters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("prism_ext_id", sa.String(length=255), nullable=False),
        sa.Column("physical_cpu_cores", sa.Integer(), nullable=False),
        sa.Column("cpu_overcommit_ratio", sa.Float(), nullable=False),
        sa.Column("allocated_vcpu", sa.Integer(), nullable=False),
        sa.Column("total_memory_gb", sa.Float(), nullable=False),
        sa.Column("used_memory_gb", sa.Float(), nullable=False),
        sa.Column("usable_storage_gb", sa.Float(), nullable=False),
        sa.Column("used_storage_gb", sa.Float(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_target_clusters_name", "target_clusters", ["name"])
    op.create_index("ix_target_clusters_prism_ext_id", "target_clusters", ["prism_ext_id"])

    op.create_table(
        "planning_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_planning_audit_event_type", "planning_audit", ["event_type"])

    op.create_table(
        "workloads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("import_batches.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cpu", sa.Integer(), nullable=False),
        sa.Column("memory_gb", sa.Float(), nullable=False),
        sa.Column("storage_gb", sa.Float(), nullable=False),
        sa.Column("os", sa.String(length=255), nullable=False),
        sa.Column("source_network", sa.String(length=255), nullable=False),
        sa.Column("target_network", sa.String(length=255), nullable=False),
        sa.Column("power_state", sa.String(length=64), nullable=False),
        sa.Column("snapshots", sa.Integer(), nullable=False),
        sa.Column("nic_count", sa.Integer(), nullable=False),
        sa.Column("criticality", sa.String(length=32), nullable=False),
        sa.Column("downtime_minutes", sa.Integer(), nullable=False),
        sa.Column("app_group", sa.String(length=128), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("migration_score", sa.Integer(), nullable=True),
        sa.Column("migration_risk", sa.String(length=32), nullable=True),
        sa.Column("migration_reasons", sa.Text(), nullable=True),
        sa.Column("wave_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_workloads_name", "workloads", ["name"])

    op.create_table(
        "migration_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wave_number", sa.Integer(), nullable=False),
        sa.Column("target_cluster_id", sa.Integer(), sa.ForeignKey("target_clusters.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("decided_by", sa.String(length=255), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("change_ticket", sa.String(length=128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("decision_notes", sa.Text(), nullable=False),
        sa.Column("headroom_percent", sa.Float(), nullable=False),
    )
    op.create_index("ix_migration_approvals_wave_number", "migration_approvals", ["wave_number"])
    op.create_index("ix_migration_approvals_status", "migration_approvals", ["status"])

    op.create_table(
        "workload_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("upstream_workload_id", sa.Integer(), sa.ForeignKey("workloads.id"), nullable=False),
        sa.Column("downstream_workload_id", sa.Integer(), sa.ForeignKey("workloads.id"), nullable=False),
        sa.Column("dependency_type", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_workload_dependencies_upstream_workload_id",
        "workload_dependencies",
        ["upstream_workload_id"],
    )
    op.create_index(
        "ix_workload_dependencies_downstream_workload_id",
        "workload_dependencies",
        ["downstream_workload_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workload_dependencies_downstream_workload_id", table_name="workload_dependencies")
    op.drop_index("ix_workload_dependencies_upstream_workload_id", table_name="workload_dependencies")
    op.drop_table("workload_dependencies")

    op.drop_index("ix_migration_approvals_status", table_name="migration_approvals")
    op.drop_index("ix_migration_approvals_wave_number", table_name="migration_approvals")
    op.drop_table("migration_approvals")

    op.drop_index("ix_workloads_name", table_name="workloads")
    op.drop_table("workloads")

    op.drop_index("ix_planning_audit_event_type", table_name="planning_audit")
    op.drop_table("planning_audit")

    op.drop_index("ix_target_clusters_prism_ext_id", table_name="target_clusters")
    op.drop_index("ix_target_clusters_name", table_name="target_clusters")
    op.drop_table("target_clusters")

    op.drop_table("import_batches")
