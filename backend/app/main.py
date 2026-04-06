"""Main FastAPI application entry point"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import redis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routers import players, predictions, live


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup: Initialize database tables
    from app.database import init_db
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"⚠ Database initialization failed (will retry on first request): {e}")

    # Startup: Initialize Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        app.state.redis = redis.StrictRedis.from_url(redis_url, decode_responses=True)
        app.state.redis.ping()
        print("✓ Redis connected")
    except Exception as e:
        print(f"⚠ Redis connection failed (will work without cache): {e}")
        app.state.redis = None

    yield

    # Shutdown: Close Redis connection
    if app.state.redis:
        app.state.redis.close()


app = FastAPI(
    title="Aaronson Oracle Baseball",
    description="Predict baseball pitches using n-gram pattern matching and other models",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(players.router, prefix="/api", tags=["players"])
app.include_router(predictions.router, prefix="/api", tags=["predictions"])
app.include_router(live.router, prefix="/api", tags=["live"])

# Check if frontend build exists
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    # Mount static files (CSS, JS, etc)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # Serve index.html for all non-API routes (SPA catch-all)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes"""
        if not full_path.startswith("api/"):
            return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/")
    async def root():
        """Health check endpoint when frontend not built"""
        return {"status": "ok", "message": "Aaronson Oracle Baseball API"}
