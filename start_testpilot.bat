@echo off
chcp 65001 >nul
cd /d "%~dp0"

python -c "import flask, dotenv, requests" >nul 2>&1
if errorlevel 1 (
  echo 正在安装 TestPilot 运行依赖...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo 依赖安装失败，请检查 Python 和网络环境。
    pause
    exit /b 1
  )
)

echo TestPilot 已启动：http://127.0.0.1:5000
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 1; Start-Process 'http://127.0.0.1:5000'"
python app.py
pause
