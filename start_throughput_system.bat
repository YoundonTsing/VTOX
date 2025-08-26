@echo off
chcp 65001 >nul
echo.
echo [信息] 吞吐量配置系统启动脚本
echo =======================================
echo.

echo [步骤1] 检查Redis服务状态...
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Redis服务未启动，请先启动Redis
    echo [提示] 运行: redis-server
    pause
    exit /b 1
)
echo [成功] Redis服务正常运行

echo.
echo [步骤2] 启动后端服务...
echo [信息] 后端将运行在 http://localhost:8000
echo [信息] API文档地址: http://localhost:8000/docs

cd /d "%~dp0\backend"
start "后端服务" cmd /k "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [成功] 后端服务启动中...
echo.

echo [步骤3] 等待后端服务就绪...
timeout /t 5 /nobreak >nul

echo [步骤4] 测试API接口...
cd /d "%~dp0"
python test_api_quick.py

echo.
echo [步骤5] 启动前端服务...
echo [信息] 前端将运行在 http://localhost:3000
echo [信息] 吞吐量配置页面: http://localhost:3000/config/throughput

cd /d "%~dp0\frontend"
start "前端服务" cmd /k "npm run dev"

echo [成功] 前端服务启动中...
echo.

echo [完成] 系统启动完成！
echo.
echo [访问地址]:
echo   - 前端主页: http://localhost:3000
echo   - 集群状态监控: http://localhost:3000/monitor/cluster-status  
echo   - 吞吐量配置: http://localhost:3000/config/throughput
echo   - 后端API文档: http://localhost:8000/docs
echo.
echo [使用说明]:
echo   1. 访问吞吐量配置页面调整参数
echo   2. 使用配置预设快速应用最佳配置
echo   3. 观察集群状态监控页面的吞吐量变化
echo   4. 手动刷新数据或启用自动刷新
echo.
echo [配置建议]:
echo   - 生产环境: 使用"稳定模式"预设
echo   - 测试环境: 使用"响应模式"预设  
echo   - 高负载场景: 使用"性能模式"预设
echo.

pause