# BoltLabeler

볼트 라벨링 GUI — 사진 캡처, SAM 자동 라벨링, YOLO 학습, RealSense 실시간 감지.

## 주요 기능

- **사진 만들기** — 영상에서 프레임 캡처
- **라벨링하기** — SAM 자동 라벨링 + 검수 (수동 폴리곤 / 삭제 / 초기화)
- **모델 테스트** — `best.pt` 로 RealSense 카메라 실시간 감지

## 설치 (Windows)

PowerShell 에서:

```powershell
git clone https://github.com/Dongju3079/labeler.git
cd labeler
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```

스크립트가 자동으로 처리:
- Python 3.11 확인
- SAM 가중치(`sam_vit_b_01ec64.pth`, 358MB) 다운로드
- 가상환경 `venv\` 생성
- GPU 감지 → 적합한 PyTorch CUDA 빌드 설치
- 의존성 설치

> Python 3.11 미설치 시 [공식 사이트](https://www.python.org/downloads/release/python-3119/) 에서 설치 (PATH 추가 체크).
> RealSense 카메라 사용 시 [Intel RealSense SDK 2.0](https://github.com/IntelRealSense/librealsense/releases) 별도 설치.

## 실행

```powershell
.\venv\Scripts\python.exe label_app.py
```

처음 실행하면 작업 폴더 선택 다이얼로그가 뜸. 영문 경로 권장 (예: `C:\boltwork`).

## 사용 흐름

1. **[사진 만들기]** — 영상 파일 입력 → 프레임 캡처 → `C:\boltwork\photos\` 에 저장
2. **[라벨링하기]** — SAM 자동 라벨링 → 검수
   - 키 단축키: `클릭` 라벨 추가 / `우클릭` 삭제 / `M` 수동 모드 / `N` 네거티브 / `R` 초기화 / `A·D` 이동 / `Q` 종료
   - `Q` 누르면 "학습 시작?" 다이얼로그 → **[아니오]** 클릭
   - → `C:\boltwork\photos\` 안에 `.jpg` + `.txt` (라벨) 생성됨

## 학습서버로 photos 이관

학습은 별도 GPU 서버(`192.168.0.150`) 에서 처리. 라벨링 끝난 photos 폴더만 전송.

**전송 방법** — PowerShell 에서:

```powershell
# 학습 세션마다 새 폴더 만들기 (날짜로 구분 권장)
$session = "boltwork_$(Get-Date -Format yyyyMMdd_HHmm)"

scp -r C:\boltwork\photos <계정>@192.168.0.150:~/$session/photos/
```

예시:
```powershell
scp -r C:\boltwork\photos matthew@192.168.0.150:~/boltwork_20260506_1430/photos/
```

학습은 서버에서 `train_only.py` 로 실행되며, 결과 `best.pt` 가 같은 세션 폴더 안의 `models/<날짜_v버전>/` 에 생성됨.

## 모델 테스트 (best.pt 회수 후)

학습 완료된 best.pt 를 `C:\boltwork\models\<날짜_v버전>\best.pt` 로 받아둔 뒤:

```powershell
.\venv\Scripts\python.exe label_app.py
```

→ **[모델 테스트]** → best.pt 선택 → RealSense 실시간 감지 시작.

## 라이선스

MIT — `LICENSE` 파일 참조.
