@echo off
REM ============================================================
REM  공유서버 -> 촬영 PC models 다운로드 (best.pt 회수)
REM ============================================================

set LOCAL_WS=C:\boltwork
set SHARE_HOST=192.168.0.150
set SHARE_PATH=\\%SHARE_HOST%\share\matthew\boltwork
set SHARE_USER=und-share

net use \\%SHARE_HOST%\share /user:%SHARE_USER% >nul 2>&1

if not exist "%SHARE_PATH%\models" (
    echo [ERROR] 공유서버에 models 폴더가 없습니다.
    echo 학습이 끝났는지 확인하세요.
    pause
    exit /b 1
)

echo.
echo === models 다운로드 ===
echo   원본:   %SHARE_PATH%\models
echo   대상:   %LOCAL_WS%\models
echo.

robocopy "%SHARE_PATH%\models" "%LOCAL_WS%\models" /MIR /MT:8 /R:3 /W:5 /NP

echo.
echo === 회수 완료 ===
echo BoltLabeler에서 [모델 테스트] 메뉴로 best.pt 선택하세요.
echo.
pause
