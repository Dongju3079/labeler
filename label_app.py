"""
볼트 라벨링 프로그램 (GUI)

기능:
  1. 사진만들기: 영상에서 프레임 캡처 → 검수/삭제
  2. 라벨링하기: SAM 자동라벨링 → 검수(자동/수동 폴리곤, 삭제, 초기화) → 학습
  3. 모델 테스트: best.pt 선택 → RealSense 카메라 실시간 감지

실행:
  python label_app.py
"""

import os
import sys
import glob
import shutil
import random
import time
import yaml
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime


# ═══════════════════════════════════════════════════════════
#  설정
# ═══════════════════════════════════════════════════════════

SAM_MODEL_PATH = "sam_vit_b_01ec64.pth"
SAM_MODEL_TYPE = "vit_b"
WINDOW_SIZE = (1280, 960)
WORKSPACE_FILE = "workspace.txt"  # 마지막 작업 폴더 기억


# ═══════════════════════════════════════════════════════════
#  작업 폴더 관리
# ═══════════════════════════════════════════════════════════

def get_workspace():
    """작업 폴더 선택 (이전 경로 기억)"""
    # 이전 작업 폴더 로드
    last_dir = ""
    if os.path.exists(WORKSPACE_FILE):
        with open(WORKSPACE_FILE) as f:
            last_dir = f.read().strip()

    root = tk.Tk()
    root.withdraw()
    workspace = filedialog.askdirectory(
        title="작업 폴더를 선택하세요 (학습 결과가 여기에 저장됩니다)",
        initialdir=last_dir if os.path.exists(last_dir) else "."
    )
    root.destroy()

    if not workspace:
        return None

    # 기억
    with open(WORKSPACE_FILE, "w") as f:
        f.write(workspace)

    # 하위 폴더 생성
    os.makedirs(os.path.join(workspace, "photos"), exist_ok=True)
    os.makedirs(os.path.join(workspace, "models"), exist_ok=True)

    return workspace


# ═══════════════════════════════════════════════════════════
#  SAM 관리
# ═══════════════════════════════════════════════════════════

class SAMManager:
    """SAM 모델 싱글톤 관리"""

    def __init__(self):
        self.predictor = None
        self.current_image_path = None

    def init(self):
        """SAM 모델 로드"""
        if self.predictor is not None:
            return
        print("[SAM] 모델 로드 중...")
        import torch
        from segment_anything import sam_model_registry, SamPredictor
        device = "cuda" if torch.cuda.is_available() else "cpu"
        sam = sam_model_registry[SAM_MODEL_TYPE](checkpoint=SAM_MODEL_PATH)
        sam.to(device)
        self.predictor = SamPredictor(sam)
        print(f"[SAM] 준비 완료 (device={device})")

    def set_image(self, img_path):
        """SAM에 이미지 세팅 (변경 시에만)"""
        if self.current_image_path == img_path:
            return
        img = cv2.imread(img_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.predictor.set_image(img_rgb)
        self.current_image_path = img_path

    def segment(self, img_path, x, y):
        """클릭 좌표 → 폴리곤 반환"""
        self.set_image(img_path)
        input_point = np.array([[x, y]])
        input_label = np.array([1])
        masks, scores, _ = self.predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,
        )
        best_idx = np.argmax(scores)
        mask = masks[best_idx]

        # 마스크 → 컨투어 → 폴리곤
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        cnt = max(contours, key=cv2.contourArea)
        if cv2.contourArea(cnt) < 100:
            return None

        epsilon = 0.015 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        poly = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
        return poly if len(poly) >= 3 else None


# ═══════════════════════════════════════════════════════════
#  라벨 저장/로드 (YOLO-seg 포맷)
# ═══════════════════════════════════════════════════════════

def get_label_path(img_path):
    """이미지 경로 → 라벨 파일 경로"""
    base, _ = os.path.splitext(img_path)
    return base + ".txt"


def save_labels(img_path, labels):
    """폴리곤 라벨을 YOLO-seg 포맷으로 저장"""
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    lbl_path = get_label_path(img_path)
    with open(lbl_path, "w") as f:
        for poly in labels:
            coords = []
            for (px, py) in poly:
                coords.append(f"{px / w:.6f}")
                coords.append(f"{py / h:.6f}")
            f.write("0 " + " ".join(coords) + "\n")


