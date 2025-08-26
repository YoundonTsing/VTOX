@echo off
chcp 65001 >nul
echo.
echo [信息] VTOX 分布式集群启动脚本
echo [信息] 集群模式已集成到 main.py，无需单独启动
echo ================================================================
echo.

echo [步骤1] 检查 Redis 服务状态...
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Redis 服务未启动，请先启动 Redis
    echo [建议] 运行: redis-server
    pause
    exit /b 1
)
echo [成功] Redis 服务正常

echo.
echo [步骤2] 清理旧数据（可选）...
set /p clear_data="是否清理 Redis Stream 积压数据？(y/N): "
if /i "%clear_data%"=="y" (
    echo [信息] 正在清理积压数据...
    python clear_redis_streams.py --action clear-all --force
    echo [完成] 数据清理完成
)

echo.
echo [步骤3] 启动 VTOX 分布式集群...
echo [信息] 使用集群模式启动 FastAPI 应用
echo [信息] 这将自动启动：
echo         - FastAPI 主服务 (端口 8000)
echo         - 分布式协调器 (端口 8001) 
echo         - 3个 Worker 节点 (端口 8002-8004)
echo         - Redis Stream 桥接器
echo         - 自动数据刷新服务
echo.

cd /d "%~dp0backend"
echo [启动] python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

echo.
echo [信息] 集群服务已停止
pause