#!/bin/bash
# 接續階段 4 的模型工作（已完成的題目會自動跳過）。
# 用法：bash devset_v0/stage4/resume.sh            → 只用 GPU 0 1 3（預設，避開 GPU 4 = admin 的 CUDA 3）
#       GPUS="0 1 3 4" bash devset_v0/stage4/resume.sh → 允許再用 GPU 4
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
export GPUS="${GPUS:-0 1 3}"
setsid nohup bash devset_v0/stage4/relaunch.sh >/dev/null 2>&1 &
echo "已重新排隊（GPUS=$GPUS）"
