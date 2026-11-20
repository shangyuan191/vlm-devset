#!/bin/bash
# 開發集 v0 階段 2 的 vLLM 啟動器（複製自 stage1/serve_devset.sh；served name 結尾 -devset5；沒有 pkill -f，只 kill 記下的 PID）。原說明：（複製自 overnight_2026-11-16/serve_model.sh，原檔未改）。
# 差別：served name 以 -devset5 結尾、port 8111–8119、等卡上限 240 分鐘、lock 檔唯讀開啟、啟動後跑 stage1/annotate_local.py。
# 規則沿用：
#  1. 只看 GPUS（預設 5090：0 1 3 4）；某卡連續 7 次（約 60 秒）空閒 >= NEED_MB 才算可用。TP>1 時要同時有 TP 張這樣的卡。
#  2. 拿到 scripts/.vllm_start.lock（flock）後再確認一次空閒記憶體才啟動。
#  3. --gpu-memory-utilization = NEED_MB / 該卡總記憶體。
#  4. HF_HUB_OFFLINE=1；TP>1 時 NCCL_P2P_DISABLE=1。
#  5. trap 確保結束時 kill 自己的 vLLM（served-model-name 含 smoke_2026-11-15）。
# 啟動成功後執行 tasks.sh（pilot2 / ladder / chain），結束後關 server。
# 用法：serve_one.sh MODEL NAME NEED_MB TP PORT QWEN(0/1) [額外 vLLM 參數...]
set -u
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
D=devset_v0/stage5
MODEL=$1; NAME=$2; NEED=$3; TP=$4; PORT=$5; QWEN=$6; shift 6; EXTRA=("$@")
[[ "$NAME" == *-devset5 ]] || { echo "RESULT: NAME must end with -devset5"; exit 1; }
[ "$PORT" = auto ] || { [ "$PORT" -ge 8111 ] && [ "$PORT" -le 8119 ]; } || { echo "RESULT: port must be 8111-8119 or auto"; exit 1; }
# 11/15 規則更新：可平行跑多個自己的 server，但一張 GPU 最多 1 個。gpu_claims/<idx> 記錄哪張卡被哪個模型佔用。
CLAIMS=$PWD/devset_v0/stage5/gpu_claims; mkdir -p $CLAIMS
pgrep -u $USER -f -- "--served-model-name $NAME( |$)" >/dev/null && { echo "RESULT: $NAME already running; abort"; exit 1; }
claimed() { local f=$CLAIMS/$1; [ -f $f ] || return 1; local pid; pid=$(awk '{print $2}' $f); kill -0 $pid 2>/dev/null && return 0; rm -f $f; return 1; }
WAIT_T0=$(date +%s); echo "$(date -u +%FT%T) WAIT_START $NAME NEED=$NEED TP=$TP"
GPUS=" ${GPUS:-0 1 3 4} "; WAIT_MIN=${WAIT_MIN:-240}
MARGIN=${MARGIN:-1500}  # vLLM 自己的 CUDA context 約 1 GB 不算在 util 內，空閒判斷要多留
ENV=$HOME/miniforge3/envs/adl_hw3_py311/bin
mkdir -p $D/logs $D/raw; LOG=$D/logs/vllm_${NAME}_${TAG:-try1}.log; : > $LOG
SERVER=""
release() { for g in ${sel//,/ }; do grep -q "^$NAME " $CLAIMS/$g 2>/dev/null && rm -f $CLAIMS/$g; done; }
cleanup() { release; [ -n "$SERVER" ] && { kill $SERVER 2>/dev/null; sleep 10; pkill -P $SERVER 2>/dev/null; kill -9 $SERVER 2>/dev/null; }; }
trap cleanup EXIT; trap "exit 143" INT TERM
[ "$PORT" != auto ] && ss -ltn | grep -q ":$PORT " && { echo "RESULT: port $PORT already in use; abort"; exit 1; }
AUTO_PORT=0; [ "$PORT" = auto ] && AUTO_PORT=1

free_now() { nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits | awk -F', ' -v i=$1 '$1==i{print $3-$2}'; }
total_of() { nvidia-smi --query-gpu=index,memory.total --format=csv,noheader,nounits | awk -F', ' -v i=$1 '$1==i{print $2}'; }
QWEN_ARGS=(); [ "$QWEN" = 1 ] && QWEN_ARGS=(--mm-processor-kwargs '{"max_pixels": 307200}')
TP_ENV=(); [ "$TP" -gt 1 ] && TP_ENV=(NCCL_P2P_DISABLE=1)
exec 9<scripts/.vllm_start.lock
for try in 1 2 3; do
  declare -A ok=(); sel=""; deadline=$(( $(date +%s) + WAIT_MIN * 60 ))
  while [ -z "$sel" ] && [ $(date +%s) -lt $deadline ]; do
    ready=()
    while IFS=', ' read -r idx used total; do
      [[ "$GPUS" == *" $idx "* ]] || continue
      claimed $idx && { ok[$idx]=0; continue; }
      free=$((total - used)); if [ $free -ge $((NEED + MARGIN)) ]; then ok[$idx]=$(( ${ok[$idx]:-0} + 1 )); else ok[$idx]=0; fi
      [ ${ok[$idx]} -ge 7 ] && ready+=($idx)
    done < <(nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits)
    if [ ${#ready[@]} -ge $TP ]; then
      flock 9
      good=($(for i in "${ready[@]}"; do claimed $i && continue; f=$(free_now $i); [ $f -ge $((NEED + MARGIN)) ] && echo "$f $i"; done | sort -rn | awk '{print $2}'))
      if [ ${#good[@]} -ge $TP ]; then sel=$(IFS=,; echo "${good[*]:0:$TP}"); for g in ${sel//,/ }; do echo "$NAME $$ $(date -u +%FT%T)" > $CLAIMS/$g; done
      else flock -u 9; declare -A ok=(); fi
    fi
    [ -z "$sel" ] && sleep 10
  done
  [ -z "$sel" ] && { echo "RESULT: no $TP GPU(s) with ${NEED}MB free within $WAIT_MIN min"; exit 2; }
  if [ $AUTO_PORT = 1 ]; then PORT=""; for p in 8111 8112 8113 8114 8115 8116 8117 8118 8119; do ss -ltn | grep -q ":$p " || { PORT=$p; break; }; done
    [ -z "$PORT" ] && { echo "RESULT: no free port in 8111-8119"; exit 1; }; fi
  first=${sel%%,*}; UTIL=$(python3 -c "print(round($NEED/$(total_of $first),2))")
  CMD=($ENV/vllm serve $MODEL --served-model-name $NAME --port $PORT --host 127.0.0.1 --max-num-seqs 1 --enforce-eager
       --gpu-memory-utilization $UTIL --max-model-len ${MAXLEN:-16384} --tensor-parallel-size $TP
       --limit-mm-per-prompt "{\"image\": ${LIMIT_MM:-41}}" "${QWEN_ARGS[@]}" "${EXTRA[@]}")
  echo "$(date -u +%FT%T) using GPU $sel (free $(free_now $first) MB), util $UTIL, try $try"
  echo "CMD: CUDA_VISIBLE_DEVICES=$sel HF_HUB_OFFLINE=1 ${TP_ENV[*]} ${VLLM_WORKER_MULTIPROC_METHOD:+VLLM_WORKER_MULTIPROC_METHOD=$VLLM_WORKER_MULTIPROC_METHOD} $(printf '%q ' "${CMD[@]}")" | tee $D/logs/cmd_${NAME}.txt
  : > $LOG; env HF_HUB_OFFLINE=1 PATH=$ENV:$PATH CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=$sel "${TP_ENV[@]}" "${CMD[@]}" > $LOG 2>&1 &
  SERVER=$!; T0=$(date +%s)
  until grep -q -E "Application startup complete|Engine core initialization failed|Traceback" $LOG; do sleep 5; kill -0 $SERVER 2>/dev/null || break; done
  flock -u 9
  grep -q "Application startup complete" $LOG && break
  cleanup; SERVER=""; sel=""
  if grep -q -E "Free memory on device|CUDA out of memory" $LOG && ! grep -q "No available memory for the cache blocks" $LOG; then
    echo "$(date -u +%FT%T) lost memory during startup; retry in 2 min"; sleep 120; continue; fi
  echo "RESULT: server failed to start"; grep -E "Error|error:" $LOG | grep -v "^\s*$" | tail -8; exit 1
done
grep -q "Application startup complete" $LOG || { echo "RESULT: gave up"; exit 1; }
echo "$(date -u +%FT%T) startup ok in $(( $(date +%s) - T0 ))s on GPU $sel (waited $(( T0 - WAIT_T0 ))s for GPUs incl. failed tries)"
echo "GPU_MEM_AFTER_START: $(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' ')"
bash $D/${TASK_SCRIPT:?} "$NAME" "$PORT" "$QWEN"; rc=$?
echo "$(date -u +%FT%T) RESULT: TASKS FINISHED (exit $rc)"; exit $rc
