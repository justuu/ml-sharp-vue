from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import uuid
import shutil
from typing import Dict
import config
from ml_sharp_service import get_service

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


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "ML-Sharp API is running"}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image and generate PLY file.
    
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
    
    # Generate PLY file
    output_filename = f"{task_id}.ply"
    output_path = config.OUTPUT_DIR / output_filename
    
    try:
        service = get_service()
        service.generate_ply(upload_path, output_path)
        
        tasks[task_id] = {
            "status": "completed",
            "ply_filename": output_filename,
            "input_image": str(upload_path)
        }
        
        return JSONResponse({
            "task_id": task_id,
            "ply_filename": output_filename,
            "status": "completed"
        })
        
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "error": str(e)
        }
        raise HTTPException(status_code=500, detail=f"Failed to generate PLY: {str(e)}")


@app.get("/api/ply/{filename}")
async def get_ply_file(filename: str):
    """Serve generated PLY file."""
    file_path = config.OUTPUT_DIR / filename
    
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
