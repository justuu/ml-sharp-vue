import os
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).parent

# Upload and output directories
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
MODEL_DIR = BASE_DIR / "models"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

# HuggingFace mirror configuration
HF_ENDPOINT = "https://hf-mirror.com"
os.environ["HF_ENDPOINT"] = HF_ENDPOINT

# Model configuration
MODEL_CHECKPOINT_URL = "https://ml-site.cdn-apple.com/models/sharp/sharp_2572gikvuh.pt"
MODEL_CHECKPOINT_NAME = "sharp_2572gikvuh.pt"
MODEL_CHECKPOINT_PATH = MODEL_DIR / MODEL_CHECKPOINT_NAME

# CORS settings
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite default dev server
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# File upload settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
