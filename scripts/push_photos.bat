@echo off
REM ============================================================
REM  촬영 PC -> 공유서버 photos 업로드
REM ============================================================
REM
REM 사용 전 변경 필요:
REM   LOCAL_WS    : Windows 작업 폴더 경로
REM   SHARE_HOST  : 공유서버 IP/호스트명
REM   SHARE_PATH  : 공유 폴더 안의 본인 경로
REM   SHARE_USER  : 공유 계정
REM   (비밀번호는 Credential Manager 사용 권장 - cmdkey)
REM
REM 처음 한 번만 자격증명 등록 (PowerShell 또는 CMD에서):
REM   cmdkey /add:SHARE_HOST /user:SHARE_USER /pass:SHARE_PASSWORD
REM ============================================================

set LOCAL_WS=C:\boltwork
set SHARE_HOST=192.168.0.150
set SHARE_PATH=\\%SHARE_HOST%\share\matthew\boltwork
set SHARE_USER=und-share

REM 공유 마운트 (이미 자격증명 저장돼있으면 비번 안 물어봄)
net use \\%SHARE_HOST%\share /user:%SHARE_USER% >nul 2>&1

if not exist "%LOCAL_WS%\photos" (
    echo [ERROR] %LOCAL_WS%\photos 폴더가 없습니다.
    pause
    exit /b 1
)

echo.
echo === photos 업로드 ===
echo   원본:   %LOCAL_WS%\photos
echo   대상:   %SHARE_PATH%\photos
echo.

robocopy "%LOCAL_WS%\photos" "%SHARE_PATH%\photos" /MIR /MT:8 /R:3 /W:5 /NP

echo.
echo === 업로드 완료 ===
echo 학습서버에서 다음을 실행하세요:
echo   python ~/labeler/train_only.py /mnt/share/matthew/boltwork
echo.
pause
