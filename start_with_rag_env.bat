@echo off
REM vtox项目使用外部RAG环境启动脚本

echo 🚀 使用外部RAG环境启动vtox项目
echo =====================================

echo 选择启动模式:
echo 1. 主应用+RAG集成 (推荐)
echo 2. 独立RAG服务
echo 3. 退出

choice /c 123 /m "请选择"

if errorlevel 3 goto :exit
if errorlevel 2 goto :isolated_rag
if errorlevel 1 goto :main_app

goto :exit

:main_app
REM 设置环境变量
set EXTERNAL_RAG_ENV=C:\Projects\RAG_Anything\rag_env
set RAG_ANYTHING_PATH=C:\Projects\RAG_Anything
set USE_EXTERNAL_RAG=true
set ISOLATED_RAG_ENV=true

REM 检查外部环境是否存在
if not exist "%EXTERNAL_RAG_ENV%" (
    echo ❌ 外部RAG环境不存在: %EXTERNAL_RAG_ENV%
    echo 请确保RAG-Anything项目已正确安装
    pause
    exit /b 1
)

REM 检查RAG-Anything项目是否存在
if not exist "%RAG_ANYTHING_PATH%" (
    echo ❌ RAG-Anything项目不存在: %RAG_ANYTHING_PATH%
    pause
    exit /b 1
)

echo ✅ 外部RAG环境: %EXTERNAL_RAG_ENV%
echo ✅ RAG-Anything项目: %RAG_ANYTHING_PATH%

echo.
echo 🔄 设置PYTHONPATH...
set PYTHONPATH=%RAG_ANYTHING_PATH%;%PYTHONPATH%

echo.
echo 🌐 启动主应用服务 (端口8000)...
cd /d "%~dp0backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

goto :exit

:isolated_rag
REM 启动独立RAG服务
echo 🌐 启动独立RAG服务 (端口8001)...
cd /d "%~dp0"
python start_rag_service.py

goto :exit

:exit
echo.
echo 👋 服务已停止
pause