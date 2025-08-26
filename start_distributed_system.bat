@echo off
chcp 65001 >nul
echo [信息] 启动VTOX分布式电机故障诊断系统
echo ================================

echo [步骤1] 检查目录结构...
if not exist "backend" (
    echo [错误] 未找到backend目录，请确保在vtox项目根目录运行此脚本
    pause
    exit /b 1
)

if not exist "cluster" (
    echo [错误] 未找到cluster目录，请确保项目结构完整
    pause
    exit /b 1
)

echo [成功] 目录结构检查通过

echo.
echo [步骤2] 检查Redis服务...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [警告] Redis服务未运行，尝试启动Redis...
    echo [提示] 请确保Redis已安装并配置到PATH环境变量
    echo [提示] 或者手动启动Redis服务
    pause
)

echo.
echo [步骤3] 进入backend目录...
cd backend

echo.
echo [步骤4] 启动VTOX分布式微服务集群...
echo [信息] 启动命令: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo [信息] 系统将自动启动:
echo   - FastAPI后端服务 (端口8000)
echo   - 分布式集群协调器 (端口8001)
echo   - 3个Worker节点 (端口8002-8004)
echo   - Redis Stream桥接器
echo   - 自动数据刷新服务
echo.
echo [提示] 启动后可访问:
echo   - API文档: http://localhost:8000/docs
echo   - 系统状态: http://localhost:8000
echo   - 集群状态: http://localhost:8000/api/v1/cluster/status
echo.
echo [提示] 按Ctrl+C停止服务
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000