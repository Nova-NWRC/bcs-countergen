@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"

rem ============================================================
rem   BCS 算子生成器 启动器：优先 exe，其次源码模式
rem ============================================================

if exist "dist\BCS算子生成器.exe" (
    start "" "dist\BCS算子生成器.exe"
    exit /b 0
)

set "PY="
if exist "C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PY=C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( where py >nul 2>nul && set "PY=py" )

if not defined PY (
    echo [错误] 找不到 Python，也没有打包好的 exe。
    echo         请先运行 构建EXE.bat，或把 dist\BCS算子生成器.exe 放回来。
    pause
    exit /b 1
)

echo 正在启动图形界面 ...
"%PY%" bcs_gui.py
if errorlevel 1 pause
endlocal