from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    migration_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    migration_risk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    migration_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    wave_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
