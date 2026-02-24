@echo off
echo ========================================
echo ML-Sharp Vue Backend Setup
echo ========================================
echo.

cd backend

echo Creating Conda environment...
call conda create -n ml-sharp-backend python=3.12 -y

echo.
echo Activating Conda environment...
call conda activate ml-sharp-backend

echo.
echo Installing PyTorch (CUDA 12.8)...
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu128

echo.
echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Installing ml-sharp...
pip install git+https://github.com/apple/ml-sharp.git

echo.
echo ========================================
echo Backend setup complete!
echo ========================================
echo.
echo To start the backend server:
echo   cd backend
echo   conda activate ml-sharp-backend
echo   python main.py
echo.

pause
