import os

from fastapi import APIRouter, HTTPException, BackgroundTasks
from uuid import uuid4
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Optional

from models.forecast import (
    ColumnMapping,
    ForecastJob,
    ForecastMode,
    ForecastRequest,
    JobStatus,
    ValidationSummary,
    ValidationAnomaly,
)
from services.ai_summarizer import AiSummaryService
from services.file_handler import FileHandler
from services.demand_engine import DemandPlanningEngine

logger = logging.getLogger(__name__)

router = APIRouter()

JOBS_DIR = Path("storage/jobs")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SCHEMA_VERSION = "1.0.0"
DEMAND_PLANNING_ENABLED = (
    os.getenv("DEMAND_PLANNING_ENABLED", "true").lower() == "true"
)
ENABLE_AI_SUMMARY = os.getenv("ENABLE_AI_SUMMARY", "false").lower() == "true"
AI_SUMMARY_MODEL = os.getenv("AI_SUMMARY_MODEL", "HuggingFaceH4/zephyr-7b-beta")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_BASE_URL = os.getenv("HF_API_BASE_URL")
AI_SUMMARY_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv("AI_SUMMARY_FALLBACK_MODELS", "").split(",")
    if model.strip()
]

# Initialize services
file_handler = FileHandler()
demand_engine = DemandPlanningEngine()
_ai_summary_service: Optional[AiSummaryService] = None


def get_ai_summary_service() -> Optional[AiSummaryService]:
    global _ai_summary_service

    if not ENABLE_AI_SUMMARY:
        return None

    if _ai_summary_service:
        return _ai_summary_service

    if not HF_API_TOKEN:
        logger.warning(
            "AI summary is enabled but HF_API_TOKEN is not configured; skipping summaries"
        )
        return None

    _ai_summary_service = AiSummaryService(
        api_token=HF_API_TOKEN,
        model=AI_SUMMARY_MODEL,
        base_url=HF_API_BASE_URL,
        fallback_models=AI_SUMMARY_FALLBACK_MODELS or None,
    )
    logger.info(
        "AI summary service initialised (model=%s, base_url=%s, fallbacks=%s)",
        AI_SUMMARY_MODEL,
        HF_API_BASE_URL or "default",
        AI_SUMMARY_FALLBACK_MODELS or "none",
    )
    return _ai_summary_service

