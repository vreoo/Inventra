from fastapi import APIRouter, UploadFile, File, HTTPException
from uuid import uuid4
from pathlib import Path

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    file_id = str(uuid4())
    destination = UPLOAD_DIR / f"{file_id}.csv"

    with open(destination, "wb") as f:
        f.write(await file.read())

    return {"fileId": file_id}
