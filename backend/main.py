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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

frontend_dist = os.getenv("FRONTEND_DIST")
if not frontend_dist:
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"),
        os.path.join(os.path.dirname(__file__), "..", "..", "https://priscomac-analytics-frontend.vercel.app/", "priscomac_analytics_frontend-main", "frontend", "dist"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            frontend_dist = candidate
            break

if frontend_dist and os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
