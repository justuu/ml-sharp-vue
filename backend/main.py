from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import uuid
import hashlib
import time
import shutil
from typing import Dict
from pydantic import BaseModel
from PIL import Image
import config
from ml_sharp_service import get_service
from oss_service import OSSService

app = FastAPI(title="ML-Sharp API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store processing tasks
tasks: Dict[str, dict] = {}


def _file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's content."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _cleanup_expired_cache():
    """Delete cache files older than CACHE_EXPIRY_DAYS."""
    expiry_seconds = config.CACHE_EXPIRY_DAYS * 86400
    now = time.time()
    count = 0
    for f in config.CACHE_DIR.iterdir():
        if f.is_file() and f.suffix == ".ply":
            if now - f.stat().st_mtime > expiry_seconds:
                f.unlink()
                count += 1
    if count:
        print(f"Cleaned up {count} expired PLY cache file(s)")


@app.on_event("startup")
async def startup_cleanup():
    """Clean expired PLY cache on startup."""
    _cleanup_expired_cache()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "ML-Sharp API is running"}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image and generate PLY file.
    Uses content-based caching: same image returns cached PLY (valid for 7 days).
    
    Returns:
        JSON with task_id and ply_filename
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = config.UPLOAD_DIR / f"{task_id}{file_ext}"
    try:
        with upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Get image dimensions
    try:
        with Image.open(upload_path) as img:
            img_width, img_height = img.size
    except Exception:
        img_width, img_height = None, None
    
    # Compute image hash for cache lookup
    image_hash = _file_hash(upload_path)
    ply_filename = f"{image_hash}.ply"
    cache_path = config.CACHE_DIR / ply_filename
    
    # Check cache: if cached PLY exists and not expired, use it directly
    expiry_seconds = config.CACHE_EXPIRY_DAYS * 86400
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < expiry_seconds:
            print(f"Cache hit for image hash {image_hash[:12]}... (age: {age/3600:.1f}h)")
            
            tasks[task_id] = {
                "status": "completed",
                "ply_filename": ply_filename,
                "input_image": str(upload_path),
                "image_width": img_width,
                "image_height": img_height,
                "cached": True
            }
            
            return JSONResponse({
                "task_id": task_id,
                "ply_filename": ply_filename,
                "status": "completed",
                "image_width": img_width,
                "image_height": img_height,
                "cached": True
            })
        else:
            # Expired, delete stale cache
            cache_path.unlink()
            print(f"Cache expired for image hash {image_hash[:12]}..., regenerating")
    
    # Generate PLY file directly to cache
    try:
        service = get_service()
        service.generate_ply(upload_path, cache_path)
        
        print(f"Generated and cached PLY for image hash {image_hash[:12]}...")
        
        tasks[task_id] = {
            "status": "completed",
            "ply_filename": ply_filename,
            "input_image": str(upload_path),
            "image_width": img_width,
            "image_height": img_height
        }
        
        return JSONResponse({
            "task_id": task_id,
            "ply_filename": ply_filename,
            "status": "completed",
            "image_width": img_width,
            "image_height": img_height
        })
        
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "error": str(e)
        }
        raise HTTPException(status_code=500, detail=f"Failed to generate PLY: {str(e)}")


class OSSUrlRequest(BaseModel):
    url: str

@app.post("/api/generate_from_oss_url")
async def generate_from_oss_url(request: OSSUrlRequest):
    """
    Generate PLY file from an Aliyun OSS image URL.
    Downloads the image locally, then uses the same content-based caching logic.
    """
    oss_url = request.url
    if not oss_url:
        raise HTTPException(status_code=400, detail="URL is required")

    task_id = str(uuid.uuid4())
    
    # Initialize OSS service
    oss_svc = OSSService(config.OSS_CONFIG)
    
    # Download file to temp dir
    local_path_str = oss_svc.download_file(oss_url, str(config.OSS_TEMP_DIR))
    if not local_path_str:
        raise HTTPException(status_code=400, detail="Failed to download file from OSS URL")
        
    upload_path = Path(local_path_str)
    
    # Validate file extension
    file_ext = upload_path.suffix.lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type {file_ext}. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
        )
        
    # Get image dimensions
    try:
        with Image.open(upload_path) as img:
            img_width, img_height = img.size
    except Exception:
        img_width, img_height = None, None
        
    # Compute image hash for cache lookup
    image_hash = _file_hash(upload_path)
    ply_filename = f"{image_hash}.ply"
    cache_path = config.CACHE_DIR / ply_filename
    
    # Check cache: if cached PLY exists and not expired, use it directly
    expiry_seconds = config.CACHE_EXPIRY_DAYS * 86400
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < expiry_seconds:
            print(f"Cache hit for image hash {image_hash[:12]}... (age: {age/3600:.1f}h)")
            
            tasks[task_id] = {
                "status": "completed",
                "ply_filename": ply_filename,
                "input_image": str(upload_path),
                "image_width": img_width,
                "image_height": img_height,
                "cached": True
            }
            
            return JSONResponse({
                "task_id": task_id,
                "ply_filename": ply_filename,
                "status": "completed",
                "image_width": img_width,
                "image_height": img_height,
                "cached": True
            })
        else:
            # Expired, delete stale cache
            cache_path.unlink()
            print(f"Cache expired for image hash {image_hash[:12]}..., regenerating")
            
    # Generate PLY file directly to cache
    try:
        service = get_service()
        service.generate_ply(upload_path, cache_path)
        
        print(f"Generated and cached PLY for image hash {image_hash[:12]}...")
        
        tasks[task_id] = {
            "status": "completed",
            "ply_filename": ply_filename,
            "input_image": str(upload_path),
            "image_width": img_width,
            "image_height": img_height
        }
        
        return JSONResponse({
            "task_id": task_id,
            "ply_filename": ply_filename,
            "status": "completed",
            "image_width": img_width,
            "image_height": img_height
        })
        
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "error": str(e)
        }
        raise HTTPException(status_code=500, detail=f"Failed to generate PLY: {str(e)}")


@app.get("/api/ply/{filename}")
async def get_ply_file(filename: str):
    """Serve PLY file from cache."""
    file_path = config.CACHE_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PLY file not found")
    
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=filename
    )


@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """Get processing status for a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return tasks[task_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6008)
