from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ForecastModel(str, Enum):
    AUTO_ARIMA = "AutoARIMA"
    ETS = "ETS"
    SEASONAL_NAIVE = "SeasonalNaive"
    NAIVE = "Naive"
    RANDOM_WALK_DRIFT = "RandomWalkWithDrift"

class ForecastConfig(BaseModel):
    model: ForecastModel = ForecastModel.AUTO_ARIMA
    horizon: int = Field(default=30, ge=1, le=365, description="Forecast horizon in days")
    frequency: str = Field(default="D", description="Data frequency (D=daily, W=weekly, M=monthly)")
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)
    seasonal_length: Optional[int] = Field(default=None, description="Seasonal period length")

class InventoryData(BaseModel):
    date: str
    product_id: str
    quantity: float
    product_name: Optional[str] = None

class ForecastRequest(BaseModel):
    fileId: str
    config: ForecastConfig

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
    stockout_date: Optional[str] = None
    reorder_point: Optional[float] = None
    reorder_date: Optional[str] = None
    peak_season: Optional[str] = None
    insights: List[ForecastInsight]
    accuracy_metrics: Optional[Dict[str, float]] = None

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
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: Optional[List[ForecastResult]] = None
    config: Optional[ForecastConfig] = None