@router.post("/forecast")
async def create_forecast_job(req: ForecastRequest, background_tasks: BackgroundTasks):
    """Create a new forecast job"""
    try:
        # Validate file exists
        if not file_handler.file_exists(req.fileId):
            raise HTTPException(status_code=404, detail="File not found")
        metadata = file_handler.get_upload_metadata(req.fileId) or {}

        base_mapping = metadata.get("mapping") or {}
        mapping = ColumnMapping(**base_mapping) if base_mapping else ColumnMapping()
        if req.mapping_overrides:
            overrides = {
                key: value
                for key, value in req.mapping_overrides.dict(
                    exclude_unset=True, exclude_none=True
                ).items()
                if value
            }
            for key, value in overrides.items():
                setattr(mapping, key, value)

        mode = req.mode
        metadata_mode = metadata.get("mode")
        if metadata_mode:
            try:
                mode = ForecastMode(metadata_mode)
            except ValueError:
                logger.warning("Unknown mode '%s' in metadata for file %s", metadata_mode, req.fileId)

        schema_version = (
            req.schema_version
            or metadata.get("schema_version")
            or DEFAULT_SCHEMA_VERSION
        )

        validation_summary = None
        if metadata.get("validation_summary"):
            summary_dict = metadata["validation_summary"]
            anomalies = [
                ValidationAnomaly(**anomaly)
                for anomaly in summary_dict.get("anomalies", [])
            ]
            validation_summary = ValidationSummary(
                rows=summary_dict.get("rows", 0),
                columns=summary_dict.get("columns", []),
                detected_frequency=summary_dict.get("detected_frequency"),
                date_coverage_pct=summary_dict.get("date_coverage_pct"),
                missing_by_field=summary_dict.get("missing_by_field", {}),
                anomalies=anomalies,
            )
        else:
            file_path = file_handler.get_file_path(req.fileId)
            validation_result = file_handler.validate_csv_file(file_path, mode)
            summary_dict = validation_result.get("summary") or {}
            anomalies = [
                ValidationAnomaly(**anomaly)
                for anomaly in summary_dict.get("anomalies", [])
            ]
            validation_summary = ValidationSummary(
                rows=summary_dict.get("rows", validation_result.get("info", {}).get("rows", 0)),
                columns=summary_dict.get("columns", validation_result.get("info", {}).get("columns", [])),
                detected_frequency=summary_dict.get("detected_frequency"),
                date_coverage_pct=summary_dict.get("date_coverage_pct"),
                missing_by_field=summary_dict.get("missing_by_field", {}),
                anomalies=anomalies,
            )

        if mode == ForecastMode.DEMAND and (not mapping.date or not mapping.demand):
            raise HTTPException(
                status_code=400,
                detail="Demand mode requires mapped date and demand columns.",
            )

        config = req.config
        if (
            validation_summary
            and validation_summary.detected_frequency
            and validation_summary.detected_frequency != config.frequency
        ):
            config.frequency = validation_summary.detected_frequency

        if config.enable_ai_summary is None:
            config.enable_ai_summary = ENABLE_AI_SUMMARY
        else:
            config.enable_ai_summary = bool(
                config.enable_ai_summary and ENABLE_AI_SUMMARY
            )

        # Create job
        job_id = str(uuid4())
        job = ForecastJob(
            jobId=job_id,
            fileId=req.fileId,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            config=config,
            mode=mode,
            schema_version=schema_version,
            mapping=mapping,
            validation=validation_summary,
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
    """Background task to process forecast job"""
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
        
        metadata = file_handler.get_upload_metadata(job.fileId) or {}
        mapping_dict = metadata.get("mapping") or {}
        mapping = job.mapping or ColumnMapping(**mapping_dict)

        artifacts = file_handler.prepare_demand_artifacts(
            job.fileId,
            mapping,
            job.config,
        )

        logger.info(
            "Processing demand planning for %s with %d rows",
            job.fileId,
            len(artifacts.demand_df),
        )

        results = demand_engine.generate(
            artifacts=artifacts,
            config=job.config,
            schema_version=job.schema_version,
        )

        job.validation = artifacts.validation
        job.mapping = mapping
        if (
            artifacts.validation.detected_frequency
            and job.config
            and artifacts.validation.detected_frequency != job.config.frequency
        ):
            job.config.frequency = artifacts.validation.detected_frequency

        summarizer = get_ai_summary_service()
        if summarizer and results:
            allow_ai = True
            if job.config and job.config.enable_ai_summary is not None:
                allow_ai = job.config.enable_ai_summary

            if not allow_ai:
                logger.info(
                    "Skipping AI summary for job %s due to config flag (enable_ai_summary=%s)",
                    job.jobId,
                    job.config.enable_ai_summary if job.config else None,
                )
                summarizer = None
        elif not summarizer:
            logger.info(
                "AI summarizer unavailable for job %s (env_enabled=%s, token_present=%s)",
                job.jobId,
                ENABLE_AI_SUMMARY,
                bool(HF_API_TOKEN),
            )

        if summarizer and results:
            for result in results:
                insights = []
                if getattr(result, "insights", None):
                    for insight in result.insights:
                        message = getattr(insight, "message", None)
                        if message:
                            insights.append(message)

                mode_value = None
                if hasattr(result, "mode") and result.mode is not None:
                    mode_value = (
                        result.mode.value if hasattr(result.mode, "value") else result.mode
                    )
                elif job.mode:
                    mode_value = job.mode.value if hasattr(job.mode, "value") else job.mode

                payload = {
                    "sku": getattr(result, "product_id", None)
                    or getattr(result, "product_name", None),
                    "mode": mode_value,
                    "horizon": job.config.horizon if job.config else None,
                    "stockout_date": getattr(result, "stockout_date", None),
                    "reorder_point": getattr(result, "reorder_point", None),
                    "reorder_date": getattr(result, "reorder_date", None),
                    "recommended_order_qty": getattr(result, "recommended_order_qty", None),
                    "safety_stock": getattr(result, "safety_stock", None),
                    "service_level": getattr(result, "service_level", None),
                    "insights": insights,
                }
                try:
                    ai_summary = summarizer.summarize(job.jobId, payload)
                except Exception as err:  # pragma: no cover - defensive
                    logger.warning(
                        "Unable to generate AI summary for job %s sku %s: %s",
                        job.jobId,
                        payload.get("sku"),
                        err,
                    )
                    continue

                result.ai_summary = ai_summary.summary
                result.ai_actions = ai_summary.actions
                result.ai_risks = ai_summary.risks
                result.ai_source = ai_summary.source
                result.ai_generated_at = ai_summary.generated_at

        # Update job with results
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now()
        job.results = results
        
        with job_file.open("w") as f:
            json.dump(job.dict(), f, default=str)
        
        logger.info(f"Forecast job {job_id} completed successfully")
        
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
