from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Workload(Base):
    __tablename__ = "workloads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    cpu: Mapped[int] = mapped_column(Integer, default=1)
    memory_gb: Mapped[float] = mapped_column(Float, default=1)
    storage_gb: Mapped[float] = mapped_column(Float, default=0)
    os: Mapped[str] = mapped_column(String(255), default="Unknown")
    source_network: Mapped[str] = mapped_column(String(255), default="Unknown")
    target_network: Mapped[str] = mapped_column(String(255), default="")
    power_state: Mapped[str] = mapped_column(String(64), default="Unknown")
    snapshots: Mapped[int] = mapped_column(Integer, default=0)
    nic_count: Mapped[int] = mapped_column(Integer, default=1)
    criticality: Mapped[str] = mapped_column(String(32), default="Medium")
    downtime_minutes: Mapped[int] = mapped_column(Integer, default=60)
    app_group: Mapped[str] = mapped_column(String(128), default="Ungrouped")
    owner: Mapped[str] = mapped_column(String(255), default="")
    data_classification: Mapped[str] = mapped_column(String(32), default="Internal")
    residency: Mapped[str] = mapped_column(String(128), default="")
    rpo_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rto_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    migration_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    migration_risk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    migration_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    wave_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TargetCluster(Base):
    __tablename__ = "target_clusters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    prism_ext_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    country_code: Mapped[str] = mapped_column(String(2), default="")
    site_name: Mapped[str] = mapped_column(String(128), default="")
    physical_cpu_cores: Mapped[int] = mapped_column(Integer, default=1)
    cpu_overcommit_ratio: Mapped[float] = mapped_column(Float, default=4.0)
    allocated_vcpu: Mapped[int] = mapped_column(Integer, default=0)
    total_memory_gb: Mapped[float] = mapped_column(Float, default=1)
    used_memory_gb: Mapped[float] = mapped_column(Float, default=0)
    usable_storage_gb: Mapped[float] = mapped_column(Float, default=1)
    used_storage_gb: Mapped[float] = mapped_column(Float, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlanningAudit(Base):
    __tablename__ = "planning_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MigrationApproval(Base):
    __tablename__ = "migration_approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wave_number: Mapped[int] = mapped_column(Integer, index=True)
    target_cluster_id: Mapped[int] = mapped_column(ForeignKey("target_clusters.id"))
    status: Mapped[str] = mapped_column(String(32), default="Pending", index=True)
    requested_by: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_by: Mapped[str] = mapped_column(String(255), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    change_ticket: Mapped[str] = mapped_column(String(128), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    decision_notes: Mapped[str] = mapped_column(Text, default="")
    headroom_percent: Mapped[float] = mapped_column(Float, default=20.0)


class WorkloadDependency(Base):
    __tablename__ = "workload_dependencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upstream_workload_id: Mapped[int] = mapped_column(ForeignKey("workloads.id"), index=True)
    downstream_workload_id: Mapped[int] = mapped_column(ForeignKey("workloads.id"), index=True)
    dependency_type: Mapped[str] = mapped_column(String(64), default="service")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MigrationExecution(Base):
    __tablename__ = "migration_executions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    approval_id: Mapped[int] = mapped_column(ForeignKey("migration_approvals.id"), index=True)
    wave_number: Mapped[int] = mapped_column(Integer, index=True)
    target_cluster_id: Mapped[int] = mapped_column(ForeignKey("target_clusters.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="Planned", index=True)
    operator: Mapped[str] = mapped_column(String(255))
    move_plan_name: Mapped[str] = mapped_column(String(255), default="")
    change_ticket: Mapped[str] = mapped_column(String(128), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cutover_duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    uat_status: Mapped[str] = mapped_column(String(32), default="NotRun")
    rollback_executed: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_summary: Mapped[str] = mapped_column(Text, default="")
    rollback_reason: Mapped[str] = mapped_column(Text, default="")
    evidence_reference: Mapped[str] = mapped_column(String(512), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
