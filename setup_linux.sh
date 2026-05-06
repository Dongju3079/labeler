#!/bin/bash
# BoltLabeler Linux 환경 자동 설치 스크립트
# Ubuntu 22.04 / Debian 12 기준

set -e

echo "=========================================="
echo " BoltLabeler Linux 환경 구축"
echo "=========================================="

# 1. Python 3.11 + Tkinter
echo ""
echo "[1/5] Python 3.11 + Tkinter 설치..."
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-tk

# 2. SAM 가중치 다운로드 (358MB)
echo ""
echo "[2/5] SAM 가중치 다운로드..."
if [ ! -f "sam_vit_b_01ec64.pth" ]; then
    wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
else
    echo "이미 존재함 - skip"
fi

# 3. 가상환경 생성
echo ""
echo "[3/5] Python 가상환경 생성 (venv/)..."
python3.11 -m venv venv
source venv/bin/activate

# 4. PyTorch (CUDA 12.4) 설치
echo ""
echo "[4/5] PyTorch + CUDA 12.4 설치..."
echo "(GPU 없으면 CPU 버전으로 진행됩니다)"
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU 감지됨 - CUDA 빌드 설치"
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
else
    echo "GPU 없음 - CPU 빌드 설치"
    pip install torch torchvision
fi

# 5. 나머지 의존성
echo ""
echo "[5/5] 라벨링 의존성 설치..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo " 설치 완료"
echo "=========================================="
echo ""
echo "실행 방법:"
echo "  source venv/bin/activate"
echo "  python label_app.py"
echo ""
echo "RealSense 카메라 사용 시:"
echo "  https://github.com/IntelRealSense/librealsense 의 설치 가이드 참조"
echo ""
