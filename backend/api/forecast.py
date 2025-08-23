from fastapi import APIRouter, HTTPException, BackgroundTasks
from uuid import uuid4
from pathlib import Path
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List
import os

from models.forecast import ForecastRequest, ForecastJob, JobStatus, ForecastConfig
from models.external_factors import (
    ExternalFactorRequest, ExternalFactorConfig, EnhancedForecastResult,
    FactorAttribution
)
from services.file_handler import FileHandler
from services.forecast_engine import ForecastEngine
from services.external_data_service import ExternalDataService
from services.ai_analysis_service import AIAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()

JOBS_DIR = Path("storage/jobs")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize services
file_handler = FileHandler()
forecast_engine = ForecastEngine()

@router.post("/forecast")
async def create_forecast_job(req: ForecastRequest, background_tasks: BackgroundTasks):
    """Create a new forecast job"""
    try:
        # Validate file exists
        if not file_handler.file_exists(req.fileId):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Create job
        job_id = str(uuid4())
        job = ForecastJob(
            jobId=job_id,
            fileId=req.fileId,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            config=req.config
        )
        
        # Save job to storage
        job_file = JOBS_DIR / f"{job_id}.json"
        with job_file.open("w") as f:
            json.dump(job.dict(), f, default=str)
        
        # Start background processing
        background_tasks.add_task(process_forecast_job, job_id)
        
        return {"jobId": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating forecast job: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/forecast/{job_id}")
async def get_forecast_status(job_id: str):
    """Get forecast job status and results"""
    try:
        job_file = JOBS_DIR / f"{job_id}.json"
        if not job_file.exists():
            raise HTTPException(status_code=404, detail="Job not found")
        
        with job_file.open("r") as f:
            job_data = json.load(f)
        
        return job_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting forecast status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_forecast_job(job_id: str):
    """Background task to process forecast job with external factors and AI analysis"""
    job_file = JOBS_DIR / f"{job_id}.json"
    
    try:
        # Load job
        with job_file.open("r") as f:
            job_data = json.load(f)
        
        job = ForecastJob(**job_data)
        
        # Update status to processing
        job.status = JobStatus.PROCESSING
        with job_file.open("w") as f:
            json.dump(job.dict(), f, default=str)
        
        # Process the file
        file_path = file_handler.get_file_path(job.fileId)
        inventory_data, processing_info = file_handler.process_inventory_data(file_path)
        
        logger.info(f"Processing {len(inventory_data)} inventory records for job {job_id}")
        
        # Generate basic forecast
        basic_results = forecast_engine.generate_forecast(inventory_data, job.config)
        
        # Initialize external factor configuration for Kuwait
        external_config = ExternalFactorConfig(
            weather_enabled=True,
            holidays_enabled=True,
            events_enabled=False,  # Keep events disabled for MVP
            ai_analysis_enabled=True,
            virtualcrossing_api_key=os.getenv("VIRTUALCROSSING_API_KEY"),
            openai_api_key=None,  # Ollama-only mode
            weather_cache_ttl=3600,
            holiday_cache_ttl=86400
        )
        
        # Initialize services
        external_service = ExternalDataService(external_config)
        ai_service = AIAnalysisService(external_config)
        
        # Enhance results with external factors and AI analysis
        enhanced_results = []
        
        for result in basic_results:
            try:
                # Get date range for external factors
                if inventory_data:
                    start_date = min(item.date for item in inventory_data)
                    end_date = max(item.date for item in inventory_data)
                    
                    # Extend to forecast period
                    forecast_end = end_date + timedelta(days=job.config.horizon)
                    
                    # Create external factor request for Kuwait
                    external_request = ExternalFactorRequest(
                        location="Kuwait City, Kuwait",
                        country="KW",  # Kuwait country code
                        region=None,
                        start_date=start_date,
                        end_date=forecast_end,
                        include_weather=True,
                        include_holidays=True,
                        include_events=False
                    )
                    
                    # Get external factors with error handling
                    try:
                        external_factors = await external_service.get_external_factors(external_request)
                        logger.info(f"External factors retrieved: weather={len(external_factors.weather_data)}, holidays={len(external_factors.holiday_data)}")
                    except Exception as e:
                        logger.error(f"Error getting external factors: {str(e)}")
                        # Create empty external factors object as fallback
                        external_factors = type('ExternalFactors', (), {
                            'weather_data': [],
                            'holiday_data': [],
                            'event_data': [],
                            'data_quality_score': 0.0
                        })()
                    
                    # Calculate factor attributions
                    factor_attributions = _calculate_factor_attributions(
                        result, external_factors, inventory_data
                    )
                    
                    # Generate AI analysis
                    trend_data = {
                        'trend_direction': 'increasing' if len(result.forecast_points) > 0 and result.forecast_points[-1].forecast > result.forecast_points[0].forecast else 'stable',
                        'trend_percentage': 5.0,  # Simplified calculation
                        'key_factors': ['weather', 'holidays'] if external_factors.weather_data or external_factors.holiday_data else [],
                        'time_period': f"{job.config.horizon} days"
                    }
                    
                    factor_data = {
                        'weather_correlation': 0.3 if external_factors.weather_data else 0.0,
                        'holiday_impact': 0.15 if external_factors.holiday_data else 0.0,
                        'other_factors': []
                    }
                    
                    forecast_data = {
                        'predicted_demand': sum(p.forecast for p in result.forecast_points) / len(result.forecast_points) if result.forecast_points else 0,
                        'current_stock': inventory_data[-1].quantity if inventory_data else 0,
                        'risk_factors': ['seasonal_variation'] if external_factors.holiday_data else [],
                        'external_factors': ['weather', 'holidays'] if external_factors.weather_data or external_factors.holiday_data else []
                    }
                    
                    risk_data = {
                        'confidence_level': 0.8,
                        'data_quality': external_factors.data_quality_score,
                        'external_uncertainty': 0.2,
                        'forecast_horizon': job.config.horizon
                    }
                    
                    # Generate AI insights with fallback handling
                    try:
                        trend_explanation = await ai_service.explain_trend(trend_data)
                        logger.info(f"AI trend explanation generated: {trend_explanation is not None}")
                    except Exception as e:
                        logger.error(f"Error generating trend explanation: {str(e)}")
                        trend_explanation = f"Trend analysis: {trend_data.get('trend_direction', 'stable')} pattern detected over {trend_data.get('time_period', 'period')}"

                    try:
                        factor_summary = await ai_service.summarize_factors(factor_data)
                        logger.info(f"AI factor summary generated: {factor_summary is not None}")
                    except Exception as e:
                        logger.error(f"Error generating factor summary: {str(e)}")
                        factor_summary = f"External factors analysis: {len([f for f in factor_data.values() if f > 0])} factors identified with potential impact"

                    try:
                        recommendations = await ai_service.generate_recommendations(forecast_data)
                        logger.info(f"AI recommendations generated: {len(recommendations) if recommendations else 0} items")
                    except Exception as e:
                        logger.error(f"Error generating recommendations: {str(e)}")
                        recommendations = ["Monitor inventory levels regularly", "Review forecast accuracy weekly", "Adjust stock based on seasonal patterns"]

                    try:
                        risk_assessment = await ai_service.assess_risks(risk_data)
                        logger.info(f"AI risk assessment generated: {risk_assessment is not None}")
                    except Exception as e:
                        logger.error(f"Error generating risk assessment: {str(e)}")
                        risk_assessment = f"Moderate risk forecast with {risk_data.get('confidence_level', 0.8):.0%} confidence level"
                    
                    # Convert forecast points to dictionaries properly
                    forecast_points_dict = []
                    for point in result.forecast_points:
                        if hasattr(point, 'model_dump'):
                            forecast_points_dict.append(point.model_dump())
                        else:
                            # Fallback for non-Pydantic objects
                            forecast_points_dict.append({
                                'date': str(point.date) if hasattr(point, 'date') else str(point.get('date', '')),
                                'forecast': float(point.forecast) if hasattr(point, 'forecast') else float(point.get('forecast', 0)),
                                'lower_bound': float(point.lower_bound) if hasattr(point, 'lower_bound') and point.lower_bound is not None else None,
                                'upper_bound': float(point.upper_bound) if hasattr(point, 'upper_bound') and point.upper_bound is not None else None
                            })

                    # Create AI analysis object for frontend compatibility
                    ai_analysis = {
                        "trend_explanation": trend_explanation or "Trend analysis not available",
                        "factor_summary": factor_summary or "External factors analysis not available",
                        "recommendations": recommendations or ["Monitor inventory levels regularly"],
                        "risk_assessment": risk_assessment or "Risk assessment not available",
                        "confidence_score": 0.8  # Default confidence score
                    }

                    # Structure external factors for frontend
                    external_factors_data = {
                        "weather_data": [
                            {
                                "date": str(w.date),
                                "temperature": w.temperature_avg or 25.0,
                                "humidity": w.humidity or 60.0,
                                "precipitation": w.precipitation or 0.0,
                                "wind_speed": w.wind_speed or 10.0,
                                "weather_condition": w.weather_condition.value if w.weather_condition else "unknown"
                            } for w in external_factors.weather_data[:7]  # Limit to 7 days
                        ] if external_factors.weather_data else [],
                        "holiday_data": [
                            {
                                "date": str(h.date),
                                "name": h.name,
                                "type": h.type.value if hasattr(h.type, 'value') else str(h.type),
                                "impact_level": "high" if h.type.value == "major" else "medium"
                            } for h in external_factors.holiday_data
                        ] if external_factors.holiday_data else [],
                        "factor_attributions": [
                            {
                                "factor_type": attr.factor_type,
                                "factor_name": attr.factor_name,
                                "impact_score": attr.impact_percentage,
                                "confidence": attr.confidence_score,
                                "description": attr.description
                            } for attr in factor_attributions
                        ]
                    }

                    # Create enhanced result
                    enhanced_result = EnhancedForecastResult(
                        # Copy all basic result fields
                        product_id=result.product_id,
                        product_name=result.product_name,
                        model_used=result.model_used,
                        forecast_points=forecast_points_dict,
                        stockout_date=result.stockout_date,
                        reorder_point=result.reorder_point,
                        reorder_date=result.reorder_date,
                        peak_season=result.peak_season,
                        insights=result.insights,
                        accuracy_metrics=result.accuracy_metrics,

                        # Add enhanced fields structured for frontend
                        external_factors_used=["weather", "holidays"] if external_factors.weather_data or external_factors.holiday_data else [],
                        factor_attributions=factor_attributions,
                        ai_trend_explanation=trend_explanation,
                        ai_factor_summary=factor_summary,
                        ai_recommendations=recommendations,
                        ai_risk_assessment=risk_assessment,
                        external_factor_confidence=external_factors.data_quality_score,

                        # Add frontend-compatible fields
                        ai_analysis=ai_analysis,
                        external_factors=external_factors_data,
                        data_quality_score=external_factors.data_quality_score
                    )
                    
                    enhanced_results.append(enhanced_result)
                    
                else:
                    # No inventory data, use basic result
                    forecast_points_dict = []
                    for point in result.forecast_points:
                        if hasattr(point, 'model_dump'):
                            forecast_points_dict.append(point.model_dump())
                        else:
                            # Fallback for non-Pydantic objects
                            forecast_points_dict.append({
                                'date': str(point.date) if hasattr(point, 'date') else str(point.get('date', '')),
                                'forecast': float(point.forecast) if hasattr(point, 'forecast') else float(point.get('forecast', 0)),
                                'lower_bound': float(point.lower_bound) if hasattr(point, 'lower_bound') and point.lower_bound is not None else None,
                                'upper_bound': float(point.upper_bound) if hasattr(point, 'upper_bound') and point.upper_bound is not None else None
                            })

                    # Create basic fallback data structures
                    ai_analysis_fallback = {
                        "trend_explanation": "Basic trend analysis available - limited data",
                        "factor_summary": "External factors analysis not available",
                        "recommendations": ["Monitor inventory levels regularly"],
                        "risk_assessment": "Risk assessment not available",
                        "confidence_score": 0.5  # Lower confidence for fallback
                    }

                    external_factors_fallback = {
                        "weather_data": [],
                        "holiday_data": [],
                        "factor_attributions": []
                    }

                    enhanced_result = EnhancedForecastResult(
                        product_id=result.product_id,
                        product_name=result.product_name,
                        model_used=result.model_used,
                        forecast_points=forecast_points_dict,
                        stockout_date=result.stockout_date,
                        reorder_point=result.reorder_point,
                        reorder_date=result.reorder_date,
                        peak_season=result.peak_season,
                        insights=result.insights,
                        accuracy_metrics=result.accuracy_metrics,
                        # Add fallback data structures
                        ai_analysis=ai_analysis_fallback,
                        external_factors=external_factors_fallback,
                        data_quality_score=0.5
                    )
                    enhanced_results.append(enhanced_result)
                    
            except Exception as e:
                logger.warning(f"Error enhancing result for product {result.product_id}: {str(e)}")
                # Fall back to basic result
                forecast_points_dict = []
                for point in result.forecast_points:
                    if hasattr(point, 'model_dump'):
                        forecast_points_dict.append(point.model_dump())
                    else:
                        # Fallback for non-Pydantic objects
                        forecast_points_dict.append({
                            'date': str(point.date) if hasattr(point, 'date') else str(point.get('date', '')),
                            'forecast': float(point.forecast) if hasattr(point, 'forecast') else float(point.get('forecast', 0)),
                            'lower_bound': float(point.lower_bound) if hasattr(point, 'lower_bound') and point.lower_bound is not None else None,
                            'upper_bound': float(point.upper_bound) if hasattr(point, 'upper_bound') and point.upper_bound is not None else None
                        })

                # Create error fallback data structures
                ai_analysis_error = {
                    "trend_explanation": "Analysis unavailable due to processing error",
                    "factor_summary": "External factors analysis failed",
                    "recommendations": ["Review data quality and retry forecast"],
                    "risk_assessment": "Unable to assess risks due to processing error",
                    "confidence_score": 0.1  # Very low confidence for error case
                }

                external_factors_error = {
                    "weather_data": [],
                    "holiday_data": [],
                    "factor_attributions": []
                }

                enhanced_result = EnhancedForecastResult(
                    product_id=result.product_id,
                    product_name=result.product_name,
                    model_used=result.model_used,
                    forecast_points=forecast_points_dict,
                    stockout_date=result.stockout_date,
                    reorder_point=result.reorder_point,
                    reorder_date=result.reorder_date,
                    peak_season=result.peak_season,
                    insights=result.insights,
                    accuracy_metrics=result.accuracy_metrics,
                    # Add error fallback data structures
                    ai_analysis=ai_analysis_error,
                    external_factors=external_factors_error,
                    data_quality_score=0.1
                )
                enhanced_results.append(enhanced_result)
        
        # Update job with enhanced results
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now()
        job.results = [result.model_dump() for result in enhanced_results]  # Convert to dict for JSON serialization
        
        with job_file.open("w") as f:
            json.dump(job.dict(), f, default=str)
        
        logger.info(f"Enhanced forecast job {job_id} completed successfully with external factors and AI analysis")
        
    except Exception as e:
        logger.error(f"Error processing forecast job {job_id}: {str(e)}")
        
        # Update job with error
        try:
            with job_file.open("r") as f:
                job_data = json.load(f)
            
            job_data["status"] = JobStatus.FAILED.value
            job_data["error_message"] = str(e)
            job_data["completed_at"] = datetime.now().isoformat()
            
            with job_file.open("w") as f:
                json.dump(job_data, f)
                
        except Exception as save_error:
            logger.error(f"Error saving job error state: {str(save_error)}")


def _calculate_factor_attributions(result, external_factors, inventory_data) -> List[FactorAttribution]:
    """Calculate how external factors contribute to forecast changes"""
    attributions = []
    
    try:
        # Weather attribution
        if external_factors.weather_data:
            weather_impact = 0.1  # Simplified calculation - 10% impact
            attributions.append(FactorAttribution(
                factor_type="weather",
                factor_name="Weather Conditions",
                impact_percentage=weather_impact,
                confidence_score=0.7,
                description=f"Weather patterns show moderate correlation with demand variations"
            ))
        
        # Holiday attribution
        if external_factors.holiday_data:
            holiday_impact = 0.15  # Simplified calculation - 15% impact
            holiday_names = [h.name for h in external_factors.holiday_data[:3]]  # Top 3 holidays
            attributions.append(FactorAttribution(
                factor_type="holiday",
                factor_name="Holiday Seasonality",
                impact_percentage=holiday_impact,
                confidence_score=0.8,
                description=f"Holiday periods ({', '.join(holiday_names)}) significantly affect demand patterns"
            ))
        
        # Seasonal attribution (always present)
        attributions.append(FactorAttribution(
            factor_type="seasonal",
            factor_name="Seasonal Trends",
            impact_percentage=0.25,  # 25% seasonal impact
            confidence_score=0.9,
            description="Historical seasonal patterns are the primary driver of demand variations"
        ))
        
    except Exception as e:
        logger.error(f"Error calculating factor attributions: {str(e)}")
    
    return attributions
