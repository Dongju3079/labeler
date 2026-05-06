# BoltLabeler 사용 가이드

볼트 인식 모델 학습 — 영상만 보내주면 학습서버에서 best.pt 까지 만들어드립니다.

> 학습서버: **192.168.0.150** (계정은 본인 것)
> 카메라 PC 에 설치할 것 **없음**.

## 사용 흐름

```
[카메라 PC] 영상 녹화 → scp 전송
                ↓
[학습서버] 원격 데스크톱 진입 → label_app.py 실행
        → 프레임 캡처 → SAM 라벨링 → 학습
                ↓
[학습서버] best.pt 생성 완료
                ↓
[카메라 PC] (필요시) best.pt scp 회수
```

## 1. 영상 보내기 (카메라 PC)

PowerShell:

```powershell
scp <영상파일> <계정>@192.168.0.150:~/boltwork_<날짜>/photos/
```

예:
```powershell
scp C:\Videos\bolt.mp4 matthew@192.168.0.150:~/boltwork_20260506/photos/
```

세션 폴더 이름(`boltwork_20260506`) 은 학습 한 사이클마다 새로 정하세요. 서버에 폴더가 없어도 scp 가 자동 생성합니다.

## 2. 학습 (학습서버, 원격 데스크톱)

학습서버 원격 데스크톱 접속 후 터미널에서:

```bash
cd ~/labeler
source venv/bin/activate
python label_app.py
```

GUI 가 뜨면:

1. **작업 폴더 선택** → 방금 영상 보낸 세션 폴더 (예: `~/boltwork_20260506`)
2. **[사진 만들기]** → `photos/` 안의 영상 선택 → 프레임 자동 캡처
3. **[라벨링하기]** → SAM 자동 라벨링 → 검수
   - `클릭` 라벨 추가 / `우클릭` 삭제 / `M` 수동 모드 / `N` 네거티브 / `R` 초기화 / `A·D` 이동 / `Q` 종료
   - `Q` → "학습 시작?" → **[예]** → 학습 자동 진행
4. 학습 완료 → `~/boltwork_<날짜>/models/<날짜_v버전>/best.pt` 생성

## 3. best.pt 회수 (선택)

카메라 PC PowerShell:

```powershell
scp <계정>@192.168.0.150:~/boltwork_<날짜>/models/<날짜_v버전>/best.pt C:\저장경로\
```

예:
```powershell
scp matthew@192.168.0.150:~/boltwork_20260506/models/20260506_v1/best.pt C:\models\
```

---

## 학습서버 셋업 (관리자용, 1회)

새 학습서버 구축 시:

```bash
cd ~
git clone https://github.com/Dongju3079/labeler.git
cd labeler
chmod +x setup_linux.sh
./setup_linux.sh
```

- Python 3.11, python3-tk
- SAM 가중치 (358MB)
- venv + PyTorch (GPU 자동 감지)
- 의존성

## 라이선스
MIT
