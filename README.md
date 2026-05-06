# BoltLabeler

산업용 볼트 라벨링 / 학습 / 감지 GUI 프로그램.
SAM 자동 라벨링 + YOLO 세그멘테이션 학습 + RealSense 실시간 감지를 한 화면에서 처리합니다.

> **분할 워크플로우 가이드**: 촬영 PC와 학습서버를 분리해서 운영하는 방법은 [WORKFLOW.md](./WORKFLOW.md) 참조.

## 주요 기능

- **사진 만들기** — 영상에서 프레임 캡처 → 검수 / 삭제
- **라벨링하기** — SAM 자동 라벨링 → 검수 (자동 / 수동 폴리곤, 삭제, 초기화) → YOLOv8-seg 학습
- **모델 테스트** — 학습된 `best.pt` 로 RealSense 카메라 실시간 감지

## 시스템 요구사항

- Python 3.11
- NVIDIA GPU 권장 (없으면 CPU로 동작, 매우 느림)
  - Blackwell (RTX 50xx): CUDA 12.8 자동 선택
  - Ampere/Ada/Hopper: CUDA 12.4 자동 선택
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
4. GPU compute capability 감지 → 적절한 PyTorch CUDA 빌드 설치
5. `requirements.txt` 의존성 설치

## Windows 설치

### 자동 설치

PowerShell 에서:
```powershell
git clone https://github.com/Dongju3079/labeler.git
cd labeler
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```

스크립트가 자동으로:
1. Python 3.11 확인
2. SAM 가중치 다운로드
3. `venv\` 가상환경 생성
4. GPU 감지 → CUDA 빌드 자동 선택 (cu128 / cu124 / CPU)
5. 의존성 설치

실행:
```powershell
.\venv\Scripts\python.exe label_app.py
```

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

### 단일 PC 시나리오 (촬영 + 라벨링 + 학습 한 곳에서)

```
[사진 만들기]
  영상 파일 입력 → 프레임 캡처 → photos/ 에 저장
        ↓
[라벨링하기]
  photos/ 의 이미지에 SAM 자동 라벨링 → 검수 → YOLO-seg 학습
        ↓
  models/YYYYMMDD_vN/best.pt 저장
        ↓
[모델 테스트]
  best.pt + RealSense → 실시간 볼트 감지
```

### 분할 시나리오 (촬영/라벨링 PC + 학습서버)

촬영용 PC에는 카메라가 있고, 학습은 GPU 서버에서 돌리는 경우:

```
[촬영 PC]                       [학습서버]                    [촬영 PC]
─────────                       ───────                     ─────────
사진 만들기                                                    
   ↓                                                          
라벨링하기 → 검수                                              
   ↓ "학습 시작?" → No                                        
workspace/ 완성                                                
(photos/*.jpg + photos/*.txt)                                  
   ↓ rsync 업로드                                            
                                workspace/ 받음               
                                   ↓                          
                                python train_only.py workspace/
                                   ↓                          
                                models/YYYYMMDD_vN/best.pt   
                                                ← rsync 다운로드
                                                  best.pt 회수
                                                       ↓
                                                  모델 테스트
                                                  (RealSense)
```

#### 핵심 명령

**촬영 PC에서 라벨링만 (학습 안 함)**
```bash
python label_app.py
# 라벨링하기 → 검수 → "학습 시작?" 다이얼로그에서 [아니오]
```

**촬영 PC → 학습서버 업로드** (PC에서 실행)
```bash
# workspace 통째로 업로드
rsync -avz --progress /home/user/boltwork/ \
    user@server:/home/user/boltwork/

# 또는 photos/ 만 (모델은 서버가 새로 만듦)
rsync -avz --progress /home/user/boltwork/photos/ \
    user@server:/home/user/boltwork/photos/
```

**학습서버에서 학습** (서버에서 실행)
```bash
cd ~/labeler
source venv/bin/activate
python train_only.py /home/user/boltwork/

# 옵션 추가
python train_only.py /home/user/boltwork/ --epochs 200 --batch 32
```

**학습서버 → 촬영 PC 회수** (PC에서 실행)
```bash
# 가장 최신 버전 폴더만 pull
rsync -avz --progress \
    user@server:/home/user/boltwork/models/ \
    /home/user/boltwork/models/

# 또는 best.pt 단일 파일만
scp user@server:/home/user/boltwork/models/20260506_v1/best.pt \
    /home/user/boltwork/models/20260506_v1/
```

**촬영 PC에서 모델 테스트**
```bash
python label_app.py
# 모델 테스트 → models/ 에서 best.pt 선택
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
