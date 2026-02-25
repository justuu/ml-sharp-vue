import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import torch
from PIL import Image
import config


class MLSharpService:
    """Service for handling ml-sharp model operations."""
    
    def __init__(self):
        self.model_path = config.MODEL_CHECKPOINT_PATH
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._ensure_sharp_installed()
        self._ensure_model_downloaded()
    
    def _ensure_sharp_installed(self):
        """Ensure ml-sharp is installed."""
        try:
            import sharp
        except ImportError:
            print("Installing ml-sharp...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "git+https://ghfast.top/https://github.com/apple/ml-sharp.git"
            ])
    
    def _ensure_model_downloaded(self):
        """Download model checkpoint if not exists."""
        if self.model_path.exists():
            print(f"Model already exists at: {self.model_path}")
            return
        
        print(f"Downloading model to: {self.model_path}")
        try:
            # Try downloading from Apple's CDN
            import urllib.request
            urllib.request.urlretrieve(
                config.MODEL_CHECKPOINT_URL,
                self.model_path
            )
            print("Model downloaded successfully!")
        except Exception as e:
            print(f"Error downloading model: {e}")
            raise RuntimeError(
                f"Failed to download model from {config.MODEL_CHECKPOINT_URL}. "
                "Please download manually and place it in the models/ directory."
            )
    
    def generate_ply(self, image_path: Path, output_path: Path) -> Path:
        """
        Generate PLY file from input image using ml-sharp.
        
        Args:
            image_path: Path to input image
            output_path: Path where PLY file should be saved
            
        Returns:
            Path to generated PLY file
        """
        import tempfile
        import shutil
        
        try:
            # Create a temporary directory for this single image
            # This prevents sharp from processing all images in uploads/
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                temp_input_dir = temp_path / "input"
                temp_output_dir = temp_path / "output"
                temp_input_dir.mkdir()
                temp_output_dir.mkdir()
                
                # Copy only the target image to temp input
                temp_image = temp_input_dir / image_path.name
                shutil.copy2(image_path, temp_image)
                
                # Run sharp predict command on temp directory
                cmd = [
                    "sharp", "predict",
                    "-i", str(temp_input_dir),
                    "-o", str(temp_output_dir),
                    "-c", str(self.model_path)
                ]
                
                print(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                print(f"Sharp output: {result.stdout}")
                if result.stderr:
                    print(f"Sharp stderr: {result.stderr}")
                
                # The output PLY file will have the same name as input image
                expected_ply = temp_output_dir / f"{image_path.stem}.ply"
                
                if not expected_ply.exists():
                    raise FileNotFoundError(f"Expected PLY file not found: {expected_ply}")
                
                # Copy the generated PLY to the final output location
                shutil.copy2(expected_ply, output_path)
            
            # Sanitize the PLY to ensure compatibility with gsplat (fix 'uint' type)
            self._sanitize_ply(output_path)
            
            return output_path
            
        except subprocess.CalledProcessError as e:
            print(f"Error running sharp: {e.stderr}")
            raise RuntimeError(f"Failed to generate PLY: {e.stderr}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise

    def _sanitize_ply(self, ply_path: Path):
        """
        Sanitize PLY file header to ensure compatibility with gsplat.
        Replaces unsupported 'uint' type with 'int' (both are 4 bytes).
        """
        import shutil
        try:
            temp_path = ply_path.with_suffix(".ply.tmp")
            
            with open(ply_path, 'rb') as f_in, open(temp_path, 'wb') as f_out:
                # Read header
                header_lines = []
                while True:
                    line = f_in.readline()
                    header_lines.append(line)
                    if line.strip() == b"end_header":
                        break
                    if len(header_lines) > 1000: # Safety break
                        print("Warning: PLY header too long, skipping sanitization")
                        # Write what we read so far and copy rest
                        for h in header_lines: f_out.write(h)
                        shutil.copyfileobj(f_in, f_out)
                        return

                # Process header
                new_header = []
                for line in header_lines:
                    try:
                        line_str = line.decode('utf-8')
                        if line_str.strip().startswith('property uint '):
                            line_str = line_str.replace('property uint ', 'property int ')
                        new_header.append(line_str.encode('utf-8'))
                    except:
                        new_header.append(line)

                # Write new header
                for line in new_header:
                    f_out.write(line)
                
                # Copy the rest of the file
                shutil.copyfileobj(f_in, f_out)
            
            # Replace original file
            os.replace(temp_path, ply_path)
            print(f"Sanitized PLY file: {ply_path}")
            
        except Exception as e:
            print(f"Error sanitizing PLY: {e}")
            # Try cleanup
            if temp_path.exists():
                try: os.remove(temp_path)
                except: pass


# Global service instance
_service: Optional[MLSharpService] = None


def get_service() -> MLSharpService:
    """Get or create the global MLSharpService instance."""
    global _service
    if _service is None:
        _service = MLSharpService()
    return _service
