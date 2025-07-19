from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import upload, forecast  # already created above

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(forecast.router)
