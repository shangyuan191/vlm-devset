#!/bin/bash
# 單一模型背景工作。用法：job3.sh SHORT TASK_SCRIPT TAG   完成 → logs/done_<TAG>_SHORT
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
D=devset_v0/stage4; short=$1; export TASK_SCRIPT=$2; tag=$3
#        short              model                                       need  tp port qwen  extra
CFG="
qwen38-27b        models/Qwen3.8-27B-FP8                 20000 2 8101 1 -
gemma4-12b        models/gemma-4-12b-it                  18000 2 8102 0 -
qwen36-35b        models/Qwen3.6-35B-A3B-FP8             22000 2 8103 1 -
internvl35-1tile  models/InternVL3_5-8B-1tile            24000 1 8104 0 --trust-remote-code
llavaov2-8b       models/LLaVA-OneVision-2-8B-Instruct   24000 1 8105 0 --trust-remote-code
qwen35-9b         models/Qwen3.5-9B                      24000 1 8106 1 -
qwen35-4b         Qwen/Qwen3.5-4B                        18000 1 8107 1 -
"
read -r _ model need tp port qwen extra <<< "$(echo "$CFG" | awk -v s=$short '$1==s')"
[ -z "$model" ] && { echo "unknown $short"; exit 1; }
[ -f $D/logs/done_${tag}_$short ] && exit 0
EX=(); [ "$extra" != - ] && IFS=',' read -ra EX <<< "$extra"
envs=(WAIT_MIN=${WAIT_MIN:-240})
[ $short = llavaov2-8b ] && envs+=(VLLM_WORKER_MULTIPROC_METHOD=fork)
prog() { echo "[$(date -u '+%F %H:%M')] $tag/$short — $1" >> $D/PROGRESS.md; }
prog "等卡並啟動 vLLM（NEED $need × TP $tp，port $port，嘗試 ${ATTEMPT:-1}）"
env "${envs[@]}" bash $D/serve_devset4.sh $model $short-devset4 $need $tp $port $qwen "${EX[@]}" >> $D/logs/serve_${tag}_$short.log 2>&1
rc=$?
if [ $rc -eq 0 ]; then touch $D/logs/done_${tag}_$short; prog "完成，server 已關"
else prog "結束 exit $rc（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）"; fi
exit $rc