def load_labels(img_path):
    """YOLO-seg 라벨 파일 로드 → 폴리곤 리스트"""
    lbl_path = get_label_path(img_path)
    if not os.path.exists(lbl_path) or os.path.getsize(lbl_path) == 0:
        return []
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    labels = []
    with open(lbl_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 7:
                coords = list(map(float, parts[1:]))
                poly = []
                for j in range(0, len(coords), 2):
                    px = int(coords[j] * w)
                    py = int(coords[j + 1] * h)
                    poly.append((px, py))
                labels.append(poly)
    return labels


# ═══════════════════════════════════════════════════════════
#  1. 사진만들기
# ═══════════════════════════════════════════════════════════

class PhotoMaker:
    """영상에서 프레임 캡처 → 검수/삭제"""

    def __init__(self, workspace):
        self.workspace = workspace
        self.output_dir = os.path.join(workspace, "photos")

    def run(self):
        """영상 선택 → 캡처 → 검수"""
        # 영상 파일 선택
        root = tk.Tk()
        root.withdraw()
        video_path = filedialog.askopenfilename(
            title="영상 파일 선택",
            filetypes=[
                ("영상 파일", "*.mp4 *.avi *.mov *.mkv"),
                ("모든 파일", "*.*"),
            ]
        )
        root.destroy()

        if not video_path:
            print("[사진만들기] 취소됨")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        existing = sorted(glob.glob(os.path.join(self.output_dir, "*.jpg")))
        count = len(existing)

        print(f"\n[사진만들기] 영상: {video_path}")
        print(f"  저장 폴더: {self.output_dir}")
        print(f"  기존 사진: {count}장")
        print()
        print("  SPACE : 캡처")
        print("  A/D   : -5초 / +5초 이동")
        print("  P     : 일시정지/재생")
        print("  Q     : 캡처 종료 → 검수")
        print()

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        cv2.namedWindow("Photo Maker", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Photo Maker", *WINDOW_SIZE)

        paused = False
        frame = None

        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break
            if frame is None:
                continue

            vis = frame.copy()
            current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            current_time = current_frame / fps if fps > 0 else 0

            # 상태 표시
            cv2.putText(vis, f"Time: {current_time:.1f}s / {duration:.1f}s",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(vis, f"Captured: {count}",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            if paused:
                cv2.putText(vis, "PAUSED", (10, 85),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(vis, "SPACE:Capture  A/D:Seek  P:Pause  Q:Done",
                        (10, frame.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            cv2.imshow("Photo Maker", vis)
            key = cv2.waitKeyEx(30 if not paused else 0)

            if key == ord('q'):
                break
            elif key == ord(' '):
                fname = os.path.join(self.output_dir, f"cap_{count:05d}.jpg")
                cv2.imwrite(fname, frame)
                count += 1
                print(f"  캡처: {count}장")
            elif key == ord('p'):
                paused = not paused
            elif key == ord('a') or key == 2424832:
                new_frame = max(0, current_frame - int(fps * 5))
                cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
            elif key == ord('d') or key == 2555904:
                new_frame = min(total_frames, current_frame + int(fps * 5))
                cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)

        cap.release()
        cv2.destroyAllWindows()

        if count == 0:
            print("[사진만들기] 캡처된 사진 없음")
            return

        # 검수 단계
        self._review_photos()

    def _review_photos(self):
        """캡처된 사진 검수 — 불필요한 사진 삭제"""
        images = sorted(glob.glob(os.path.join(self.output_dir, "*.jpg")))
        if not images:
            return

        idx = 0
        deleted = 0

        print(f"\n[검수] {len(images)}장 확인")
        print("  A/D   : 이전/다음")
        print("  DEL   : 삭제")
        print("  Q     : 완료")

        cv2.namedWindow("Review Photos", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Review Photos", *WINDOW_SIZE)

        while True:
            if not images:
                break
            idx = max(0, min(idx, len(images) - 1))

            img = cv2.imread(images[idx])
            vis = img.copy()

            cv2.putText(vis, f"[{idx + 1}/{len(images)}] {os.path.basename(images[idx])}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(vis, f"Deleted: {deleted}",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(vis, "A/D:Nav  DEL:Delete  Q:Done",
                        (10, img.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            cv2.imshow("Review Photos", vis)
            key = cv2.waitKeyEx(0)

            if key == ord('q'):
                break
            elif key == ord('a') or key == 2424832:
                idx = max(0, idx - 1)
            elif key == ord('d') or key == 2555904:
                idx = min(len(images) - 1, idx + 1)
            elif key == 3014656 or key == 127:  # DEL
                os.remove(images[idx])
                print(f"  삭제: {os.path.basename(images[idx])}")
                images.pop(idx)
                deleted += 1

        cv2.destroyAllWindows()
        print(f"\n[검수 완료] 남은 사진: {len(images)}장 / 삭제: {deleted}장")


# ═══════════════════════════════════════════════════════════
#  2. 라벨링하기
# ═══════════════════════════════════════════════════════════

class Labeler:
    """SAM 자동라벨링 → 검수 → 학습"""

    def __init__(self, workspace):
        self.workspace = workspace
        self.sam = SAMManager()
        self.images = []
        self.labels = {}
        self.current_idx = 0
        self.mouse_pos = (0, 0)
        self.need_redraw = True
        self.manual_mode = False
        self.polygon_pts = []

    def run(self):
        """폴더 선택 → 검수 → 학습"""
        # 사진 폴더 선택
        root = tk.Tk()
        root.withdraw()
        folder = filedialog.askdirectory(
            title="라벨링할 사진 폴더 선택",
            initialdir=os.path.join(self.workspace, "photos")
        )
        root.destroy()

        if not folder:
            print("[라벨링] 취소됨")
            return

        self.images = sorted(
            glob.glob(os.path.join(folder, "*.jpg")) +
            glob.glob(os.path.join(folder, "*.png"))
        )
        if not self.images:
            print(f"[ERROR] {folder}에 이미지 없음")
            return

        # SAM 초기화
        self.sam.init()

        # 기존 라벨 로드
        for img_path in self.images:
            self.labels[img_path] = load_labels(img_path)

        existing_labels = sum(1 for v in self.labels.values() if v)
        print(f"\n[라벨링] 이미지: {len(self.images)}장 / 기존 라벨: {existing_labels}장")

        # 검수 화면 (SAM으로 직접 라벨링 + 수정)
        self._review()

        # 학습 통계 표시 및 확인
        labeled = sum(1 for v in self.labels.values() if v)
        negative = sum(1 for p in self.images
                       if os.path.exists(get_label_path(p))
                       and not self.labels.get(p))
        total_bolts = sum(len(v) for v in self.labels.values())

        print(f"\n{'=' * 50}")
        print(f"  학습 데이터 통계")
        print(f"{'=' * 50}")
        print(f"  볼트 이미지:   {labeled}장")
        print(f"  네거티브:      {negative}장")
        print(f"  총 볼트 수:    {total_bolts}개")
        print(f"  미라벨:        {len(self.images) - labeled - negative}장")
        print(f"{'=' * 50}")

        if labeled < 10:
            print("[학습 불가] 최소 10장 필요")
            return

        root = tk.Tk()
        root.withdraw()
        do_train = messagebox.askyesno(
            "학습",
            f"볼트 이미지: {labeled}장\n"
            f"네거티브: {negative}장\n"
            f"총 볼트 수: {total_bolts}개\n\n"
            f"학습을 시작할까요?"
        )
        root.destroy()

        if do_train:
            self._train()

    def _review(self):
        """검수 화면: SAM 자동 + 수동 폴리곤 + 삭제 + 초기화"""
        self.current_idx = 0
        self.manual_mode = False
        self.polygon_pts = []

        cv2.namedWindow("Labeling", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Labeling", *WINDOW_SIZE)
        cv2.setMouseCallback("Labeling", self._mouse_callback)

        print()
        print("=" * 50)
        print("  라벨링 / 검수 모드")
        print("=" * 50)
        print(f"  이미지: {len(self.images)}장")
        print()
        print("  좌클릭     : SAM 자동 폴리곤 (또는 수동 점 추가)")
        print("  우클릭     : 가장 가까운 라벨 삭제")
        print("  M         : SAM <-> 수동 모드 전환")
        print("  SPACE     : [수동] 폴리곤 확정")
        print("  ESC       : [수동] 폴리곤 취소")
        print("  A / <-    : 이전 이미지")
        print("  D / ->    : 다음 이미지")
        print("  N         : 네거티브 샘플 (볼트 없음)")
        print("  R         : 현재 이미지 전체 초기화")
        print("  Q         : 완료")
        print()

        while True:
            if self.need_redraw:
                self._draw()
                self.need_redraw = False

            key = cv2.waitKeyEx(30)

            if key == ord('q'):
                break
            elif key == ord('m'):
                self.manual_mode = not self.manual_mode
                self.polygon_pts = []
                mode = "수동 폴리곤" if self.manual_mode else "SAM"
                print(f"  모드: {mode}")
                self.need_redraw = True
            elif key == ord(' ') and self.manual_mode:
                if len(self.polygon_pts) >= 3:
                    img_path = self.images[self.current_idx]
                    if img_path not in self.labels:
                        self.labels[img_path] = []
                    self.labels[img_path].append(list(self.polygon_pts))
                    save_labels(img_path, self.labels[img_path])
                    n = len(self.polygon_pts)
                    self.polygon_pts = []
                    print(f"  확정 ({n}점)")
                    self.need_redraw = True
                elif self.polygon_pts:
                    print("  최소 3점 필요")
            elif key == 27 and self.manual_mode:
                if self.polygon_pts:
                    self.polygon_pts = []
                    print("  폴리곤 취소")
                    self.need_redraw = True
            elif key == ord('a') or key == 2424832:
                if self.current_idx > 0:
                    self.polygon_pts = []
                    self.current_idx -= 1
                    self.need_redraw = True
            elif key == ord('d') or key == 2555904:
                if self.current_idx < len(self.images) - 1:
                    self.polygon_pts = []
                    self.current_idx += 1
                    self.need_redraw = True
            elif key == ord('n'):
                # 네거티브 샘플: 빈 라벨 파일 생성
                img_path = self.images[self.current_idx]
                self.labels[img_path] = []
                self.polygon_pts = []
                lbl_path = get_label_path(img_path)
                open(lbl_path, 'w').close()
                print(f"  네거티브: {os.path.basename(img_path)}")
                self.need_redraw = True
            elif key == ord('r'):
                img_path = self.images[self.current_idx]
                self.labels[img_path] = []
                self.polygon_pts = []
                # 라벨 파일 삭제
                lbl_path = get_label_path(img_path)
                if os.path.exists(lbl_path):
                    os.remove(lbl_path)
                print(f"  초기화: {os.path.basename(img_path)}")
                self.need_redraw = True

        cv2.destroyAllWindows()

    def _mouse_callback(self, event, x, y, flags, param):
        """마우스 콜백"""
        img_path = self.images[self.current_idx]

        if event == cv2.EVENT_MOUSEMOVE:
            self.mouse_pos = (x, y)
            self.need_redraw = True

        elif event == cv2.EVENT_LBUTTONDOWN:
            if self.manual_mode:
                self.polygon_pts.append((x, y))
            else:
                poly = self.sam.segment(img_path, x, y)
                if poly:
                    if img_path not in self.labels:
                        self.labels[img_path] = []
                    self.labels[img_path].append(poly)
                    save_labels(img_path, self.labels[img_path])
                    print(f"  감지 ({len(poly)}점)")
                else:
                    print(f"  실패")
            self.need_redraw = True

        elif event == cv2.EVENT_RBUTTONDOWN:
            if img_path in self.labels and self.labels[img_path]:
                min_dist = float('inf')
                min_idx = 0
                for i, poly in enumerate(self.labels[img_path]):
                    pts = np.array(poly)
                    cx = pts[:, 0].mean()
                    cy = pts[:, 1].mean()
                    d = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
                    if d < min_dist:
                        min_dist = d
                        min_idx = i
                if min_dist < 200:
                    self.labels[img_path].pop(min_idx)
                    save_labels(img_path, self.labels[img_path])
                    print(f"  삭제 (라벨 {min_idx + 1})")
                    self.need_redraw = True

    def _draw(self):
        """검수 화면 그리기"""
        img_path = self.images[self.current_idx]
        img = cv2.imread(img_path)
        vis = img.copy()
        h, w = img.shape[:2]

        labels = self.labels.get(img_path, [])
        lbl_exists = os.path.exists(get_label_path(img_path))

        # 완성된 폴리곤
        for i, poly in enumerate(labels):
            pts = np.array(poly, dtype=np.int32)
            overlay = vis.copy()
            cv2.fillPoly(overlay, [pts], (0, 255, 0))
            cv2.addWeighted(overlay, 0.3, vis, 0.7, 0, vis)
            cv2.polylines(vis, [pts], True, (0, 255, 0), 2)
            for pt in poly:
                cv2.circle(vis, pt, 3, (0, 0, 255), -1)
            cx = int(pts[:, 0].mean())
            cy = int(pts[:, 1].mean())
            cv2.putText(vis, str(i + 1), (cx - 5, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 수동 모드 진행 중 폴리곤
        if self.manual_mode and self.polygon_pts:
            pts = self.polygon_pts
            for pt in pts:
                cv2.circle(vis, pt, 5, (0, 255, 255), -1)
            for i in range(len(pts) - 1):
                cv2.line(vis, pts[i], pts[i + 1], (0, 255, 255), 2)
            mx, my = self.mouse_pos
            cv2.line(vis, pts[-1], (mx, my), (255, 255, 0), 1)
            cv2.line(vis, (mx, my), pts[0], (255, 255, 0), 1)
            cv2.putText(vis, f"Manual: {len(pts)}pts (SPACE/ESC)",
                        (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 255, 255), 2)

        # 십자 커서
        mx, my = self.mouse_pos
        cv2.drawMarker(vis, (mx, my), (0, 255, 255),
                       cv2.MARKER_CROSS, 20, 1)

        # 모드 표시
        mode_text = "MANUAL" if self.manual_mode else "SAM"
        mode_color = (0, 165, 255) if self.manual_mode else (0, 255, 0)
        cv2.putText(vis, mode_text, (w - 120, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)

        # 상태 판별
        labeled_total = sum(1 for v in self.labels.values() if v)
        n_labels = len(labels)

        if n_labels > 0:
            status = f"Bolts: {n_labels}"
            status_color = (0, 255, 0)
        elif lbl_exists:
            status = "NEGATIVE"
            status_color = (0, 165, 255)
        else:
            status = "UNLABELED"
            status_color = (0, 0, 255)

        cv2.putText(vis, f"[{self.current_idx + 1}/{len(self.images)}] "
                    f"{status} | Total: {labeled_total}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)

        # 도움말
        cv2.putText(vis, "Click:Label  RClick:Del  M:Mode  "
                    "A/D:Nav  N:Neg  R:Reset  Q:Done",
                    (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                    (200, 200, 200), 1)

        cv2.imshow("Labeling", vis)

    def _train(self):
        """YOLO-seg 학습 → 작업폴더/models/날짜_v버전/ 에 저장"""
        from ultralytics import YOLO

        # 라벨 있는 이미지 수집 (볼트 + 네거티브)
        all_labeled = []
        for p in self.images:
            lbl = get_label_path(p)
            if os.path.exists(lbl):
                all_labeled.append(p)

        positive = sum(1 for p in all_labeled if self.labels.get(p))
        negative = len(all_labeled) - positive

        # 버전 폴더 생성: models/20260415_v1/
        models_dir = os.path.join(self.workspace, "models")
        today = datetime.now().strftime("%Y%m%d")

        # 기존 버전 확인 → 다음 버전 번호
        existing = glob.glob(os.path.join(models_dir, f"{today}_v*"))
        version = len(existing) + 1
        version_dir = os.path.join(models_dir, f"{today}_v{version}")
        os.makedirs(version_dir, exist_ok=True)

        print(f"\n{'=' * 50}")
        print(f"  학습 시작")
        print(f"{'=' * 50}")
        print(f"  볼트 이미지: {positive}장")
        print(f"  네거티브:    {negative}장")
        print(f"  저장 위치:   {version_dir}")
        print(f"{'=' * 50}")

        # 데이터셋 구성
        data_dir = os.path.join(version_dir, "dataset")
        random.seed(42)
        shuffled = all_labeled.copy()
        random.shuffle(shuffled)
        split = max(1, int(len(shuffled) * 0.85))

        for split_name, imgs in [("train", shuffled[:split]),
                                  ("val", shuffled[split:])]:
            img_dest = os.path.join(data_dir, split_name, "images")
            lbl_dest = os.path.join(data_dir, split_name, "labels")
            os.makedirs(img_dest, exist_ok=True)
            os.makedirs(lbl_dest, exist_ok=True)
            for idx, img_path in enumerate(imgs):
                ext = os.path.splitext(img_path)[1]
                shutil.copy2(img_path,
                             os.path.join(img_dest, f"img_{idx:05d}{ext}"))
                lbl_src = get_label_path(img_path)
                shutil.copy2(lbl_src,
                             os.path.join(lbl_dest, f"img_{idx:05d}.txt"))

        yaml_path = os.path.join(data_dir, "data.yaml")
        with open(yaml_path, "w") as f:
            yaml.dump({
                "path": os.path.abspath(data_dir),
                "train": "train/images",
                "val": "val/images",
                "nc": 1,
                "names": ["bolt"],
            }, f)

        # 학습 — 결과를 버전 폴더에 직접 저장
        model = YOLO("yolov8n-seg.pt")
        model.train(
            data=yaml_path,
            epochs=100,
            imgsz=640,
            batch=16,
            project=version_dir,
            name="train",
            patience=20,
            verbose=True,
        )

        # best.pt를 버전 폴더 루트에 복사
        train_best = os.path.join(version_dir, "train", "weights", "best.pt")
        if not os.path.exists(train_best):
            # YOLO가 train2 등으로 만들 수 있으니 검색
            candidates = sorted(
                glob.glob(os.path.join(version_dir, "train*", "weights", "best.pt")),
                key=os.path.getmtime)
            if candidates:
                train_best = candidates[-1]

        if os.path.exists(train_best):
            dest = os.path.join(version_dir, "best.pt")
            shutil.copy2(train_best, dest)

            # 학습 정보 저장
            info = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": f"{today}_v{version}",
                "positive": positive,
                "negative": negative,
                "total_images": len(all_labeled),
                "source_folder": os.path.dirname(self.images[0]),
            }
            with open(os.path.join(version_dir, "info.txt"), "w") as f:
                for k, v in info.items():
                    f.write(f"{k}: {v}\n")

            print(f"\n{'=' * 50}")
            print(f"  학습 완료!")
            print(f"{'=' * 50}")
            print(f"  모델 저장: {dest}")
            print(f"  버전: {today}_v{version}")
            print(f"{'=' * 50}")

            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(
                "학습 완료",
                f"모델 저장 위치:\n{dest}\n\n"
                f"버전: {today}_v{version}\n"
                f"학습 데이터: {positive}장 + 네거티브 {negative}장"
            )
            root.destroy()
        else:
            print("[ERROR] 학습 결과 best.pt를 찾을 수 없음")


# ═══════════════════════════════════════════════════════════
#  3. 모델 테스트 (카메라 실행)
# ═══════════════════════════════════════════════════════════

class ModelTester:
    """best.pt 선택 → RealSense 카메라로 실시간 감지 테스트"""

    def __init__(self, workspace):
        self.workspace = workspace

    def run(self):
        from ultralytics import YOLO
        import pyrealsense2 as rs

        # 모델 파일 선택 — 작업폴더/models/ 에서 시작
        root = tk.Tk()
        root.withdraw()
        model_path = filedialog.askopenfilename(
            title="모델 파일 선택 (best.pt)",
            initialdir=os.path.join(self.workspace, "models"),
            filetypes=[("PyTorch Model", "*.pt"), ("모든 파일", "*.*")],
        )
        root.destroy()

        if not model_path:
            print("[테스트] 취소됨")
            return

        print(f"\n[테스트] 모델: {model_path}")
        model = YOLO(model_path)

        # RealSense 초기화
        print("[테스트] 카메라 초기화...")
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        pipeline.start(config)

        for _ in range(30):
            pipeline.wait_for_frames()

        cv2.namedWindow("Model Test", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Model Test", *WINDOW_SIZE)

        print("[테스트] 실행 중... (Q: 종료)")
        fps_time = time.time()

        while True:
            frames = pipeline.wait_for_frames()
            color = np.asanyarray(frames.get_color_frame().get_data())
            vis = color.copy()

            # YOLO 감지
            results = model(color, conf=0.5, verbose=False)

            # 결과 시각화
            n_detected = 0
            if results[0].boxes is not None:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0])
                    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(vis, f"{conf:.2f}", (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    n_detected += 1

            # 세그멘테이션 마스크 오버레이
            if results[0].masks is not None:
                for mask in results[0].masks:
                    xy = mask.xy[0]
                    if len(xy) >= 3:
                        pts = np.array(xy, dtype=np.int32)
                        overlay = vis.copy()
                        cv2.fillPoly(overlay, [pts], (0, 255, 0))
                        cv2.addWeighted(overlay, 0.3, vis, 0.7, 0, vis)
                        cv2.polylines(vis, [pts], True, (0, 255, 0), 2)

            # FPS
            now = time.time()
            fps = 1.0 / max(now - fps_time, 0.001)
            fps_time = now

            cv2.putText(vis, f"Detected: {n_detected} | FPS: {fps:.0f}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(vis, f"Model: {os.path.basename(model_path)}",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(vis, "Q: Quit", (10, color.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            cv2.imshow("Model Test", vis)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        pipeline.stop()
        cv2.destroyAllWindows()
        print("[테스트] 종료")


# ═══════════════════════════════════════════════════════════
#  메인 메뉴
# ═══════════════════════════════════════════════════════════

def main():
    # 작업 폴더 선택
    workspace = get_workspace()
    if not workspace:
        print("작업 폴더를 선택하지 않았습니다.")
        return

    print(f"\n[작업 폴더] {workspace}")
    print(f"  사진: {workspace}/photos/")
    print(f"  모델: {workspace}/models/")
    print()

    root = tk.Tk()
    root.title("볼트 라벨링 프로그램")
    root.geometry("400x350")
    root.resizable(False, False)

    # 스타일
    style = ttk.Style()
    style.configure("Big.TButton", font=("맑은 고딕", 14), padding=15)

    # 제목
    title = tk.Label(root, text="볼트 라벨링 프로그램",
                     font=("맑은 고딕", 16, "bold"))
    title.pack(pady=10)

    # 작업 폴더 표시
    ws_label = tk.Label(root, text=f"작업 폴더: {workspace}",
                        font=("맑은 고딕", 9), fg="gray")
    ws_label.pack(pady=2)

    # 버튼 프레임
    frame = tk.Frame(root)
    frame.pack(pady=10)

    def on_photo():
        root.withdraw()
        PhotoMaker(workspace).run()
        root.deiconify()

    def on_label():
        root.withdraw()
        Labeler(workspace).run()
        root.deiconify()

    def on_test():
        root.withdraw()
        ModelTester(workspace).run()
        root.deiconify()

    btn_photo = ttk.Button(frame, text="1. 사진만들기",
                           style="Big.TButton", command=on_photo)
    btn_photo.pack(fill=tk.X, pady=4, padx=20)

    btn_label = ttk.Button(frame, text="2. 라벨링하기",
                           style="Big.TButton", command=on_label)
    btn_label.pack(fill=tk.X, pady=4, padx=20)

    btn_test = ttk.Button(frame, text="3. 모델 테스트",
                          style="Big.TButton", command=on_test)
    btn_test.pack(fill=tk.X, pady=4, padx=20)

    btn_quit = ttk.Button(frame, text="종료", command=root.quit)
    btn_quit.pack(fill=tk.X, pady=10, padx=20)

    root.mainloop()


if __name__ == "__main__":
    main()
