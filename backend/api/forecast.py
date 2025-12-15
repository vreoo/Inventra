import csv
import io
import os

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from uuid import uuid4
from pathlib import Path
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from models.forecast import (
    ColumnMapping,
    ForecastJob,
    ForecastMode,
    ForecastRequest,
    JobStatus,
    ValidationSummary,
    ValidationAnomaly,
)
from fastapi.responses import StreamingResponse
from services.ai_summarizer import AiSummaryService
from services.file_handler import FileHandler
from services.demand_engine import DemandPlanningEngine
from pydantic import BaseModel

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


class AiSummaryRequest(BaseModel):
    product_id: str


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


def _load_job(job_id: str) -> Dict[str, Any]:
    job_file = JOBS_DIR / f"{job_id}.json"
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with job_file.open("r") as f:
        return json.load(f)


def _format_number(value: Any, precision: Optional[int] = None) -> str:
    if value is None:
        return ""
    try:
        if precision is not None:
            return f"{float(value):.{precision}f}"
        return str(value)
    except Exception:
        return str(value)


def _build_orders_rows(job_data: Dict[str, Any]) -> List[List[str]]:
    results = job_data.get("results") or []
    rows: List[List[str]] = []
    for result in results:
        mode = result.get("mode") or job_data.get("mode") or ""
        rows.append(
            [
                result.get("product_id") or "",
                result.get("product_name") or "",
                mode,
                result.get("demand_frequency") or "",
                result.get("reorder_date") or "",
                _format_number(result.get("recommended_order_qty"), 2),
                _format_number(result.get("reorder_point"), 2),
                _format_number(result.get("safety_stock"), 2),
                result.get("stockout_date") or "",
                _format_number(result.get("starting_inventory"), 2),
                _format_number(result.get("lead_time_days")),
                _format_number(result.get("service_level"), 3),
                result.get("model_used") or "",
                result.get("schema_version")
                or job_data.get("schema_version")
                or "",
                result.get("ai_summary") or "",
            ]
        )
    return rows


def _build_forecast_rows(job_data: Dict[str, Any]) -> List[List[str]]:
    results = job_data.get("results") or []
    rows: List[List[str]] = []
    for result in results:
        mode = result.get("mode") or job_data.get("mode") or ""
        points = result.get("forecast_points") or []
        if not points:
            continue
        for point in points:
            rows.append(
                [
                    result.get("product_id") or "",
                    result.get("product_name") or "",
                    mode,
                    result.get("demand_frequency") or "",
                    point.get("date") or "",
                    _format_number(point.get("forecast"), 4),
                    _format_number(point.get("lower_bound"), 4),
                    _format_number(point.get("upper_bound"), 4),
                    result.get("reorder_date") or "",
                    _format_number(result.get("reorder_point"), 2),
                    _format_number(result.get("recommended_order_qty"), 2),
                    _format_number(result.get("safety_stock"), 2),
                    result.get("stockout_date") or "",
                    _format_number(result.get("starting_inventory"), 2),
                    _format_number(result.get("lead_time_days")),
                    _format_number(result.get("service_level"), 3),
                    result.get("model_used") or "",
                    result.get("schema_version")
                    or job_data.get("schema_version")
                    or "",
                ]
            )
    return rows

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

@router.get("/forecast/{job_id}/export")
async def export_forecast_csv(
    job_id: str,
    kind: str = Query(
        default="orders",
        description="Export view: 'orders' (one row per SKU) or 'forecast' (one row per date per SKU).",
        regex="^(orders|forecast)$",
    ),
):
    """Stream forecast results as CSV for downloads."""
    job_data = _load_job(job_id)
    status = job_data.get("status")
    if status != JobStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Job is not completed yet.")

    results = job_data.get("results") or []
    if not results:
        raise HTTPException(status_code=404, detail="No results available for export.")

    if kind == "forecast":
        headers = [
            "product_id",
            "product_name",
            "mode",
            "demand_frequency",
            "date",
            "forecast",
            "lower_bound",
            "upper_bound",
            "reorder_date",
            "reorder_point",
            "recommended_order_qty",
            "safety_stock",
            "stockout_date",
            "starting_inventory",
            "lead_time_days",
            "service_level",
            "model_used",
            "schema_version",
        ]
        rows = _build_forecast_rows(job_data)
    else:
        headers = [
            "product_id",
            "product_name",
            "mode",
            "demand_frequency",
            "reorder_date",
            "recommended_order_qty",
            "reorder_point",
            "safety_stock",
            "stockout_date",
            "starting_inventory",
            "lead_time_days",
            "service_level",
            "model_used",
            "schema_version",
            "ai_summary",
        ]
        rows = _build_orders_rows(job_data)

    if not rows:
        raise HTTPException(status_code=404, detail="Nothing to export for this job.")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    buffer.seek(0)

    filename = f"forecast-{job_id}-{kind}.csv"
    return StreamingResponse(
        iter([buffer.getvalue().encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/forecast/{job_id}/ai-summary")
async def generate_ai_summary(job_id: str, req: AiSummaryRequest):
    """Generate an AI summary for a single SKU on-demand and persist it on the job."""
    summarizer = get_ai_summary_service()
    if not summarizer:
        raise HTTPException(
            status_code=503,
            detail="AI summaries are disabled or misconfigured on the server.",
        )

    job_data = _load_job(job_id)
    status = job_data.get("status")
    if status != JobStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Job must be completed before requesting an AI summary.")

    results = job_data.get("results") or []
    target_index = None
    target = None
    for idx, item in enumerate(results):
        product_id = item.get("product_id") or item.get("product_name")
        if str(product_id) == str(req.product_id):
            target_index = idx
            target = item
            break

    if target is None or target_index is None:
        raise HTTPException(status_code=404, detail="SKU not found on this job.")

    insights = []
    for insight in target.get("insights") or []:
        if isinstance(insight, dict):
            message = insight.get("message")
            if message:
                insights.append(message)
        elif isinstance(insight, str):
            insights.append(insight)

    mode_value = target.get("mode") or job_data.get("mode")
    if isinstance(mode_value, Enum):
        mode_value = mode_value.value

    payload = {
        "sku": target.get("product_id") or target.get("product_name"),
        "mode": mode_value,
        "horizon": job_data.get("config", {}).get("horizon"),
        "stockout_date": target.get("stockout_date"),
        "reorder_point": target.get("reorder_point"),
        "reorder_date": target.get("reorder_date"),
        "recommended_order_qty": target.get("recommended_order_qty"),
        "safety_stock": target.get("safety_stock"),
        "service_level": target.get("service_level"),
        "insights": insights,
    }

    try:
        ai_summary = summarizer.summarize(job_id, payload)
    except Exception as err:  # pragma: no cover - defensive
        logger.warning(
            "Unable to generate AI summary for job %s sku %s: %s",
            job_id,
            payload.get("sku"),
            err,
        )
        raise HTTPException(status_code=502, detail="AI summary provider unavailable.")

    serialized = {
        "product_id": target.get("product_id"),
        "product_name": target.get("product_name"),
        "ai_summary": ai_summary.summary,
        "ai_actions": ai_summary.actions,
        "ai_risks": ai_summary.risks,
        "ai_source": ai_summary.source,
        "ai_generated_at": ai_summary.generated_at.isoformat(),
    }

    # Persist back to the job file
    target.update(serialized)
    results[target_index] = target
    job_data["results"] = results
    job_file = JOBS_DIR / f"{job_id}.json"
    with job_file.open("w") as f:
        json.dump(job_data, f, default=str)

    return serialized

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
