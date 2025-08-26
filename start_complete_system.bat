@echo off
chcp 65001 >nul
REM VTOX 完整分布式监控系统启动脚本
REM 用于故障模拟监控展示和并发量测试

echo.
echo 启动 VTOX 完整分布式监控系统
echo ============================================================

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Python未安装或不在PATH中
    pause
    exit /b 1
)

echo [成功] Python环境检查通过

REM 检查Redis服务
echo.
echo [检查] 检查Redis服务状态...
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Redis服务未启动，请先启动Redis服务
    echo 请运行: redis-server
    pause
    exit /b 1
)
echo [成功] Redis服务运行正常

echo.
echo [信息] 系统启动顺序:
echo 1. 后端FastAPI服务 (端口8000)
echo 2. 分布式诊断系统Consumer
echo 3. 多车辆数据模拟器 (并发测试)
echo 4. 前端Vue应用 (端口3000)

echo.
echo [选择] 选择运行模式:
echo [1] 基础演示模式 (5辆车)
echo [2] 并发测试模式 (20辆车)
echo [3] 高负载测试模式 (50辆车)
echo [4] 自定义配置

set /p mode="请选择模式 (1-4): "

if "%mode%"=="1" (
    set VEHICLE_COUNT=5
    set TEST_DURATION=300
    echo [模式] 基础演示模式: 5辆车，运行5分钟
) else if "%mode%"=="2" (
    set VEHICLE_COUNT=20
    set TEST_DURATION=600
    echo [模式] 并发测试模式: 20辆车，运行10分钟
) else if "%mode%"=="3" (
    set VEHICLE_COUNT=50
    set TEST_DURATION=900
    echo [模式] 高负载测试模式: 50辆车，运行15分钟
) else if "%mode%"=="4" (
    set /p VEHICLE_COUNT="请输入车辆数量: "
    set /p TEST_DURATION="请输入运行时间(秒): "
    echo [模式] 自定义模式: %VEHICLE_COUNT%辆车，运行%TEST_DURATION%秒
) else (
    echo [警告] 无效选择，使用默认配置
    set VEHICLE_COUNT=5
    set TEST_DURATION=300
)

echo.
echo [启动] 开始启动系统组件...

REM 启动后端服务 (后台运行)
echo [1/4] 启动后端FastAPI服务...
start "VTOX Backend" cmd /k "cd /d %~dp0backend && python run.py"

REM 等待后端服务启动
echo [等待] 等待后端服务启动 (10秒)...
timeout /t 10 /nobreak >nul

REM 启动分布式诊断系统
echo [2/4] 启动分布式诊断系统Consumer...
start "VTOX Consumer" cmd /k "cd /d %~dp0 && python databases/start_diagnosis_system.py"

REM 等待Consumer启动
echo [等待] 等待Consumer启动 (5秒)...
timeout /t 5 /nobreak >nul

REM 启动数据模拟器
echo [3/4] 启动多车辆数据模拟器 (%VEHICLE_COUNT%辆车)...
start "VTOX Simulator" cmd /k "cd /d %~dp0 && python databases/multi_vehicle_simulator.py --vehicles %VEHICLE_COUNT% --duration %TEST_DURATION%"

REM 等待模拟器启动
echo [等待] 等待模拟器启动 (3秒)...
timeout /t 3 /nobreak >nul

REM 启动前端服务
echo [4/4] 启动前端Vue应用...
start "VTOX Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo [完成] 所有组件启动完成！
echo.
echo [访问] 系统访问地址:
echo    前端应用: http://localhost:3000
echo    后端API: http://localhost:8000
echo    API文档: http://localhost:8000/docs
echo.
echo [监控] 监控推荐页面:
echo    1. 集群状态监控: http://localhost:3000/monitor/cluster-status
echo    2. 实时诊断页面: http://localhost:3000/diagnosis/realtime
echo    3. 车队管理页面: http://localhost:3000/vehicles/fleet
echo.
echo [命令] 性能监控命令:
echo    监控Redis Stream: python databases/redis_stream_monitor.py
echo    集群健康诊断: python diagnose_cluster_health.py
echo    实时系统状态: python verify_worker_status.py
echo.
echo [提示] 测试完成后按任意键退出...
pause >nul