from fastapi import APIRouter, HTTPException, BackgroundTasks
from uuid import uuid4
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Optional

from models.forecast import ForecastRequest, ForecastJob, JobStatus, ForecastConfig
from services.file_handler import FileHandler
from services.forecast_engine import ForecastEngine

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
        
        # Process the file
        file_path = file_handler.get_file_path(job.fileId)
        inventory_data, processing_info = file_handler.process_inventory_data(file_path)
        
        logger.info(f"Processing {len(inventory_data)} inventory records for job {job_id}")
        
        # Generate forecast
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
