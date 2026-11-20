#!/usr/bin/env bash
# 開發集 v0 階段 2 agent 的看守程式：碰到用量上限就睡到重置時間；其他原因中斷最多重試 5 次。
set -u
unset ALL_PROXY HTTPS_PROXY HTTP_PROXY all_proxy http_proxy https_proxy
D=/mnt/raid0/home/skyler/vlm-diverse-retrieval/devset_v0/stage3; cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
SID=$(cat "$D/session_id" 2>/dev/null || { uuidgen | tee "$D/session_id"; }); LOG="$D/launcher.log"; fails=0
for i in $(seq 1 40); do
  grep -q "ALL DONE" "$D/PROGRESS.md" 2>/dev/null && { echo "[$(date -u)] ALL DONE" >> "$LOG"; break; }
  start=$(stat -c %s "$D/agent_stream.jsonl" 2>/dev/null || echo 0)
  echo "[$(date -u)] run $i" >> "$LOG"
  if [ $i -eq 1 ] && [ ! -s "$D/agent_stream.jsonl" ]; then
    claude -p "請完整閱讀並遵守 $D/RUNBOOK.md，然後開始工作。現在時間 $(date -u '+%F %H:%M') UTC。" --session-id "$SID" \
      --model sonnet --permission-mode auto --output-format stream-json --verbose < /dev/null >> "$D/agent_stream.jsonl" 2>> "$D/agent_stderr.log"
  else
    claude -p "你剛才被中斷了。現在時間 $(date -u '+%F %H:%M') UTC。請重讀 $D/RUNBOOK.md、PROGRESS.md、DECISIONS.md，從中斷處繼續，直到 PROGRESS.md 寫上 ALL DONE。" --resume "$SID" \
      --model sonnet --permission-mode auto --output-format stream-json --verbose < /dev/null >> "$D/agent_stream.jsonl" 2>> "$D/agent_stderr.log"
  fi
  echo "[$(date -u)] run $i exited code $?" >> "$LOG"
  last=$(tail -c +$((start+1)) "$D/agent_stream.jsonl" | grep '"type":"result"' | tail -1 | python3 -c 'import sys,json
l=sys.stdin.read().strip(); print(json.loads(l).get("result","") if l else "")' 2>/dev/null)
  if echo "$last" | grep -qi "hit your.*limit"; then
    rt=$(echo "$last" | grep -oiE 'resets [0-9]{1,2}(:[0-9]{2})?(am|pm)' | sed 's/resets //I'); now=$(date -u +%s)
    tgt=$(date -u -d "$rt" +%s 2>/dev/null || echo $((now+1800))); [ "$tgt" -le "$now" ] && tgt=$((tgt+86400))
    echo "[$(date -u)] usage limit; sleeping $((tgt-now+120))s" >> "$LOG"; sleep $((tgt-now+120)); continue
  fi
  fails=$((fails+1)); [ $fails -ge 5 ] && { echo "[$(date -u)] 5 non-limit exits, stop" >> "$LOG"; break; }
  sleep 60
done
pkill -u skyler -f "vllm serve .*--served-model-name [^ ]*-devset3" 2>/dev/null
echo "[$(date -u)] watcher finished" >> "$LOG"
