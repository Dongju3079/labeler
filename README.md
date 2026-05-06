# BoltLabeler

산업용 볼트 라벨링 / 학습 / 감지 GUI 프로그램.
SAM 자동 라벨링 + YOLO 세그멘테이션 학습 + RealSense 실시간 감지를 한 화면에서 처리합니다.

## 주요 기능

- **사진 만들기** — 영상에서 프레임 캡처 → 검수 / 삭제
- **라벨링하기** — SAM 자동 라벨링 → 검수 (자동 / 수동 폴리곤, 삭제, 초기화) → YOLOv8-seg 학습
- **모델 테스트** — 학습된 `best.pt` 로 RealSense 카메라 실시간 감지

## 시스템 요구사항

- Python 3.11
- NVIDIA GPU + CUDA 12.4 권장 (없으면 CPU로 동작, 매우 느림)
- RAM 8GB 이상
- 디스크 여유공간 10GB+
- (선택) Intel RealSense D435i — 모델 테스트 기능용

## Linux 설치 (Ubuntu / Debian)

### 자동 설치

```bash
git clone https://github.com/Dongju3079/labeler.git
cd labeler
chmod +x setup_linux.sh
./setup_linux.sh
```

스크립트가 자동으로 처리하는 것:
1. `python3.11`, `python3-tk` apt 설치
2. SAM 가중치 (`sam_vit_b_01ec64.pth`, 358MB) 다운로드
3. Python 가상환경 (`venv/`) 생성
4. PyTorch + CUDA 12.4 설치 (GPU 없으면 CPU)
5. `requirements.txt` 의존성 설치

### 수동 설치

```bash
# 1. Python + Tk
sudo apt install python3.11 python3.11-venv python3.11-dev python3-tk

# 2. SAM 가중치 (라벨링에 필수)
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth

# 3. 가상환경 + PyTorch
python3.11 -m venv venv
source venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# 4. 나머지
pip install -r requirements.txt
```

### RealSense 카메라 (선택사항)

`pyrealsense2` Python 패키지는 시스템에 `librealsense2` 가 설치돼 있어야 동작합니다.

```bash
# Ubuntu 22.04 기준
sudo apt install -y software-properties-common
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE
sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main"
sudo apt install librealsense2-dkms librealsense2-utils
```

자세한 설치는 [Intel 공식 가이드](https://github.com/IntelRealSense/librealsense/blob/master/doc/distribution_linux.md) 참조.

## 실행

```bash
source venv/bin/activate
python label_app.py
```

처음 실행하면 **작업 폴더 선택** 다이얼로그가 뜹니다.
선택한 폴더에 `photos/`, `models/` 가 자동 생성되며, 다음 실행부터는 자동으로 기억됩니다.

## 사용 흐름

```
[사진 만들기]
  영상 파일 입력 → 프레임 캡처 → photos/ 에 저장
        ↓
[라벨링하기]
  photos/ 의 이미지에 SAM 자동 라벨링 → 검수 → YOLO-seg 학습
        ↓
  models/ 에 best.pt 저장
        ↓
[모델 테스트]
  best.pt + RealSense → 실시간 볼트 감지
```

## 모델 정보

| 모델 | 용도 | 다운로드 |
|------|------|---------|
| `sam_vit_b_01ec64.pth` | SAM 자동 라벨링 (358MB) | [Meta 공식](https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth) |
| `yolov8n-seg.pt` | YOLO 베이스 (학습 시작점) | `ultralytics` 가 자동 다운로드 |
| `best.pt` | 사용자 학습 결과물 | 직접 학습 (라벨링하기 → 학습 버튼) |

## Windows 사용자

Windows 에서 사용하려면:

- **소스 실행** — 위 Linux 가이드의 의존성을 Windows Python 3.11 에 동일하게 설치
- **PyInstaller 빌드** — `pip install pyinstaller && pyinstaller BoltLabeler.spec` (spec 파일은 별도 요청)

## 라이선스

MIT License — `LICENSE` 파일 참조.
