"""
Chandrayaan-2 Multi-Modal Image Correspondence API

Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.api.routes import upload, jobs, results


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        logger.warning("No GPU detected — falling back to CPU. Inference will be slower.")

    yield

    # Shutdown
    logger.info("Shutting down application.")


# ──────────────────────────────────────────────
# Create FastAPI App
# ──────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API for finding feature correspondences between multi-modal Chandrayaan-2 "
        "images (OHRC, TMC-2, IIRS) with scale and sun-angle invariance."
    ),
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(results.router, prefix="/api", tags=["Results"])


# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — API information."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
