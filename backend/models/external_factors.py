from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

# Fix for type annotations
from datetime import date as DateType

class WeatherCondition(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    STORM = "storm"
    FOG = "fog"

class HolidayType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    REGIONAL = "regional"
    RELIGIOUS = "religious"
    NATIONAL = "national"

class EventType(str, Enum):
    SPORTS = "sports"
    CULTURAL = "cultural"
    BUSINESS = "business"
    SEASONAL = "seasonal"
    LOCAL = "local"

class WeatherData(BaseModel):
    """Weather data for a specific location and date"""
    location: str = Field(..., description="Location identifier (city, coordinates)")
    date: DateType = Field(..., description="Date of weather data")
    temperature_avg: Optional[float] = Field(None, description="Average temperature in Celsius")
    temperature_min: Optional[float] = Field(None, description="Minimum temperature in Celsius")
    temperature_max: Optional[float] = Field(None, description="Maximum temperature in Celsius")
    precipitation: Optional[float] = Field(None, description="Precipitation in mm")
    humidity: Optional[float] = Field(None, description="Humidity percentage")
    wind_speed: Optional[float] = Field(None, description="Wind speed in km/h")
    weather_condition: Optional[WeatherCondition] = Field(None, description="General weather condition")
    seasonal_index: Optional[float] = Field(None, description="Seasonal temperature index (-1 to 1)")
    
    class Config:
        json_encoders = {
            DateType: lambda v: v.isoformat()
        }

class HolidayData(BaseModel):
    """Holiday information for a specific region and date"""
    country: str = Field(..., description="Country code (ISO 3166-1 alpha-2)")
    region: Optional[str] = Field(None, description="Region or state within country")
    date: DateType = Field(..., description="Holiday date")
    name: str = Field(..., description="Holiday name")
    type: HolidayType = Field(..., description="Type of holiday")
    is_observed: bool = Field(True, description="Whether holiday is officially observed")
    impact_days: int = Field(1, description="Number of days the holiday typically affects business")
    
    class Config:
        json_encoders = {
            DateType: lambda v: v.isoformat()
        }

class EventData(BaseModel):
    """Event information that might affect inventory demand"""
    location: str = Field(..., description="Event location")
    date: DateType = Field(..., description="Event date")
    name: str = Field(..., description="Event name")
    type: EventType = Field(..., description="Type of event")
    expected_attendance: Optional[int] = Field(None, description="Expected number of attendees")
    impact_radius: Optional[float] = Field(None, description="Impact radius in kilometers")
    impact_factor: Optional[float] = Field(1.0, description="Expected demand impact factor")
    
    class Config:
        json_encoders = {
            DateType: lambda v: v.isoformat()
        }

class ExternalFactorRequest(BaseModel):
    """Request parameters for external factor data"""
    location: str = Field(..., description="Location for data retrieval")
    start_date: date = Field(..., description="Start date for data range")
    end_date: date = Field(..., description="End date for data range")
    country: Optional[str] = Field("KW", description="Country code for holiday data")
    region: Optional[str] = Field(None, description="Region for localized data")
    include_weather: bool = Field(True, description="Include weather data")
    include_holidays: bool = Field(True, description="Include holiday data")
    include_events: bool = Field(False, description="Include event data")
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }

class ExternalFactorSummary(BaseModel):
    """Summary of external factors for a date range"""
    location: str
    date_range: str
    weather_data: List[WeatherData] = Field(default_factory=list)
    holiday_data: List[HolidayData] = Field(default_factory=list)
    event_data: List[EventData] = Field(default_factory=list)
    weather_correlation_score: Optional[float] = Field(None, description="Weather correlation with historical data")
    holiday_impact_score: Optional[float] = Field(None, description="Holiday impact score")
    seasonal_adjustment: Optional[float] = Field(None, description="Seasonal adjustment factor")
    data_quality_score: float = Field(1.0, description="Overall data quality score (0-1)")
    
class WeatherFactor(BaseModel):
    """Weather factor for forecasting"""
    date: date
    temperature_factor: float = Field(0.0, description="Temperature impact factor (-1 to 1)")
    precipitation_factor: float = Field(0.0, description="Precipitation impact factor (-1 to 1)")
    seasonal_factor: float = Field(0.0, description="Seasonal impact factor (-1 to 1)")
    overall_weather_impact: float = Field(0.0, description="Combined weather impact (-1 to 1)")
    confidence: float = Field(1.0, description="Confidence in weather factor (0-1)")

class HolidayFactor(BaseModel):
    """Holiday factor for forecasting"""
    date: date
    is_holiday: bool = Field(False, description="Whether date is a holiday")
    is_holiday_period: bool = Field(False, description="Whether date is in holiday period")
    holiday_type: Optional[HolidayType] = Field(None, description="Type of holiday if applicable")
    impact_multiplier: float = Field(1.0, description="Holiday impact multiplier")
    days_to_holiday: Optional[int] = Field(None, description="Days until next major holiday")
    days_from_holiday: Optional[int] = Field(None, description="Days since last major holiday")

