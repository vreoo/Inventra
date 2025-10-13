import logging
import sys
import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import upload, forecast, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def resolve_allowed_origins(raw_value: str | None) -> List[str]:
    """Derive the list of allowed origins from ALLOWED_ORIGINS env."""
    if not raw_value:
        return DEFAULT_ALLOWED_ORIGINS

    candidates = []
    for chunk in raw_value.replace("\n", ",").split(","):
        entry = chunk.strip()
        if entry:
            candidates.append(entry.rstrip("/"))

    return candidates or DEFAULT_ALLOWED_ORIGINS


app = FastAPI(
    title="Inventra API",
    description="Inventory Prediction System API",
    version="1.0.0"
)

allowed_origins = resolve_allowed_origins(os.getenv("ALLOWED_ORIGINS"))
allowed_origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX")

cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

if allowed_origin_regex:
    cors_kwargs["allow_origin_regex"] = allowed_origin_regex
    cors_kwargs["allow_origins"] = []
else:
    cors_kwargs["allow_origins"] = allowed_origins

logger.info("Configuring CORS")
logger.info(" - allow_origins=%s", cors_kwargs.get("allow_origins"))
logger.info(" - allow_origin_regex=%s", cors_kwargs.get("allow_origin_regex"))

app.add_middleware(CORSMiddleware, **cors_kwargs)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(forecast.router, prefix="/api", tags=["forecast"])
app.include_router(config.router, prefix="/api", tags=["config"])

@app.get("/")
async def root():
    return {"message": "Inventra API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2025-01-08T15:35:00Z"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
