#!/bin/bash
# ============================================================
#  학습서버에서 share 마운트된 workspace 학습
# ============================================================
#
# 사용 전 확인:
#   - /mnt/share 가 마운트돼 있어야 함 (WORKFLOW.md 의 cifs 마운트 참조)
#   - ~/labeler 에 git clone + setup_linux.sh 완료 상태
#
# 사용법:
#   ./bolt_train.sh                     # 기본 (epoch 100)
#   ./bolt_train.sh --epochs 200        # 커스텀
# ============================================================

WORKSPACE=/mnt/share/matthew/boltwork
LABELER=$HOME/labeler

if [ ! -d "$WORKSPACE/photos" ]; then
    echo "[ERROR] $WORKSPACE/photos 폴더가 없습니다."
    echo "촬영 PC에서 먼저 push_photos.bat 를 실행했는지 확인하세요."
    exit 1
fi

if [ ! -f "$LABELER/venv/bin/activate" ]; then
    echo "[ERROR] $LABELER/venv 가 없습니다."
    echo "먼저 git clone https://github.com/Dongju3079/labeler.git && cd labeler && ./setup_linux.sh"
    exit 1
fi

source "$LABELER/venv/bin/activate"

echo ""
echo "=========================================="
echo "  BoltLabeler 학습 시작"
echo "=========================================="
echo "  workspace: $WORKSPACE"
echo "  args:      $@"
echo ""

python "$LABELER/train_only.py" "$WORKSPACE" "$@"

echo ""
echo "=========================================="
echo "  학습 완료"
echo "=========================================="
echo "best.pt 가 $WORKSPACE/models/<날짜_v버전>/ 에 저장됐습니다."
echo "촬영 PC에서 pull_models.bat 를 실행하면 회수됩니다."
