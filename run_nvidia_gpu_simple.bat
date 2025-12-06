@echo off
REM Start ComfyUI with NVIDIA GPU acceleration
cd /d D:\ComfyUI-master
echo Starting ComfyUI with NVIDIA GPU acceleration...

REM Check if NVIDIA GPU is available
where nvidia-smi >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Warning: NVIDIA GPU not detected
    pause
    exit /b 1
)

REM Start ComfyUI with GPU parameters
python main.py --gpu-only --cuda-device 0

if %ERRORLEVEL% neq 0 (
    echo Error: ComfyUI failed to start
    pause
    exit /b %ERRORLEVEL%
)

echo ComfyUI started successfully
pause