@echo off
chcp 65001 >nul
echo ========================================
echo   多AI辩论决策助手 - 启动中...
echo ========================================
echo.

:: 激活 conda 环境
call conda activate debate-env

:: 启动应用
echo 正在启动，浏览器将自动打开...
echo 手动访问：http://localhost:8501
echo 按 Ctrl+C 可停止程序
echo.
streamlit run debate_assistant.py
pause
