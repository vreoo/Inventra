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
from services.file_handler import FileHandler
from services.forecast_engine import ForecastEngine
from services.demand_engine import DemandPlanningEngine

logger = logging.getLogger(__name__)

router = APIRouter()

JOBS_DIR = Path("storage/jobs")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SCHEMA_VERSION = "1.0.0"
DEMAND_PLANNING_ENABLED = (
    os.getenv("DEMAND_PLANNING_ENABLED", "true").lower() == "true"
)

# Initialize services
file_handler = FileHandler()
forecast_engine = ForecastEngine()
demand_engine = DemandPlanningEngine()

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

        if mode == ForecastMode.DEMAND and not DEMAND_PLANNING_ENABLED:
            raise HTTPException(
                status_code=403,
                detail="Demand planning is disabled on this environment.",
            )

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
        
        if job.mode == ForecastMode.DEMAND:
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
        else:
            file_path = file_handler.get_file_path(job.fileId)
            inventory_data, _ = file_handler.process_inventory_data(
                file_path, job.mapping
            )

            logger.info(
                "Processing %d inventory records for job %s",
                len(inventory_data),
                job_id,
            )

            results = forecast_engine.generate_forecast(inventory_data, job.config)
        
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
