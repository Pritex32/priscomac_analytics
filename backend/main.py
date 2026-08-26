from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.api.router import router as api_router
import os
from dotenv import load_dotenv

load_dotenv()


app = FastAPI(title="Priscomac Analytics", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://priscomac-analytics-frontend.vercel.app",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
