# BoltLabeler 사용 가이드

볼트 인식 모델 학습 도구. 카메라 PC 에서 라벨링까지 완료 후, 학습서버로 보내서 학습, 결과만 회수.

```
[카메라 PC]                                  [학습서버 192.168.0.150]
─────────                                    ─────────────────
BoltLabeler.exe                              
  ├─ 영상 캡처                              
  └─ SAM 라벨링                             
        ↓ scp 전송                          
                                            ~/boltwork_<날짜>/photos/
                                                   ↓ (학습 진행)
                                            ~/boltwork_<날짜>/models/<버전>/best.pt
        ↓ scp 회수                          
  best.pt                                   
        ↓                                   
BoltLabeler.exe → 모델 테스트 (RealSense)   
```

## 1. 설치 (카메라 PC)

### 1-1. 공유폴더에서 BoltLabeler.zip 다운로드

파일 탐색기 주소창에 입력:
```
\\192.168.0.150\share
```

자격증명 창이 뜨면:
- 사용자: `und-share`
- 암호: `und1234`

`matthew` 폴더 안의 **`BoltLabeler.zip`** 을 본인 PC 로 복사.

### 1-2. 압축 해제

**영문 경로**에 풀기 (예: `C:\BoltLabeler\`).

> ⚠️ **한글 경로 금지** — SAM 모델 로딩이 깨질 수 있음. `새 폴더`, `바탕 화면` 같은 한글 폴더 안에 풀지 말 것.

### 1-3. 실행

`C:\BoltLabeler\BoltLabeler.exe` 더블클릭.

> 첫 실행 시 SAM 모델 로딩에 30초~1분 소요 (응답없음 표시 정상).

---

## 2. 라벨링 (카메라 PC)

BoltLabeler 실행 후:

1. **작업 폴더 선택** 다이얼로그 → 영문 경로 만들기 (예: `C:\boltwork`)
2. **[사진 만들기]** → 영상 파일 선택 → 프레임 자동 캡처 → `photos/` 에 저장
3. **[라벨링하기]** → SAM 자동 라벨링 → 검수
   - **클릭** 라벨 추가 / **우클릭** 삭제 / **M** 수동 모드 / **N** 네거티브 / **R** 초기화 / **A·D** 이동 / **Q** 종료
   - `Q` → "학습 시작?" 다이얼로그 → **[아니오]** ← 학습은 서버에서 처리
4. 결과: `C:\boltwork\photos\` 안에 `.jpg` (이미지) + `.txt` (라벨) 생성

---

## 3. 학습서버로 전송

PowerShell 에서:

```powershell
ssh <본인계정>@192.168.0.150 "mkdir -p ~/boltwork_<날짜>/photos"
scp -r "C:\boltwork\photos\*" <본인계정>@192.168.0.150:~/boltwork_<날짜>/photos/
```

예:
```powershell
ssh matthew@192.168.0.150 "mkdir -p ~/boltwork_20260507/photos"
scp -r "C:\boltwork\photos\*" matthew@192.168.0.150:~/boltwork_20260507/photos/
```

> **경로 주의** — 공백/한글 있으면 큰따옴표 `" "` 로 감싸기.
> **첫 SSH 접속 시** `Are you sure you want to continue connecting?` → `yes` 입력.
> **비밀번호 입력 시 화면에 안 보임** (정상). 그냥 치고 엔터.

전송 완료 후 학습서버에서 학습 진행 (관리자가 처리).

---

## 4. best.pt 회수

학습 완료 안내를 받으면 PowerShell 에서:

```powershell
scp -r <본인계정>@192.168.0.150:~/boltwork_<날짜>/models C:\boltwork\
```

예:
```powershell
scp -r matthew@192.168.0.150:~/boltwork_20260507/models C:\boltwork\
```

→ `C:\boltwork\models\<날짜_v버전>\best.pt` 생성됨.

---

## 5. 모델 테스트

```
BoltLabeler.exe → [모델 테스트] → best.pt 선택 → RealSense 실시간 감지
```

`Q` 또는 `ESC` 로 종료.

---

## 시스템 요구사항

- Windows 10/11 64bit
- (권장) NVIDIA GPU — SAM 라벨링 가속
- (선택) Intel RealSense D435i — 모델 테스트용
- 디스크 여유공간 10GB+ (BoltLabeler 4.5GB + 작업 데이터)

## 트러블슈팅

**프로그램이 응답 없음 (실행 직후)**
- SAM 모델 로딩 중. 30초~1분 대기.

**SAM 모델 로딩 실패 / 한글경로 에러**
- BoltLabeler 폴더가 한글 경로에 있음. 영문 경로(`C:\BoltLabeler\`)로 옮긴 후 재실행.

**SSH/SCP `Permission denied`**
- 계정명 또는 비밀번호 오류. 학습서버 관리자에게 본인 계정 확인.

**SSH/SCP 비밀번호 입력해도 진행 안 됨**
- 화면에 안 보일 뿐 입력은 들어감. 비밀번호 끝까지 치고 엔터.

**`scp: stat local "...": No such file or directory`**
- 로컬 경로에 공백/한글 있는데 따옴표 빠짐. `"경로"` 처럼 큰따옴표로 감싸기.

**RealSense 카메라 인식 안 됨**
- Intel RealSense SDK 2.0 별도 설치 필요: https://github.com/IntelRealSense/librealsense/releases
