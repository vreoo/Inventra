import logging
import sys
import os
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def load_environment() -> List[str]:
    """Populate os.environ from .env-style files if present."""
    candidates = [".env", ".env.local"]
    loaded_files: List[str] = []
    for filename in candidates:
        env_path = Path(filename)
        if not env_path.exists():
            continue
        try:
            for raw_line in env_path.read_text().splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if not key or key in os.environ:
                    continue
                normalized = value.strip().strip('"').strip("'")
                os.environ[key] = normalized
            loaded_files.append(str(env_path.resolve()))
        except Exception as exc:  # pragma: no cover - defensive logging only
            logging.getLogger(__name__).warning(
                "Unable to load environment file %s: %s", env_path, exc
            )
    return loaded_files


LOADED_ENV_FILES = load_environment()

from api import upload, forecast, config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)

if LOADED_ENV_FILES:
    logger.info("Loaded environment file(s): %s", ", ".join(LOADED_ENV_FILES))
else:
    logger.info("No environment file found; relying on process environment variables")

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

AI_SUMMARY_ENABLED = os.getenv("ENABLE_AI_SUMMARY", "false").lower() == "true"
AI_SUMMARY_MODEL = os.getenv("AI_SUMMARY_MODEL", "HuggingFaceH4/zephyr-7b-beta")
HF_API_TOKEN_PRESENT = bool(os.getenv("HF_API_TOKEN"))


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

@app.get("/api/ai/status")
async def ai_status():
    enabled = AI_SUMMARY_ENABLED and HF_API_TOKEN_PRESENT
    return {"enabled": enabled, "model": AI_SUMMARY_MODEL if enabled else None}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2025-01-08T15:35:00Z"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
