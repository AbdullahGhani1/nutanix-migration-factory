from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkloadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    cpu: int
    memory_gb: float
    storage_gb: float
    os: str
    source_network: str
    target_network: str
    power_state: str
    snapshots: int
    nic_count: int
    criticality: str
    downtime_minutes: int
    app_group: str
    owner: str
    data_classification: str
    residency: str
    rpo_minutes: int | None
    rto_minutes: int | None
    migration_score: int | None
    migration_risk: str | None
    migration_reasons: str | None
    wave_number: int | None


class ImportResult(BaseModel):
    batch_id: int
    filename: str
    imported: int


class AssessmentSummary(BaseModel):
    assessed: int
    low: int
    medium: int
    high: int


class WaveSummary(BaseModel):
    waves: int
    workloads: int


class NetworkMappingRule(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    description: str | None = None


class NetworkMappingRequest(BaseModel):
    rules: list[NetworkMappingRule]


class NetworkMappingResponse(BaseModel):
    total: int
    mapped: int
    unmapped: int


class ReadinessWorkload(BaseModel):
    workload_id: int
    name: str
    status: str
    blockers: list[str]
    warnings: list[str]


class ReadinessResponse(BaseModel):
    total: int
    ready: int
    ready_with_warnings: int
    blocked: int
    workloads: list[ReadinessWorkload]


class TargetClusterIn(BaseModel):
    name: str = Field(min_length=1)
    prism_ext_id: str = ""
    country_code: str = Field(default="", pattern=r"^([A-Za-z]{2})?$")
    site_name: str = ""
    physical_cpu_cores: int = Field(gt=0)
    cpu_overcommit_ratio: float = Field(gt=0, le=20)
    allocated_vcpu: int = Field(ge=0)
    total_memory_gb: float = Field(gt=0)
    used_memory_gb: float = Field(ge=0)
    usable_storage_gb: float = Field(gt=0)
    used_storage_gb: float = Field(ge=0)
    enabled: bool = True

    @field_validator("country_code")
    @classmethod
    def _upper_country(cls, value: str) -> str:
        return value.upper()


class TargetClusterOut(TargetClusterIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class WaveDemand(BaseModel):
    wave: int
    workloads: int
    vcpu: int
    memory_gb: float
    storage_gb: float


class ClusterCapacityResult(BaseModel):
    cluster_id: int
    cluster_name: str
    fit: bool
    score: float
    reasons: list[str]
    effective_vcpu_capacity: float
    projected_vcpu: float
    projected_memory_gb: float
    projected_storage_gb: float
    max_vcpu_after_headroom: float
    max_memory_after_headroom_gb: float
    max_storage_after_headroom_gb: float


class CapacityEvaluationResponse(BaseModel):
    headroom_percent: float
    demand: WaveDemand
    candidates: list[ClusterCapacityResult]


class PrismClusterReconciliation(BaseModel):
    prism_ext_id: str
    prism_name: str
    local_cluster_id: int | None
    local_cluster_name: str | None
    status: str


class PrismReconciliationResponse(BaseModel):
    prism_clusters: int
    matched: int
    unmatched: int
    results: list[PrismClusterReconciliation]


class ApprovalRequest(BaseModel):
    target_cluster_id: int
    requested_by: str = Field(min_length=1)
    change_ticket: str = ""
    notes: str = ""
    headroom_percent: float = Field(default=20.0, ge=0, le=50)


class ApprovalDecision(BaseModel):
    decision: str
    decided_by: str = Field(min_length=1)
    notes: str = ""


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    wave_number: int
    target_cluster_id: int
    status: str
    requested_by: str
    requested_at: datetime
    decided_by: str
    decided_at: datetime | None
    change_ticket: str
    notes: str
    decision_notes: str
    headroom_percent: float


class DependencyCreate(BaseModel):
    upstream_workload_id: int
    downstream_workload_id: int
    dependency_type: str = "service"
    notes: str = ""


class DependencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    upstream_workload_id: int
    downstream_workload_id: int
    dependency_type: str
    notes: str


class DependencyGraphNode(BaseModel):
    id: int
    name: str
    wave_number: int | None


class DependencyGraphEdge(BaseModel):
    id: int
    upstream_workload_id: int
    downstream_workload_id: int
    dependency_type: str


class DependencyGraphResponse(BaseModel):
    nodes: list[DependencyGraphNode]
    edges: list[DependencyGraphEdge]
    has_cycle: bool
    start_order: list[int]
    stop_order: list[int]


class PrismEnvironmentSummary(BaseModel):
    connected: bool
    clusters: int
    vms: int
    subnets: int
    cluster_inventory_truncated: bool
    vm_inventory_truncated: bool
    subnet_inventory_truncated: bool


class NetworkReconciliationItem(BaseModel):
    target_network: str
    status: str
    matches: list[dict]


class NetworkReconciliationResponse(BaseModel):
    targets: int
    matched: int
    missing: int
    ambiguous: int
    results: list[NetworkReconciliationItem]


class ExecutionCreate(BaseModel):
    approval_id: int
    operator: str = Field(min_length=1)
    move_plan_name: str = ""
    evidence_reference: str = ""
    notes: str = ""


class ExecutionTransition(BaseModel):
    action: str
    actor: str = Field(min_length=1)
    cutover_duration_minutes: float | None = Field(default=None, ge=0)
    uat_status: str | None = None
    validation_summary: str = ""
    rollback_reason: str = ""
    evidence_reference: str | None = None
    notes: str = ""


class ExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    approval_id: int
    wave_number: int
    target_cluster_id: int
    status: str
    operator: str
    move_plan_name: str
    change_ticket: str
    started_at: datetime | None
    completed_at: datetime | None
    cutover_duration_minutes: float | None
    uat_status: str
    rollback_executed: bool
    validation_summary: str
    rollback_reason: str
    evidence_reference: str
    notes: str
    created_at: datetime


class ResidencyRequest(BaseModel):
    cluster_id: int
    dr_cluster_id: int | None = None
    wave: int | None = None


class ResidencyWorkload(BaseModel):
    workload_id: int
    name: str
    classification: str
    allowed_countries: list[str] | None
    status: str
    violations: list[str]
    warnings: list[str]


class ResidencyResponse(BaseModel):
    cluster: str
    dr_cluster: str | None
    total: int
    compliant: int
    unverified: int
    violations: int
    workloads: list[ResidencyWorkload]


class DRPlanRequest(BaseModel):
    wave: int | None = None
    primary_cluster_id: int | None = None
    dr_cluster_id: int | None = None
    site_rtt_ms: float | None = Field(default=None, ge=0)
    sync_max_rtt_ms: float = Field(default=5.0, gt=0)
    daily_change_rate_percent: float = Field(default=5.0, gt=0, le=100)
    nearsync_max_minutes: int = Field(default=15, ge=1, le=59)
    available_bandwidth_mbps: float | None = Field(default=None, gt=0)
    peak_factor: float = Field(default=2.0, ge=1, le=10)


class ChangeWindowIn(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0 = Monday")
    start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration_minutes: int = Field(gt=0, le=24 * 60)


class CalendarPeriodIn(BaseModel):
    start: date
    end: date
    kind: str = Field(default="blackout", pattern=r"^(blackout|restricted)$")
    reason: str = Field(min_length=1)


class ChangeCalendarRequest(BaseModel):
    start_date: date
    periods: list[CalendarPeriodIn] = []
    windows: list[ChangeWindowIn] | None = None
    weeks: int = Field(default=26, ge=1, le=104)
    min_gap_days: int = Field(default=7, ge=0, le=60)
    parallel_cutovers: int = Field(default=5, ge=1, le=50)
    per_vm_cutover_minutes: int = Field(default=30, ge=5, le=600)
    precheck_minutes: int = Field(default=60, ge=0, le=600)
    validation_minutes: int = Field(default=60, ge=0, le=600)
    rollback_reserve_minutes: int = Field(default=60, ge=0, le=600)
