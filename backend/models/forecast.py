from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ForecastMode(str, Enum):
    INVENTORY = "inventory"
    DEMAND = "demand"

class ForecastModel(str, Enum):
    AUTO_ARIMA = "AutoARIMA"
    AUTO_ETS = "AutoETS"
    SEASONAL_NAIVE = "SeasonalNaive"
    NAIVE = "Naive"
    RANDOM_WALK_DRIFT = "RandomWalkWithDrift"
    SKLEARN_MODEL = "SklearnModel"
    CROSTON_CLASSIC = "CrostonClassic"
    CROSTON_OPTIMIZED = "CrostonOptimized"
    CROSTON_SBA = "CrostonSBA"
    TBATS = "TBATS"

class ForecastConfig(BaseModel):
    model: ForecastModel = ForecastModel.AUTO_ARIMA
    horizon: int = Field(default=90, ge=1, le=365, description="Forecast horizon in days")
    frequency: str = Field(default="D", description="Data frequency (D=daily, W=weekly, M=monthly)")
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)
    seasonal_length: Optional[int] = Field(default=None, description="Seasonal period length")
    service_level: float = Field(default=0.95, ge=0.5, le=0.999, description="Target service level for safety stock")
    lead_time_days_default: int = Field(default=7, ge=0, le=365, description="Default lead time when SKU specific data missing")
    safety_stock_policy: str = Field(default="ss_z_score", description="Safety stock policy identifier")
    reorder_policy: str = Field(default="continuous_review", description="Reorder policy identifier")
    enable_tbats: bool = Field(default=False, description="Attempt TBATS model when dependency available")

class InventoryData(BaseModel):
    date: str
    product_id: str
    quantity: float
    product_name: Optional[str] = None


class ColumnMapping(BaseModel):
    date: Optional[str] = None
    sku: Optional[str] = None
    demand: Optional[str] = None
    inventory: Optional[str] = None
    lead_time: Optional[str] = None
    name: Optional[str] = None
    promo_flag: Optional[str] = None
    holiday_flag: Optional[str] = None


class ValidationAnomaly(BaseModel):
    unique_id: str
    date: str
    value: float
    z_score: float


class ValidationSummary(BaseModel):
    rows: int
    columns: List[str]
    detected_frequency: Optional[str] = None
    date_coverage_pct: Optional[float] = None
    missing_by_field: Dict[str, float] = Field(default_factory=dict)
    anomalies: List[ValidationAnomaly] = Field(default_factory=list)

class ForecastRequest(BaseModel):
    fileId: str
    config: ForecastConfig
    mode: ForecastMode = ForecastMode.INVENTORY
    schema_version: Optional[str] = None
    mapping_overrides: Optional[ColumnMapping] = None

class ForecastPoint(BaseModel):
    date: str
    forecast: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

class ForecastInsight(BaseModel):
    type: str
    message: str
    severity: str  # "info", "warning", "critical"
    value: Optional[float] = None

class ForecastResult(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    model_used: str
    forecast_points: List[ForecastPoint]
    mode: ForecastMode = ForecastMode.INVENTORY
    stockout_date: Optional[str] = None
    reorder_point: Optional[float] = None
    reorder_date: Optional[str] = None
    peak_season: Optional[str] = None
    insights: List[ForecastInsight]
    accuracy_metrics: Optional[Dict[str, float]] = None
    safety_stock: Optional[float] = None
    recommended_order_qty: Optional[float] = None
    service_level: Optional[float] = None
    lead_time_days: Optional[int] = None
    starting_inventory: Optional[float] = None
    demand_frequency: Optional[str] = None
    schema_version: Optional[str] = None

class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ForecastJob(BaseModel):
    jobId: str
    fileId: str
    status: JobStatus
    created_at: datetime
    mode: ForecastMode = ForecastMode.INVENTORY
    schema_version: Optional[str] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: Optional[List[ForecastResult]] = None
    config: Optional[ForecastConfig] = None
    validation: Optional[ValidationSummary] = None
    mapping: Optional[ColumnMapping] = None


class ConfigScope(str, Enum):
    GLOBAL = "global"
    SKU = "sku"


class ConfigUpdate(BaseModel):
    scope: ConfigScope = ConfigScope.GLOBAL
    target: Optional[str] = None
    settings: Dict[str, Any]
    author: Optional[str] = None


class ConfigRecord(ConfigUpdate):
    timestamp: str
    version: str
