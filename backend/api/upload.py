import os

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from uuid import uuid4
from pathlib import Path
import logging

from models.forecast import ColumnMapping, ForecastMode, ValidationAnomaly, ValidationSummary
from services.file_handler import FileHandler

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEMAND_PLANNING_ENABLED = (
    os.getenv("DEMAND_PLANNING_ENABLED", "false").lower() == "true"
)
DEFAULT_UPLOAD_MODE = (
    ForecastMode.DEMAND if DEMAND_PLANNING_ENABLED else ForecastMode.INVENTORY
)

# Initialize file handler
file_handler = FileHandler()

DEFAULT_SCHEMA_VERSION = "1.0.0"


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    mode: str = Form(DEFAULT_UPLOAD_MODE.value),
    schema_version: str = Form(DEFAULT_SCHEMA_VERSION),
):
    """Upload and validate CSV file"""
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

        try:
            mode_enum = ForecastMode(mode)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported mode '{mode}'.")

        # Generate file ID and save file
        file_id = str(uuid4())
        destination = UPLOAD_DIR / f"{file_id}.csv"

        # Save uploaded file
        content = await file.read()
        with open(destination, "wb") as f:
            f.write(content)
        
        # Validate CSV file
        validation_result = file_handler.validate_csv_file(destination, mode_enum)

        if not validation_result["valid"]:
            # Remove invalid file
            destination.unlink()
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "Invalid CSV file",
                    "errors": validation_result["errors"],
                    "warnings": validation_result["warnings"]
                }
            )
        
        mapping = ColumnMapping(**validation_result.get("mapping", {}))
        summary_dict = validation_result.get("summary") or {}
        anomalies = [
            ValidationAnomaly(**anomaly) for anomaly in summary_dict.get("anomalies", [])
        ]
        validation_summary = ValidationSummary(
            rows=summary_dict.get("rows", validation_result.get("info", {}).get("rows", 0)),
            columns=summary_dict.get("columns", validation_result.get("info", {}).get("columns", [])),
            detected_frequency=summary_dict.get("detected_frequency"),
            date_coverage_pct=summary_dict.get("date_coverage_pct"),
            missing_by_field=summary_dict.get("missing_by_field", {}),
            anomalies=anomalies,
        )

        file_handler.save_upload_metadata(
            file_id=file_id,
            filename=file.filename,
            mode=mode_enum,
            schema_version=schema_version,
            mapping=mapping,
            validation=validation_summary,
            raw_validation=validation_result,
        )

        logger.info("File uploaded successfully: %s", file_id)

        return {
            "fileId": file_id,
            "filename": file.filename,
            "mode": mode_enum.value,
            "schema_version": schema_version,
            "validation": validation_result,
            "mapping": mapping.dict(),
            "summary": validation_summary.dict(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/upload/{file_id}/validate")
async def validate_uploaded_file(file_id: str):
    """Get validation details for uploaded file"""
    try:
        if not file_handler.file_exists(file_id):
            raise HTTPException(status_code=404, detail="File not found")
        
        metadata = file_handler.get_upload_metadata(file_id)
        if metadata:
            return {
                "fileId": metadata.get("fileId"),
                "filename": metadata.get("filename"),
                "mode": metadata.get("mode"),
                "schema_version": metadata.get("schema_version"),
                "uploaded_at": metadata.get("uploaded_at"),
                "mapping": metadata.get("mapping"),
                "summary": metadata.get("validation_summary"),
                "validation": metadata.get("validation_raw"),
            }

        file_path = file_handler.get_file_path(file_id)
        validation_result = file_handler.validate_csv_file(file_path, ForecastMode.INVENTORY)

        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
