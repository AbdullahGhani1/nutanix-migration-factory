from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


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
    physical_cpu_cores: int = Field(gt=0)
    cpu_overcommit_ratio: float = Field(gt=0, le=20)
    allocated_vcpu: int = Field(ge=0)
    total_memory_gb: float = Field(gt=0)
    used_memory_gb: float = Field(ge=0)
    usable_storage_gb: float = Field(gt=0)
    used_storage_gb: float = Field(ge=0)
    enabled: bool = True


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
