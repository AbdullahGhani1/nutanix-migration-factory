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
