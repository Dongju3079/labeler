# BoltLabeler 분할 워크플로우 가이드

촬영 PC(Windows)에서 라벨링하고, 별도 학습서버(Linux + GPU)에서 학습한 뒤,
다시 촬영 PC로 모델을 회수해서 RealSense 카메라로 테스트하는 방식.

## 목차
1. [전체 구조](#전체-구조)
2. [장비 / 계정 준비](#장비--계정-준비)
3. [1회성 셋업](#1회성-셋업)
4. [일상 워크플로우](#일상-워크플로우)
5. [자동화 스크립트](#자동화-스크립트)
6. [트러블슈팅](#트러블슈팅)

---

## 전체 구조

```
[Windows 촬영 PC]                [공유서버 SMB]              [Linux 학습서버 GPU]
─────────────────                ─────────────              ───────────────────
BoltLabeler GUI                                              ~/labeler/
  python label_app.py                                        (git clone)
       │                                                     
       ▼                                                     
  C:\boltwork\photos\                                        
  ├── *.jpg                                                  
  └── *.txt (라벨)                                           
       │                                                     
       │ push_photos.bat                                     
       ▼                                                     
                                 \\share\boltwork\           
                                 └── photos\                 
                                                              │
                                                              │ /mnt/share 마운트
                                                              ▼
                                                          bolt_train.sh
                                                              │
                                                              ▼
                                 \\share\boltwork\           
                                 └── models\                 
                                     └── 20260506_v1\        
                                         └── best.pt         
       │                                                     
       │ pull_models.bat                                      
       ▼                                                     
  C:\boltwork\models\20260506_v1\best.pt                     
       │                                                     
       ▼                                                     
  BoltLabeler GUI → 모델 테스트                              
  (RealSense 카메라 실시간 감지)                             
```

데이터 흐름은 단방향(촬영 PC → 학습서버 → 촬영 PC)이라 충돌 걱정 없음.

---

## 장비 / 계정 준비

### 촬영 PC (Windows)
- Windows 10/11 64bit
- Python 3.11 ([공식 사이트](https://www.python.org/downloads/release/python-3119/))
- Git ([Git for Windows](https://git-scm.com/download/win))
- Intel RealSense D435i (모델 테스트용, 라벨링만 할 거면 불필요)
- (선택) NVIDIA GPU — 라벨링 시 SAM 가속 (없어도 동작, 단 느림)

### 학습서버 (Linux)
- Ubuntu 22.04 / Debian 12 권장
- Python 3.11
- NVIDIA GPU (CUDA 지원)
- 인터넷 연결 (의존성 설치용)

### 공유서버 (SMB/CIFS)
- 양쪽에서 접근 가능한 SMB 공유
- 네트워크 경로 (예: `\\192.168.0.150\share`)
- 본인 폴더 (예: `\\192.168.0.150\share\<본인이름>\`)
- 공유 계정 / 비밀번호

---

## 1회성 셋업

### A. 촬영 PC (Windows)

**1. Git 으로 코드 받기**

PowerShell 또는 CMD 에서:
```powershell
cd C:\
git clone https://github.com/Dongju3079/labeler.git
cd labeler
```

**2. 자동 설치 스크립트 실행**

```powershell
# PowerShell 실행 정책 우회 (한 세션 한정)
Set-ExecutionPolicy -Scope Process Bypass

# 설치 시작
.\setup_windows.ps1
```

스크립트가 자동으로:
- Python 3.11 확인
- SAM 가중치 다운로드 (`sam_vit_b_01ec64.pth`, 358MB)
- `venv\` 가상환경 생성
- GPU compute capability 감지 → CUDA 빌드 자동 선택 (Blackwell은 cu128, 이전 세대는 cu124, GPU 없으면 CPU)
- `requirements.txt` 의존성 설치

소요시간 10~20분.

**3. RealSense SDK 설치 (모델 테스트 기능 쓸 때만)**

[Intel RealSense SDK 2.0](https://github.com/IntelRealSense/librealsense/releases) 다운로드 → 설치.
설치 후 PC 재기동 권장.

**4. 작업 폴더 생성**

```powershell
mkdir C:\boltwork
```

`C:\` 직하단 영문 경로 권장 — 한글 경로면 SAM 모델 로딩이 깨질 수 있음.

**5. 실행 테스트**

```powershell
cd C:\labeler
.\venv\Scripts\python.exe label_app.py
```

Tk 창이 떠서 "작업 폴더 선택" 다이얼로그가 나오면 정상.
→ `C:\boltwork` 선택.

### B. 학습서버 (Linux)

**1. 사전 확인**

```bash
lsb_release -a            # Ubuntu 22.04 인지
python3.11 --version      # Python 3.11
nvidia-smi                # GPU + 드라이버
```

Python 3.11이 없으면:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3.11-tk
```

**2. Git 으로 코드 받기**

```bash
cd ~
git clone https://github.com/Dongju3079/labeler.git
cd labeler
```

**3. 자동 설치 스크립트**

```bash
chmod +x setup_linux.sh
./setup_linux.sh
```

스크립트가 자동으로:
- `python3-tk` 등 시스템 패키지 설치 (sudo 비번 한 번)
- SAM 가중치 다운로드
- `venv/` 가상환경 생성
- GPU 감지 → CUDA 빌드 선택 (RTX 50xx → cu128, 이전 → cu124)
- 의존성 설치

### C. 공유서버 마운트

**촬영 PC (Windows)**

PowerShell 에서 한 번 자격증명 등록:
```powershell
# 자격증명을 Windows Credential Manager 에 저장 (다음부터 자동 로그인)
cmdkey /add:192.168.0.150 /user:<공유계정> /pass:<공유비번>

# 마운트 테스트
net use \\192.168.0.150\share

# 본인 폴더 만들기 (없으면)
mkdir \\192.168.0.150\share\<본인이름>\boltwork
```

**학습서버 (Linux)**

```bash
# cifs-utils 설치
sudo apt install -y cifs-utils

# 마운트 포인트
sudo mkdir -p /mnt/share

# 자격증명 파일 (보안)
sudo tee /root/.smbcred > /dev/null <<EOF
username=<공유계정>
password=<공유비번>
EOF
sudo chmod 600 /root/.smbcred

# /etc/fstab 에 추가 (재부팅 시 자동 마운트)
echo "//192.168.0.150/share /mnt/share cifs credentials=/root/.smbcred,uid=$(id -u),gid=$(id -g),iocharset=utf8,vers=3.0 0 0" | sudo tee -a /etc/fstab

# 즉시 마운트
sudo mount -a

# 확인
ls /mnt/share
```

`<본인이름>` 폴더가 보이면 OK.

---

## 일상 워크플로우

### Step 1. 촬영 PC — 사진 캡처

```powershell
cd C:\labeler
.\venv\Scripts\python.exe label_app.py
```

→ `[사진 만들기]`
- 영상 파일 선택 (mp4, avi 등)
- 프레임 자동 캡처 → `C:\boltwork\photos\` 에 저장
- 검수 화면에서 흐릿한/중복된 프레임 삭제

### Step 2. 촬영 PC — 라벨링

→ `[라벨링하기]`
- SAM 자동 라벨링 (모델 로딩 30초~1분)
- 검수 화면에서 잘못된 라벨 수정 / 삭제
  - **클릭**: 자동 라벨 추가
  - **우클릭**: 라벨 삭제
  - **M**: 수동 폴리곤 모드 토글
  - **N**: NEGATIVE (볼트 없음) 표시
  - **R**: 현재 이미지 라벨 초기화
  - **A/D**: 이전/다음 이미지
  - **Q**: 검수 종료
- `Q` 누르면 통계 다이얼로그 + **"학습 시작?" → [아니오] 클릭**
- → 라벨링만 저장하고 종료. `C:\boltwork\photos\` 안에 `.txt` 파일들이 추가됨.

### Step 3. 촬영 PC — 공유서버에 업로드

```powershell
cd C:\labeler\scripts
.\push_photos.bat
```

스크립트가 robocopy 로 photos 폴더를 share 에 미러링.
처음엔 전체 업로드라 시간 걸리고, 그다음부턴 변경분만.

### Step 4. 학습서버 — 학습 실행

학습서버에 SSH 또는 원격 데스크톱 접속 후:

```bash
cd ~/labeler/scripts
chmod +x bolt_train.sh    # 처음 한 번만
./bolt_train.sh
```

기본 설정 (100 epoch, batch 16, imgsz 640) 으로 학습.
커스텀 옵션:
```bash
./bolt_train.sh --epochs 200 --batch 32
./bolt_train.sh --epochs 50 --imgsz 320  # 빠른 테스트용
```

학습 진행상황이 콘솔에 뜨고 RTX 5080 기준 100 epoch ~ 5~30분 (데이터셋 크기 의존).

완료 시 콘솔 출력:
```
==========================================
  학습 완료
==========================================
  best.pt:  /mnt/share/<본인>/boltwork/models/20260506_v1/best.pt
  버전:     20260506_v1
==========================================
```

→ best.pt 가 자동으로 share 에 저장됨.

### Step 5. 촬영 PC — 모델 회수

```powershell
cd C:\labeler\scripts
.\pull_models.bat
```

→ `C:\boltwork\models\20260506_v1\best.pt` 생성됨.

### Step 6. 촬영 PC — 모델 테스트

```powershell
cd C:\labeler
.\venv\Scripts\python.exe label_app.py
```

→ `[모델 테스트]`
- best.pt 선택 → `C:\boltwork\models\20260506_v1\best.pt`
- RealSense 카메라 자동 시작 → 실시간 감지 화면

`Q` 또는 `ESC` 로 종료.

---

## 자동화 스크립트

`scripts/` 폴더 안에 셋 있음:

### push_photos.bat (Windows)
촬영 PC → 공유서버 photos 미러링.
사용 전 파일 안의 변수 수정 (LOCAL_WS, SHARE_HOST, SHARE_USER 등).

### pull_models.bat (Windows)
공유서버 → 촬영 PC models 미러링.

### bolt_train.sh (Linux)
학습서버에서 share 마운트된 workspace 학습.
인자는 `train_only.py` 와 동일 (`--epochs`, `--batch`, `--imgsz`, `--patience`, `--base-model`).

### 바탕화면 단축 만들기 (Windows)
편의를 위해:
- `push_photos.bat` 우클릭 → 바로가기 만들기 → 바탕화면으로 이동
- `pull_models.bat` 도 동일

---

## 트러블슈팅

### setup_windows.ps1 실행 시 "이 시스템에서 스크립트를 실행할 수 없으므로..."
```powershell
# 한 세션 한정으로 우회
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```

### Python 3.11 못 찾음
- [공식 설치파일](https://www.python.org/downloads/release/python-3119/) 받아서 설치
- 설치 시 **"Add python.exe to PATH"** 체크
- 설치 후 PowerShell 재시작

### `nvidia-smi` 없음 / GPU 미감지
- NVIDIA 드라이버 미설치 또는 PATH 문제
- 드라이버: https://www.nvidia.com/download/index.aspx
- GPU 없는 PC면 CPU 빌드로 동작 (라벨링은 가능, 학습은 매우 느림)

### `no kernel image is available for execution on the device`
- GPU와 PyTorch CUDA 버전 미스매치
- RTX 50xx 인데 cu124 설치된 경우 발생
- 해결: `venv/` 삭제 후 setup 스크립트 재실행

### SAM 모델 로딩에서 응답없음 / 한참 멈춤
- 정상. 첫 로딩 30초~1분, GPU 없으면 더 오래
- 1분 넘게 걸리면 메모리 부족 가능성 → 다른 GPU 프로그램 종료

### `ModuleNotFoundError: No module named '_tkinter'` (Linux)
```bash
sudo apt install python3.11-tk
# 또는
sudo apt install python3-tk
```

### 공유서버 마운트 안 됨 (Linux)
```bash
# 마운트 상태 확인
mount | grep share

# 수동 마운트 시도 (에러 메시지 확인)
sudo mount //192.168.0.150/share /mnt/share -o credentials=/root/.smbcred,uid=$(id -u),gid=$(id -g),iocharset=utf8,vers=3.0

# 흔한 원인: SMB 버전 불일치 → vers=2.0 또는 vers=1.0 시도
```

### robocopy 실행 후 "Access is denied" (Windows)
```powershell
# 자격증명 재등록
net use \\192.168.0.150\share /delete
cmdkey /delete:192.168.0.150
cmdkey /add:192.168.0.150 /user:<공유계정> /pass:<공유비번>
net use \\192.168.0.150\share
```

### 학습 도중 OOM (CUDA out of memory)
- batch 크기 줄이기: `./bolt_train.sh --batch 8` 또는 `--batch 4`
- imgsz 줄이기: `--imgsz 320`
- 다른 GPU 프로세스 종료: `nvidia-smi` 로 확인 후 `kill <PID>`

### 학습 결과가 너무 안 좋음 (mAP 낮음)
- 라벨링 데이터 부족 — 최소 30~50장 추천
- 네거티브 샘플 부족 — 볼트 없는 사진도 30% 정도 섞기
- 환경 다양성 부족 — 조명, 각도, 배경 변화 데이터 추가
- epoch 늘리기: `--epochs 300 --patience 50`

---

## FAQ

**Q. 학습서버에서 GUI(label_app.py) 도 돌릴 수 있나?**
A. 가능. 원격 데스크톱이나 X11 forwarding 으로. 단 학습서버에 RealSense 카메라가 없으면 모델 테스트 기능은 못 씀.

**Q. workspace.txt 가 PC 에 남는데 지워도 되나?**
A. 지워도 됨. 다음 실행 때 작업 폴더 선택 다이얼로그가 다시 뜸.

**Q. 학습 중인 데 PC 끄면?**
A. 학습은 학습서버에서 돌아가니 PC 꺼도 됨. SSH 로 접속해서 학습 돌릴 거면 `tmux` 또는 `nohup` 사용 권장 (SSH 끊겨도 학습 계속).

```bash
# tmux 세션
tmux new -s train
./bolt_train.sh
# Ctrl+B, D 로 detach (세션은 살아있음)
# 다시 들어가기: tmux attach -t train
```

**Q. 학습 결과를 여러 버전 보관 가능?**
A. 자동 보관됨. `models/20260506_v1`, `models/20260506_v2`, `models/20260507_v1` 식으로 날짜+버전 폴더 자동 생성. 모델 테스트 시 원하는 버전 선택.

**Q. share 안 쓰고 USB 로 옮겨도 되나?**
A. 됨. workspace 폴더 통째로 USB 에 복사 → 학습서버에 풀어서 `python train_only.py /path/to/workspace` 로 학습. 결과물 best.pt 만 USB 로 가져오면 됨.

---

## 더 알아보기

- 메인 README: [README.md](./README.md)
- 코드 진입점: [label_app.py](./label_app.py)
- 학습 전용 스크립트: [train_only.py](./train_only.py)
- 자동화 배치: [scripts/](./scripts/)
