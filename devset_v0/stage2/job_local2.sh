#!/bin/bash
# 一個本地標註者的背景工作：等卡 → 啟動 vLLM → 標 sample.jsonl → 關 server。完成 → logs/done_SHORT
# 用法：job_local.sh qwen38-27b|gemma4-12b
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
D=devset_v0/stage2; short=$1
case $short in
  qwen38-27b) model=models/Qwen3.8-27B-FP8; need=20000; tp=2; port=8081; qwen=1;;
  gemma4-12b) model=models/gemma-4-12b-it;  need=18000; tp=2; port=8082; qwen=0;;
  *) echo "unknown $short"; exit 1;;
esac
[ -f $D/logs/done_$short ] && exit 0
prog() { echo "[$(date -u '+%F %H:%M')] 階段2/$short — $1" >> $D/PROGRESS.md; }
prog "等卡並啟動 vLLM（NEED $need MB × $tp 張，port $port，嘗試 ${ATTEMPT:-1}）"
bash $D/serve_devset2.sh $model $short-devset2 $need $tp $port $qwen >> $D/logs/serve_$short.log 2>&1
rc=$?
if [ $rc -eq 0 ]; then touch $D/logs/done_$short; prog "標註完成，server 已關"
else prog "結束 exit $rc（2 = 等卡超過 4 小時；1 = 啟動或標註中斷）"; fi
exit $rc
