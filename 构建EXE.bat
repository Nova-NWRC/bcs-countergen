@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"

rem ============================================================
rem   重新打包单文件 exe -> dist\BCS算子生成器.exe
rem ============================================================

set "PY="
if exist "C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PY=C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY (
    echo [错误] 找不到 Python。
    pause
    exit /b 1
)

echo 使用 Python: %PY%
"%PY%" -c "import PIL" 2>nul || "%PY%" -m pip install pillow
"%PY%" -c "import PyInstaller" 2>nul || "%PY%" -m pip install pyinstaller

echo.
echo 正在打包 ...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name "BCS算子生成器" --add-data "%CD%\samples\units.json;samples" --distpath dist --workpath build --specpath build bcs_app.py

if errorlevel 1 (
    echo.
    echo [失败] 打包出错，请看上面的日志。
    pause
    exit /b 1
)

echo.
echo 完成: dist\BCS算子生成器.exe
pause
endlocal