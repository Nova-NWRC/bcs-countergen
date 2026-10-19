@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"

rem ============================================================
rem   一步推送到 GitHub：Nova-NWRC/bcs-countergen
rem   首次运行会弹浏览器让你登录/授权 GitHub（之后会记住凭据）
rem ============================================================

set "GIT=C:\Program Files\Git\cmd\git.exe"
if not exist "%GIT%" set "GIT=git"

echo 仓库：%CD%
"%GIT%" remote -v
echo.
echo 正在推送 main 分支 ...
echo  （若弹出 GitHub 登录窗口，请选浏览器登录并点 Authorize）
echo.

"%GIT%" push -u origin main

echo.
if errorlevel 1 (
    echo [推送失败] 常见原因：
    echo   1) GitHub 上还没建仓库  -^> 去 github.com 新建 bcs-countergen
    echo   2) 建仓库时勾了 README/.gitignore -^> 删掉那个仓库重建空仓库
    echo   3) 登录窗口被关掉了 -^> 重跑本脚本
) else (
    echo [成功] 已推送到 https://github.com/Nova-NWRC/bcs-countergen
)
pause
endlocal