#!/bin/bash
# 補跑：對還沒有 done_C_<模型> 的模型重新排隊（job4.sh 會跳過已完成者）。已有同模型 job 在跑時不重複啟動。
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
for m in qwen38-27b gemma4-12b qwen36-35b qwen35-9b internvl35-1tile llavaov2-8b qwen35-4b; do
  [ -f devset_v0/stage4/logs/done_C_$m ] && continue
  pgrep -u $USER -f "stage4/job4.sh $m " >/dev/null && continue
  pgrep -u $USER -f -- "--served-model-name $m-devset4" >/dev/null && continue
  ( for a in 1 2 3 4 5 6; do ATTEMPT=$a bash devset_v0/stage4/job4.sh $m tasks_run4.sh C && break; sleep 120; done ) >/dev/null 2>&1 &
  sleep 15
done
