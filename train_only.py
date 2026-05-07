"""
학습 전용 스크립트 (헤드리스 - GUI 없음)

용도:
  PC에서 라벨링 끝낸 workspace 폴더를 학습서버로 옮긴 뒤
  서버에서 학습만 돌릴 때 사용.

사용법:
  python train_only.py /path/to/workspace
  python train_only.py /path/to/workspace --epochs 200 --batch 32

결과:
  workspace/models/YYYYMMDD_vN/best.pt  생성
"""

import os
import sys
import glob
import shutil
import random
import argparse
import yaml
from datetime import datetime


def get_label_path(img_path):
    """이미지 경로 -> 같은 폴더의 .txt 라벨 경로"""
    return os.path.splitext(img_path)[0] + ".txt"


def main():
    parser = argparse.ArgumentParser(description="BoltLabeler 학습 전용 스크립트")
    parser.add_argument("workspace", help="작업 폴더 경로 (photos/ 가 있는 곳)")
    parser.add_argument("--epochs", type=int, default=100, help="학습 에폭 (기본 100)")
    parser.add_argument("--batch", type=int, default=16, help="배치 크기 (기본 16)")
    parser.add_argument("--imgsz", type=int, default=640, help="이미지 크기 (기본 640)")
    parser.add_argument("--patience", type=int, default=20, help="EarlyStopping patience (기본 20)")
    parser.add_argument("--base-model", default="yolov8n-seg.pt",
                        help="베이스 모델 (기본 yolov8n-seg.pt)")
    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    photos_dir = os.path.join(workspace, "photos")

    if not os.path.isdir(photos_dir):
        print(f"[ERROR] photos 폴더가 없습니다: {photos_dir}")
        sys.exit(1)

    # 라이브러리는 인자 검증 후 import (기동 빠르게)
    from ultralytics import YOLO

    # 라벨 있는 이미지 수집 (볼트 + 네거티브)
    img_exts = (".jpg", ".jpeg", ".png", ".bmp")
    all_images = sorted([
        os.path.join(photos_dir, f) for f in os.listdir(photos_dir)
        if f.lower().endswith(img_exts)
    ])

    all_labeled = []
    positive = 0
    negative = 0
    for p in all_images:
        lbl = get_label_path(p)
        if os.path.exists(lbl):
            all_labeled.append(p)
            # 빈 파일이면 네거티브, 내용 있으면 포지티브
            if os.path.getsize(lbl) > 0:
                positive += 1
            else:
                negative += 1

    if positive < 10:
        print(f"[학습 불가] 라벨된 볼트 이미지가 최소 10장 필요 (현재 {positive}장)")
        sys.exit(1)

    # 버전 폴더 생성: models/YYYYMMDD_vN/
    models_dir = os.path.join(workspace, "models")
    os.makedirs(models_dir, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    existing = glob.glob(os.path.join(models_dir, f"{today}_v*"))
    version = len(existing) + 1
    version_dir = os.path.join(models_dir, f"{today}_v{version}")
    os.makedirs(version_dir, exist_ok=True)

    print(f"\n{'=' * 50}")
    print(f"  학습 시작 (헤드리스)")
    print(f"{'=' * 50}")
    print(f"  작업 폴더:    {workspace}")
    print(f"  볼트 이미지:  {positive}장")
    print(f"  네거티브:     {negative}장")
    print(f"  버전 폴더:    {version_dir}")
    print(f"  에폭:         {args.epochs}")
    print(f"  배치:         {args.batch}")
    print(f"{'=' * 50}\n")

    # 데이터셋 구성 (85:15 split, seed 고정)
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
            shutil.copy2(img_path, os.path.join(img_dest, f"img_{idx:05d}{ext}"))
            shutil.copy2(get_label_path(img_path),
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

    # 학습
    model = YOLO(args.base_model)
    model.train(
        data=yaml_path,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=version_dir,
        name="train",
        patience=args.patience,
        verbose=True,
    )

    # best.pt 를 버전 폴더 루트로 복사
    train_best = os.path.join(version_dir, "train", "weights", "best.pt")
    if not os.path.exists(train_best):
        candidates = sorted(
            glob.glob(os.path.join(version_dir, "train*", "weights", "best.pt")),
            key=os.path.getmtime)
        if candidates:
            train_best = candidates[-1]

    if os.path.exists(train_best):
        dest = os.path.join(version_dir, "best.pt")
        shutil.copy2(train_best, dest)

        info = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": f"{today}_v{version}",
            "positive": positive,
            "negative": negative,
            "total_images": len(all_labeled),
            "epochs": args.epochs,
            "batch": args.batch,
            "imgsz": args.imgsz,
            "host": os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "?"),
        }
        with open(os.path.join(version_dir, "info.txt"), "w") as f:
            for k, v in info.items():
                f.write(f"{k}: {v}\n")

        print(f"\n{'=' * 50}")
        print(f"  학습 완료")
        print(f"{'=' * 50}")
        print(f"  best.pt:  {dest}")
        print(f"  버전:     {today}_v{version}")
        print(f"{'=' * 50}")
        print(f"\nPC로 회수하려면 (서버에서 실행):")
        print(f"  scp {dest} user@PC주소:/path/to/workspace/models/{today}_v{version}/")
        print(f"또는 PC에서 (PC에서 실행):")
        print(f"  rsync -av server:{version_dir}/best.pt /path/to/workspace/models/{today}_v{version}/")
    else:
        print("[ERROR] best.pt 를 찾을 수 없음")
        sys.exit(1)


if __name__ == "__main__":
    main()
