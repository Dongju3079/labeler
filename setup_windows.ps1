# BoltLabeler Windows 환경 자동 설치 스크립트
# Windows 10/11 + Python 3.11 기준
#
# 실행 방법 (PowerShell 관리자 권한 권장):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\setup_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " BoltLabeler Windows 환경 구축" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Python 3.11 확인
Write-Host ""
Write-Host "[1/5] Python 3.11 확인..."
$python = $null
foreach ($cmd in @("py -3.11", "python3.11", "python")) {
    try {
        $ver = & cmd /c "$cmd --version 2>&1"
        if ($ver -match "3\.11") {
            $python = $cmd
            Write-Host "  발견: $cmd ($ver)" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $python) {
    Write-Host "  Python 3.11이 없습니다." -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/release/python-3119/ 에서 설치 후 다시 실행하세요."
    Write-Host "  설치 시 'Add python.exe to PATH' 체크 권장."
    exit 1
}

# 2. SAM 가중치 다운로드 (358MB)
Write-Host ""
Write-Host "[2/5] SAM 가중치 다운로드..."
$samPath = Join-Path $PSScriptRoot "sam_vit_b_01ec64.pth"
if (Test-Path $samPath) {
    $sizeMB = [math]::Round((Get-Item $samPath).Length / 1MB, 1)
    if ($sizeMB -gt 350) {
        Write-Host "  이미 존재함 ($sizeMB MB) - skip" -ForegroundColor Green
    } else {
        Write-Host "  파일이 손상된 것 같음 - 재다운로드"
        Remove-Item $samPath -Force
    }
}
if (-not (Test-Path $samPath)) {
    $url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
    Write-Host "  다운로드 중... ($url)"
    Invoke-WebRequest -Uri $url -OutFile $samPath -UseBasicParsing
    Write-Host "  완료" -ForegroundColor Green
}

# 3. 가상환경 생성
Write-Host ""
Write-Host "[3/5] Python 가상환경 생성 (venv\)..."
$venvPath = Join-Path $PSScriptRoot "venv"
if (-not (Test-Path $venvPath)) {
    Invoke-Expression "$python -m venv `"$venvPath`""
    Write-Host "  생성 완료" -ForegroundColor Green
} else {
    Write-Host "  이미 존재함 - skip" -ForegroundColor Green
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

# pip 업그레이드
& $venvPython -m pip install --upgrade pip --quiet

# 4. PyTorch 설치 (GPU 감지 → 적절한 CUDA 빌드)
Write-Host ""
Write-Host "[4/5] PyTorch 설치..."
$gpuCC = $null
try {
    $gpuOut = & nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>&1
    if ($LASTEXITCODE -eq 0) {
        $gpuCC = ($gpuOut -split "`n")[0].Trim() -replace '\.', ''
        Write-Host "  감지된 GPU compute capability: $gpuCC" -ForegroundColor Green
    }
} catch {}

if ($gpuCC) {
    if ([int]$gpuCC -ge 120) {
        Write-Host "  → Blackwell 이상 (RTX 50xx 등): CUDA 12.8 빌드 설치"
        & $venvPip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
    } else {
        Write-Host "  → Ampere/Ada/Hopper: CUDA 12.4 빌드 설치"
        & $venvPip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
    }
} else {
    Write-Host "  NVIDIA GPU 미감지 - CPU 빌드 설치"
    & $venvPip install torch torchvision
}

# 5. 나머지 의존성
Write-Host ""
Write-Host "[5/5] 라벨링 의존성 설치..."
& $venvPip install -r (Join-Path $PSScriptRoot "requirements.txt")

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " 설치 완료" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "실행 방법:"
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "  python label_app.py"
Write-Host ""
Write-Host "또는 한 줄로:"
Write-Host "  .\venv\Scripts\python.exe label_app.py"
Write-Host ""
Write-Host "RealSense 카메라 사용 시:"
Write-Host "  Intel RealSense SDK 2.0 설치 필요"
Write-Host "  https://github.com/IntelRealSense/librealsense/releases"
Write-Host ""
