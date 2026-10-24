"""
src/contracts.py - Data Contracts and Validation Schemas for FOREST HEARTBEAT
Enforces strict typing, reproducibility, and rule compliance (R5, R6).
"""

from typing import List, Dict, Optional, Literal, Tuple
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

class ObservationTimepoint(BaseModel):
    date: str = Field(description="ISO 8601 date YYYY-MM-DD")
    doy: int = Field(description="Day of year 1-366")
    b2: float = Field(description="Blue reflectance (0-1)")
    b3: float = Field(description="Green reflectance (0-1)")
    b4: float = Field(description="Red reflectance (0-1)")
    b8: float = Field(description="NIR reflectance (0-1)")
    b11: float = Field(description="SWIR1 reflectance (0-1)")
    b12: float = Field(description="SWIR2 reflectance (0-1)")
    ndvi: float = Field(description="Normalized Difference Vegetation Index")
    nbr: float = Field(description="Normalized Burn Ratio")
    ndmi: float = Field(description="Normalized Difference Moisture Index")
    is_valid: bool = Field(description="True if unclouded and not shadow")
    cloud_flag: int = Field(description="0=clear, 1=cloud, 2=shadow, 3=cirrus/haze")

class PixelHeartbeat(BaseModel):
    pixel_id: str
    lat: float
    lon: float
    forest_id: str
    baseline_treecover_2000: float = Field(description="Hansen treecover2000 percent (0-100)")
    observations: List[ObservationTimepoint]
    harmonic_expected_ndvi: List[float]
    harmonic_sigma_ndvi: List[float]
    residual_z_scores: List[float]
    break_date_range: Optional[Tuple[str, str]] = None
    break_confidence: float = Field(0.0, ge=0.0, le=1.0)
    classification: Literal["STABLE_FOREST", "VERIFIED_LOSS", "SEASONAL_DECIDUOUS", "UNKNOWN_CLOUD_GAP"]
    cause_attribution: Optional[str] = None
    evidence_summary: str

class AreaAlertSummary(BaseModel):
    forest_id: str
    forest_name: str
    state: str
    date_a: str
    date_b: str
    tree_cover_at_a_ha: float
    loss_by_b_ha: float
    loss_percent: float
    remaining_forest_ha: float
    loss_per_month_ha: float
    mean_confidence: float
    unknown_cloud_ha: float
    cause_breakdown_ha: Dict[str, float]
    provenance: Literal["COMPUTED", "ILLUSTRATIVE"]
    computed_file: str

class MetricWithCI(BaseModel):
    value: float
    ci_lower_95: float
    ci_upper_95: float

class EvaluationResults(BaseModel):
    config_sha256: str
    test_manifest_sha256: str
    evaluated_at: str
    test_state: str
    holdout_year: int
    segmentation_10m: Dict[str, MetricWithCI]
    segmentation_30m_hansen: Dict[str, MetricWithCI]
    false_alarm_per_1000ha_deciduous: MetricWithCI
    recall_by_size: Dict[str, MetricWithCI]
    date_mae_days: MetricWithCI
    date_interval_hit_rate: MetricWithCI
    cause_macro_f1: MetricWithCI
    conformal_empirical_coverage_90: float
    cloud_mask_error_rate: float
    inter_annotator_kappa: float
    ablation_ladder: List[Dict[str, float]]
    runs_log_appended: bool
