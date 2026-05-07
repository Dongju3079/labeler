# BoltLabeler

볼트 인식 모델 학습 도구 — 영상에서 프레임 캡처 + SAM 자동 라벨링은 카메라 PC 에서, 학습은 GPU 학습서버에서 처리.

## 워크플로우

```
[카메라 PC (Windows)]                 [학습서버 192.168.0.150]
─────────────────────                 ─────────────────────
git clone https://github.com/Dongju3079/labeler.git
setup_windows.ps1                     setup_linux.sh
        │                                       │
python label_app.py                             │
  ├─ [사진 만들기] 영상 → photos/                │
  └─ [라벨링하기]  SAM 라벨 → "학습?→아니오"     │
        │                                       │
  C:\boltwork\photos\ (.jpg + .txt)             │
        ↓ scp 전송                              │
                        ~/boltwork_<날짜>/photos/
                                                │
                              python train_only.py ~/boltwork_<날짜>
                                                │
                              ~/boltwork_<날짜>/models/<버전>/best.pt
        ↓ scp 회수                              │
  C:\boltwork\models\<버전>\best.pt             │
        │
python label_app.py
  └─ [모델 테스트] best.pt + RealSense
```

## 1. 카메라 PC (Windows) 셋업

PowerShell:
```powershell
git clone https://github.com/Dongju3079/labeler.git
cd labeler
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```

자동 처리: Python 3.11 확인 → SAM 가중치 다운로드 → venv 생성 → GPU 자동 감지 → PyTorch 설치 → 의존성 설치.

## 2. 라벨링 (카메라 PC)

```powershell
.\venv\Scripts\python.exe label_app.py
```

1. 작업 폴더 선택 (예: `C:\boltwork`)
2. **[사진 만들기]** → 영상 선택 → 프레임 캡처 (`photos/` 자동 생성)
3. **[라벨링하기]** → SAM 자동 라벨링 → 검수
   - 클릭/우클릭/M/N/R/A·D/Q
   - `Q` → "학습 시작?" → **[아니오]** ← 학습은 서버에서 할 거니 No
4. 결과: `C:\boltwork\photos\` 안에 `.jpg` + `.txt` (라벨)

## 3. 학습서버로 photos 전송

```powershell
ssh <본인계정>@192.168.0.150 "mkdir -p ~/boltwork_<날짜>/photos"
scp -r "C:\boltwork\photos\*" <본인계정>@192.168.0.150:~/boltwork_<날짜>/photos/
```

예:
```powershell
ssh matthew@192.168.0.150 "mkdir -p ~/boltwork_20260507/photos"
scp -r "C:\boltwork\photos\*" matthew@192.168.0.150:~/boltwork_20260507/photos/
```

> **경로 주의** — 공백/한글 들어있으면 큰따옴표 `" "` 로 감싸기.
> **첫 SSH 접속 시** `Are you sure...?` 프롬프트 → `yes`.

## 4. 학습 (학습서버, 원격 데스크톱)

학습서버 셋업 (1회):
```bash
cd ~
git clone https://github.com/Dongju3079/labeler.git
cd labeler
chmod +x setup_linux.sh
./setup_linux.sh
```

학습 실행:
```bash
cd ~/labeler
source venv/bin/activate
python train_only.py ~/boltwork_<날짜>
```

옵션 (선택):
```bash
python train_only.py ~/boltwork_<날짜> --epochs 200 --batch 32
```

완료 시 `~/boltwork_<날짜>/models/<날짜_v버전>/best.pt` 생성.

## 5. best.pt 회수 (서버 → 카메라 PC)

PowerShell:
```powershell
scp -r <본인계정>@192.168.0.150:~/boltwork_<날짜>/models C:\boltwork\
```

예:
```powershell
scp -r matthew@192.168.0.150:~/boltwork_20260507/models C:\boltwork\
```

→ `C:\boltwork\models\<날짜_v버전>\best.pt` 생성됨.

## 6. 모델 테스트 (카메라 PC)

```powershell
.\venv\Scripts\python.exe label_app.py
```

→ **[모델 테스트]** → 회수한 `best.pt` 선택 → RealSense 실시간 감지.

## 시스템 요구사항

**카메라 PC**
- Windows 10/11 64bit, Python 3.11
- (권장) NVIDIA GPU — SAM 라벨링 가속용
- (선택) Intel RealSense D435i — 모델 테스트용

**학습서버**
- Ubuntu 22.04 / Debian 12, Python 3.11
- NVIDIA GPU (8GB+ VRAM 권장)

## 라이선스
MIT
