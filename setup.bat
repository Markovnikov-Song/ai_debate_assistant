@echo off
chcp 65001 >nul
echo ========================================
echo   多AI辩论决策助手 - 一键环境配置
echo ========================================
echo.

:: 检查 conda 是否可用
conda --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Anaconda/Miniconda
    echo 下载地址：https://www.anaconda.com/download
    pause
    exit /b 1
)

echo [1/3] 检测到 Conda：
conda --version
echo.

:: 创建 conda 环境（Python 3.10）
echo [2/3] 创建 conda 环境 debate-env ...
conda create -n debate-env python=3.10 -y
echo.

:: 激活环境并安装依赖
echo [3/3] 安装依赖包...
call conda activate debate-env
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.

:: 生成 .env 文件
if not exist .env (
    copy .env.example .env >nul
    echo [提示] 已生成 .env 文件，请用记事本打开填入你的 API Key
    echo        文件位置：%cd%\.env
    echo.
)

echo ========================================
echo   安装完成！
echo   运行程序请双击 start.bat
echo ========================================
pause
