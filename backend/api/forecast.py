from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from pathlib import Path
import json
import time
import random

router = APIRouter()

JOBS_DIR = Path("storage/jobs")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

class ForecastRequest(BaseModel):
    fileId: str
    config: dict

@router.post("/forecast")
def create_forecast_job(req: ForecastRequest):
    # Validate input
    if not req.fileId or not req.config:
        raise HTTPException(status_code=400, detail="Missing fileId or config")

    # Simulate background job creation
    job_id = str(uuid4())
    job_data = {
        "jobId": job_id,
        "fileId": req.fileId,
        "status": "PENDING",
        "results": None
    }

    job_file = JOBS_DIR / f"{job_id}.json"
    with job_file.open("w") as f:
        json.dump(job_data, f)

    return {"jobId": job_id}

@router.get("/forecast/{job_id}")
def get_forecast_status(job_id: str):
    job_file = JOBS_DIR / f"{job_id}.json"
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with job_file.open("r") as f:
        job_data = json.load(f)

    # Simulate long-running job becoming complete
    if job_data["status"] == "PENDING":
        # Randomly decide to mark as completed
        if random.random() > 0.5:  # 50% chance to complete
            job_data["status"] = "COMPLETED"
            job_data["results"] = {
                "stockoutDate": "2025-08-12",
                "reorderPoint": 35,
                "peakSeason": "Q4",
                "insights": [
                    "Inventory trend increasing in Q3",
                    "Projected stockout within 24 days",
                    "Reorder advised on August 5"
                ]
            }
            with job_file.open("w") as f:
                json.dump(job_data, f)

    return job_data