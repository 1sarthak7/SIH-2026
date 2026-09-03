"""
Core configuration module.
Loads settings from environment variables with sensible defaults.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Chandrayaan-2 Image Correspondence API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # File storage
    UPLOAD_DIR: Path = Path("uploads")
    RESULTS_DIR: Path = Path("results")
    MAX_UPLOAD_SIZE_MB: int = 500  # Chandrayaan images can be large

    # ML Model
    DEVICE: str = "cuda"  # "cuda" for T4 GPU, "cpu" for fallback
    LOFTR_PRETRAINED: str = "outdoor"  # Kornia LoFTR pretrained weights
    LOFTR_CONFIDENCE_THRESHOLD: float = 0.7
    MATCH_BATCH_SIZE: int = 4

    # Preprocessing
    PATCH_SIZE: int = 512
    PATCH_OVERLAP: int = 64
    CLAHE_CLIP_LIMIT: float = 3.0
    CLAHE_TILE_GRID: int = 8
    PCA_N_COMPONENTS: int = 3

    # Verification
    RANSAC_REPROJ_THRESHOLD: float = 3.0
    RANSAC_CONFIDENCE: float = 0.9999
    RANSAC_MAX_ITERS: int = 10000

    # Redis (for Celery task queue)
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
