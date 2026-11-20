#!/bin/bash
# 7 個模型各一個背景迴圈（失敗最多重試 3 次；每張卡最多一個 server 由 serve_devset4.sh 的 gpu_claims 控制）。
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
for m in qwen38-27b gemma4-12b qwen36-35b qwen35-9b internvl35-1tile llavaov2-8b qwen35-4b; do
  ( for a in 1 2 3 4; do ATTEMPT=$a bash devset_v0/stage4/job4.sh $m tasks_run4.sh C && break; sleep 120; done ) >/dev/null 2>&1 &
  sleep 20
done
