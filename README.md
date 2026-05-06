# 볼트 학습 사용가이드

학습서버: **192.168.0.150**

---

## 1. 영상 보내기 (카메라 PC, PowerShell)

```powershell
scp <영상파일> <본인계정>@192.168.0.150:~/boltwork_<날짜>/photos/
```

예:
```powershell
scp C:\Videos\bolt.mp4 matthew@192.168.0.150:~/boltwork_20260506/photos/
```

세션 폴더 이름(`boltwork_20260506`)은 매번 새로 정해도 됨. 자동 생성됨.

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
scp <본인계정>@192.168.0.150:~/boltwork_<날짜>/models/<버전>/best.pt C:\저장경로\
```

예:
```powershell
scp matthew@192.168.0.150:~/boltwork_20260506/models/20260506_v1/best.pt C:\models\
```
