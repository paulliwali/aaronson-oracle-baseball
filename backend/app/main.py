"""Main FastAPI application entry point"""

import os
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import players, predictions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup: Initialize Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    app.state.redis = redis.StrictRedis.from_url(redis_url, decode_responses=True)

    yield

    # Shutdown: Close Redis connection
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
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(players.router, prefix="/api", tags=["players"])
app.include_router(predictions.router, prefix="/api", tags=["predictions"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Aaronson Oracle Baseball API"}
