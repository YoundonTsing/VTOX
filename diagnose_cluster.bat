@echo off
REM VTOX 集群健康诊断脚本
REM 使用方法: diagnose_cluster.bat

echo.
echo 🏥 VTOX 集群健康诊断
echo ============================================================

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python未安装或不在PATH中
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

echo.
echo 🔍 开始集群健康诊断...
echo.

REM 运行诊断脚本
python diagnose_cluster_health.py

echo.
echo ============================================================
echo 🏁 诊断完成
echo.
echo 💡 如需进一步帮助，请根据上述建议进行修复
echo.
pause