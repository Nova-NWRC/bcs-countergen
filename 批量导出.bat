@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"

rem ============================================================
rem   批量导出：samples\units.json -> out\  (默认 75px, 正反两面)
rem   用法: 批量导出.bat [spec.json] [size]
rem ============================================================

set "PY="
if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PY=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( where py >nul 2>nul && set "PY=py" )

set "SPEC=%~1"
if "%SPEC%"=="" set "SPEC=samples\units.json"
set "SIZE=%~2"
if "%SIZE%"=="" set "SIZE=75"

echo 输入: %SPEC%
echo 尺寸: %SIZE% px   输出: out\
echo.

if exist "dist\BCS算子生成器.exe" (
    "dist\BCS算子生成器.exe" --cli --spec "%SPEC%" --out out --size %SIZE% --pair
) else (
    if not defined PY (
        echo [错误] 找不到 Python 或已打包的 exe。
        pause
        exit /b 1
    )
    "%PY%" bcs_cli.py --spec "%SPEC%" --out out --size %SIZE% --pair
)

echo.
echo 完成, 文件在 out\ 目录。
pause
endlocal