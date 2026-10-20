@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"

rem ============================================================
rem   BCS 军队编辑器：表格批量编辑 + 一键出整套算子
rem ============================================================

if exist "dist\BCS算子生成器.exe" (
    start "" "dist\BCS算子生成器.exe" --army
    exit /b 0
)

set "PY="
if exist "C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PY=C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( where py >nul 2>nul && set "PY=py" )

if not defined PY (
    echo [错误] 找不到 Python，也没有打包好的 exe。
    pause
    exit /b 1
)

echo 正在启动军队编辑器 ...
"%PY%" bcs_army.py
if errorlevel 1 pause
endlocal
