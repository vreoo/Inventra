from fastapi import APIRouter, UploadFile, File, HTTPException
from uuid import uuid4
from pathlib import Path
import logging

from services.file_handler import FileHandler

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize file handler
file_handler = FileHandler()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and validate CSV file"""
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
        
        # Generate file ID and save file
        file_id = str(uuid4())
        destination = UPLOAD_DIR / f"{file_id}.csv"
        
        # Save uploaded file
        content = await file.read()
        with open(destination, "wb") as f:
            f.write(content)
        
        # Validate CSV file
        validation_result = file_handler.validate_csv_file(destination)
        
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
        
        logger.info(f"File uploaded successfully: {file_id}")
        
        return {
            "fileId": file_id,
            "filename": file.filename,
            "validation": validation_result
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
        
        file_path = file_handler.get_file_path(file_id)
        validation_result = file_handler.validate_csv_file(file_path)
        
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
