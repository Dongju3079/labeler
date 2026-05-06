# 볼트 학습 사용가이드

학습서버: **192.168.0.150**

---

## 1. 영상 보내기 (카메라 PC, PowerShell)

먼저 서버에 폴더를 만든 뒤 영상 전송:

```powershell
ssh <본인계정>@192.168.0.150 "mkdir -p ~/boltwork_<날짜>/photos"
scp "<영상파일>" <본인계정>@192.168.0.150:~/boltwork_<날짜>/photos/
```

예:
```powershell
ssh matthew@192.168.0.150 "mkdir -p ~/boltwork_20260506/photos"
scp "C:\Videos\bolt.mp4" matthew@192.168.0.150:~/boltwork_20260506/photos/
```

> **⚠️ 경로 주의** — 영상 경로에 **공백 또는 한글**이 들어있으면 반드시 큰따옴표 `" "` 로 감싸기. 안 그러면 scp 가 끊어 읽어서 `No such file or directory` 에러.
> 예: `"C:\Users\matth\OneDrive\Desktop\새 폴더\bolt.mp4"`

세션 폴더 이름(`boltwork_20260506`)은 매번 새로 정해도 됨.

---

## 2. 학습 (학습서버 원격 데스크톱 접속, 터미널)

```bash
cd ~/labeler
source venv/bin/activate
python label_app.py
```

GUI 뜨면:
1. 작업 폴더 선택 → 방금 보낸 세션 폴더 (`~/boltwork_20260506`)
2. **[사진 만들기]** → 영상 선택 → 프레임 캡처
3. **[라벨링하기]** → SAM 자동라벨 → 검수 → `Q` → 학습 시작 **[예]**

학습 완료 시 `~/boltwork_<날짜>/models/<날짜_v버전>/best.pt` 생성.

---

## 3. best.pt 회수 (카메라 PC, PowerShell)

```powershell
scp <본인계정>@192.168.0.150:~/boltwork_<날짜>/models/<버전>/best.pt "<저장경로>"
```

예:
```powershell
scp matthew@192.168.0.150:~/boltwork_20260506/models/20260506_v1/best.pt "C:\models\"
```

> 저장 경로에 공백/한글 있으면 큰따옴표로 감싸기.
