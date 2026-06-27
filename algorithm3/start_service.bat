@echo off
chcp 65001 >nul
echo ========================================
echo 关联规则算法服务启动脚本
echo ========================================
echo.

echo [1] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2] 安装依赖...
pip install -r requirements.txt -q

echo.
echo [3] 启动服务...
echo    - 模式: 服务模式（持续轮询）
echo    - 轮询间隔: 10秒
echo.
python run.py --mode service --interval 10

pause