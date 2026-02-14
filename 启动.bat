@echo off
chcp 65001 >nul
title 天地图综合分析工具 V1.0
color 0A

:: ===================== 配置区（根据实际情况修改） =====================
:: 程序根目录（默认自动获取bat文件所在目录，无需修改）
set "PROJECT_DIR=%~dp0"
:: Python解释器路径（如果系统已配置Python环境变量，直接用python即可；否则填完整路径）
set "PYTHON_EXE=python"
:: 可选：如果需要指定虚拟环境，取消下面注释并修改路径
:: set "PYTHON_EXE=C:\Users\Administrator\venv\tianditu\Scripts\python.exe"

:: ===================== 核心逻辑 =====================
echo ==============================================
echo          天地图综合分析工具 启动中...
echo ==============================================
echo 程序根目录：%PROJECT_DIR%
echo Python解释器：%PYTHON_EXE%
echo ==============================================

:: 切换到程序根目录
cd /d "%PROJECT_DIR%" || (
    echo [31m❌ 切换到程序目录失败！[0m
    pause
    exit /b 1
)

:: 检查Python是否可用
%PYTHON_EXE% --version >nul 2>&1 || (
    echo [31m❌ 未找到Python解释器！请检查：[0m
    echo 1. 是否已安装Python并添加到系统环境变量
    echo 2. 或修改bat文件中PYTHON_EXE为Python完整路径（如：C:\Python314\python.exe）
    pause
    exit /b 1
)

:: 检查核心文件是否存在
if not exist "gui_main.py" (
    echo [31m❌ 未找到核心文件 gui_main.py！请确认bat文件放在程序根目录[0m
    pause
    exit /b 1
)

:: 启动程序（出错时暂停，方便查看错误）
echo [32m✅ 开始启动GUI程序...[0m
%PYTHON_EXE% gui_main.py || (
    echo [31m❌ 程序启动失败！错误信息如上，请检查依赖包是否安装[0m
    echo 建议执行：pip install tkinter requests pillow sqlalchemy beautifulsoup4 chart.js（按需安装）
    pause
    exit /b 1
)

:: 程序正常退出时的提示
echo [32m✅ 程序已正常退出[0m
pause
exit /b 0@echo off
chcp 65001 >nul
title 天地图综合分析工具 V1.0
color 0A

:: ===================== 配置区（根据实际情况修改） =====================
:: 程序根目录（默认自动获取bat文件所在目录，无需修改）
set "PROJECT_DIR=%~dp0"
:: Python解释器路径（如果系统已配置Python环境变量，直接用python即可；否则填完整路径）
set "PYTHON_EXE=python"
:: 可选：如果需要指定虚拟环境，取消下面注释并修改路径
:: set "PYTHON_EXE=C:\Users\Administrator\venv\tianditu\Scripts\python.exe"

:: ===================== 核心逻辑 =====================
echo ==============================================
echo          天地图综合分析工具 启动中...
echo ==============================================
echo 程序根目录：%PROJECT_DIR%
echo Python解释器：%PYTHON_EXE%
echo ==============================================

:: 切换到程序根目录
cd /d "%PROJECT_DIR%" || (
    echo [31m❌ 切换到程序目录失败！[0m
    pause
    exit /b 1
)

:: 检查Python是否可用
%PYTHON_EXE% --version >nul 2>&1 || (
    echo [31m❌ 未找到Python解释器！请检查：[0m
    echo 1. 是否已安装Python并添加到系统环境变量
    echo 2. 或修改bat文件中PYTHON_EXE为Python完整路径（如：C:\Python314\python.exe）
    pause
    exit /b 1
)

:: 检查核心文件是否存在
if not exist "gui_main.py" (
    echo [31m❌ 未找到核心文件 gui_main.py！请确认bat文件放在程序根目录[0m
    pause
    exit /b 1
)

:: 启动程序（出错时暂停，方便查看错误）
echo [32m✅ 开始启动GUI程序...[0m
%PYTHON_EXE% gui_main.py || (
    echo [31m❌ 程序启动失败！错误信息如上，请检查依赖包是否安装[0m
    echo 建议执行：pip install tkinter requests pillow sqlalchemy beautifulsoup4 chart.js（按需安装）
    pause
    exit /b 1
)

:: 程序正常退出时的提示
echo [32m✅ 程序已正常退出[0m
pause
exit /b 0