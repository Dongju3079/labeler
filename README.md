# BoltLabeler

볼트 라벨링 / 학습 GUI — SAM 자동 라벨링 + YOLO 학습 + RealSense 실시간 감지.

> 카메라 PC 에서는 **영상만 찍어서 학습서버로 전송**하면 끝.
> 프레임 캡처, 라벨링, 학습, 모델 테스트는 **모두 학습서버에서 처리**합니다.

## 전체 구조

```
[카메라 PC]                       [학습서버 192.168.0.150]
─────────                       ─────────────────────
영상 녹화                        ~/labeler/  (이 repo)
   ↓ scp 전송
                                ~/<세션폴더>/photos/video.mp4
                                       ↓
                                python label_app.py
                                ├─ [사진 만들기] 영상 → 프레임
                                ├─ [라벨링하기]  SAM + 검수 → 학습
                                └─ [모델 테스트] best.pt 확인
                                       ↓
                                ~/<세션폴더>/models/<날짜_v버전>/best.pt
                                       ↓ (필요 시 PC 로 회수)
```

## 카메라 PC

설치할 것 **없음**. 영상 녹화 후 scp 만 보내면 됨.

```powershell
# PowerShell - Windows 10/11 은 OpenSSH 기본 탑재
scp <영상파일> <계정>@192.168.0.150:~/boltwork_<날짜>/photos/
```

예시:
```powershell
scp C:\Videos\bolt_capture.mp4 matthew@192.168.0.150:~/boltwork_20260506/photos/
```

세션 폴더 이름은 학습 한 사이클 단위로 자유롭게 (예: `boltwork_20260506`, `bolt_v1` 등).

## 학습서버 (Linux)

### 설치 (1회)

```bash
cd ~
git clone https://github.com/Dongju3079/labeler.git
cd labeler
chmod +x setup_linux.sh
./setup_linux.sh
```

자동으로:
- `python3.11`, `python3-tk` 설치
- SAM 가중치 다운로드 (358MB)
- `venv/` 생성
- GPU 감지 → PyTorch CUDA 빌드 자동 선택 (RTX 50xx → cu128)
- 의존성 설치

### 실행

```bash
cd ~/labeler
source venv/bin/activate
python label_app.py
```

→ 작업 폴더 선택 다이얼로그 → 카메라 PC 가 보낸 세션 폴더 선택 (예: `~/boltwork_20260506`)

### 사용 흐름

1. **[사진 만들기]** → 보내준 영상(`photos/*.mp4`) 선택 → 프레임 캡처
2. **[라벨링하기]** → SAM 자동 라벨링 + 검수
   - 키: `클릭` 라벨 / `우클릭` 삭제 / `M` 수동 모드 / `N` 네거티브 / `R` 초기화 / `A·D` 이동 / `Q` 종료
   - `Q` → "학습 시작?" → **[예]** → 자동으로 학습까지 진행
3. **[모델 테스트]** (선택) → 학습서버에 RealSense 연결돼있으면 실시간 감지로 검증

학습 완료 시 `~/<세션폴더>/models/<날짜_v버전>/best.pt` 생성.

## best.pt 회수 (선택)

카메라 PC 의 production 시스템에서 쓰려면, PC 의 PowerShell 에서:

```powershell
scp <계정>@192.168.0.150:~/<세션폴더>/models/<날짜_v버전>/best.pt C:\path\to\save\
```

## 시스템 요구사항 (학습서버)

- Ubuntu 22.04 / Debian 12 권장
- Python 3.11
- NVIDIA GPU + 충분한 VRAM (권장 8GB 이상)
- (선택) Intel RealSense D435i — 모델 테스트 실시간 감지용

## 라이선스

MIT — `LICENSE` 파일 참조.