class EnhancedForecastRequest(BaseModel):
    """Extended forecast request with external factors"""
    # Base forecast parameters (from existing model)
    horizon: int = Field(30, ge=1, le=365, description="Forecast horizon in days")
    confidence_level: float = Field(0.95, ge=0.5, le=0.99, description="Confidence level for intervals")
    seasonal_length: Optional[int] = Field(None, description="Seasonal period length")
    frequency: str = Field("D", description="Data frequency (D=daily, W=weekly, M=monthly)")
    
    # External factor parameters
    location: str = Field(..., description="Location for external factor data")
    country: str = Field("US", description="Country code for regional data")
    region: Optional[str] = Field(None, description="Region for localized data")
    
    # Feature flags
    use_weather_factors: bool = Field(True, description="Include weather factors in forecast")
    use_holiday_factors: bool = Field(True, description="Include holiday factors in forecast")
    use_event_factors: bool = Field(False, description="Include event factors in forecast")
    use_ai_analysis: bool = Field(True, description="Generate AI-powered analysis")
    
    # Advanced options
    weather_sensitivity: float = Field(0.1, ge=0.0, le=1.0, description="Weather sensitivity factor")
    holiday_sensitivity: float = Field(0.2, ge=0.0, le=1.0, description="Holiday sensitivity factor")
    external_factor_weight: float = Field(0.3, ge=0.0, le=1.0, description="Overall external factor weight")

class FactorAttribution(BaseModel):
    """Attribution of forecast changes to specific factors"""
    factor_name: str
    factor_type: str  # weather, holiday, event, seasonal
    impact_percentage: float = Field(description="Percentage contribution to forecast change")
    confidence: float = Field(description="Confidence in attribution (0-1)")
    description: str = Field(description="Human-readable description of factor impact")

class EnhancedForecastResult(BaseModel):
    """Extended forecast results with factor attribution and AI analysis"""
    # Base forecast results (from existing model)
    product_id: str
    product_name: Optional[str] = None
    model_used: str
    forecast_points: List[Dict[str, Any]]  # Will contain enhanced forecast points
    
    # Enhanced results
    external_factors_used: List[str] = Field(default_factory=list, description="List of external factors included")
    factor_attributions: List[FactorAttribution] = Field(default_factory=list, description="Factor impact attributions")
    weather_impact_summary: Optional[str] = Field(None, description="Summary of weather impact")
    holiday_impact_summary: Optional[str] = Field(None, description="Summary of holiday impact")
    
    # AI-generated insights
    ai_trend_explanation: Optional[str] = Field(None, description="AI explanation of forecast trends")
    ai_factor_summary: Optional[str] = Field(None, description="AI summary of factor impacts")
    ai_recommendations: List[str] = Field(default_factory=list, description="AI-generated recommendations")
    ai_risk_assessment: Optional[str] = Field(None, description="AI assessment of forecast risks")
    
    # Enhanced metrics
    baseline_accuracy: Optional[float] = Field(None, description="Baseline model accuracy")
    enhanced_accuracy: Optional[float] = Field(None, description="Enhanced model accuracy with external factors")
    accuracy_improvement: Optional[float] = Field(None, description="Accuracy improvement percentage")
    external_factor_confidence: float = Field(1.0, description="Confidence in external factor data")
    
    # Scenario analysis
    best_case_scenario: Optional[Dict[str, Any]] = Field(None, description="Best case forecast scenario")
    worst_case_scenario: Optional[Dict[str, Any]] = Field(None, description="Worst case forecast scenario")
    most_likely_scenario: Optional[Dict[str, Any]] = Field(None, description="Most likely forecast scenario")

class ExternalFactorConfig(BaseModel):
    """Configuration for external factor integration"""
    # API configurations
    virtualcrossing_api_key: Optional[str] = Field(None, description="Virtual Crossing API key")
    
    # Feature toggles
    weather_enabled: bool = Field(True, description="Enable weather factor integration")
    holidays_enabled: bool = Field(True, description="Enable holiday factor integration")
    events_enabled: bool = Field(True, description="Enable event factor integration")
    ai_analysis_enabled: bool = Field(True, description="Enable AI-powered analysis")
    
    # Cache settings
    weather_cache_ttl: int = Field(3600, description="Weather data cache TTL in seconds")
    holiday_cache_ttl: int = Field(86400, description="Holiday data cache TTL in seconds")
    
    # Quality thresholds
    min_data_quality_score: float = Field(0.7, description="Minimum data quality score to use external factors")
    max_api_retry_attempts: int = Field(3, description="Maximum API retry attempts")
    api_timeout_seconds: int = Field(30, description="API request timeout in seconds")
    
    # Cost controls
    max_daily_api_calls: int = Field(1000, description="Maximum daily API calls")
    max_monthly_cost: float = Field(100.0, description="Maximum monthly cost in USD")

class DataQualityMetrics(BaseModel):
    """Metrics for external data quality assessment"""
    completeness_score: float = Field(description="Data completeness score (0-1)")
    accuracy_score: float = Field(description="Data accuracy score (0-1)")
    timeliness_score: float = Field(description="Data timeliness score (0-1)")
    consistency_score: float = Field(description="Data consistency score (0-1)")
    overall_quality_score: float = Field(description="Overall quality score (0-1)")
    
    missing_data_points: int = Field(0, description="Number of missing data points")
    outlier_data_points: int = Field(0, description="Number of outlier data points")
    stale_data_points: int = Field(0, description="Number of stale data points")
    
    quality_issues: List[str] = Field(default_factory=list, description="List of identified quality issues")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for quality improvement")
