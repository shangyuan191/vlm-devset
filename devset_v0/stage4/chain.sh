#!/usr/bin/env bash
# 夜間串接：等階段 3 完成 → Opus 審查（stage3/OPUS_REVIEW.md）→ 審查通過才啟動階段 4（Sonnet）。
set -u
unset ALL_PROXY HTTPS_PROXY HTTP_PROXY all_proxy http_proxy https_proxy
R=/mnt/raid0/home/skyler/vlm-diverse-retrieval; T=$R/devset_v0/stage3; U=$R/devset_v0/stage4; LOG=$U/chain.log
cd $R
log(){ echo "[$(date -u)] $*" >> $LOG; }
watcher_running(){ pgrep -u skyler -f "^bash (.*/)?$(basename $1)/watch.sh" >/dev/null; }
log "chain start"
# 1. 等階段 3（看守程式結束）；沒寫 ALL DONE 就重啟看守程式，最多 2 次
for k in 0 1 2; do
  while watcher_running $T; do sleep 300; done
  grep -q "ALL DONE" $T/PROGRESS.md && break
  [ $k -lt 2 ] && { log "stage3 watcher exited without ALL DONE; relaunch $((k+1))"; (cd $R && setsid nohup bash devset_v0/stage3/watch.sh >/dev/null 2>&1 &); sleep 60; }
done
grep -q "ALL DONE" $T/PROGRESS.md && log "stage3 ALL DONE" || log "stage3 NOT done; reviewing anyway"
# 2. Opus 審查（碰到用量上限就睡到重置）
SID=$(cat $U/review_session_id 2>/dev/null || { uuidgen | tee $U/review_session_id; })
for i in $(seq 1 15); do
  tail -1 $T/OPUS_REVIEW.md 2>/dev/null | grep -qE "REVIEW (DONE|BLOCK)" && break
  start=$(stat -c %s $U/review_stream.jsonl 2>/dev/null || echo 0)
  log "review run $i"
  if [ ! -s $U/review_stream.jsonl ]; then
    claude -p "請完整閱讀並遵守 $U/REVIEW_PROMPT.md，然後開始審查。現在時間 $(date -u '+%F %H:%M') UTC。" --session-id "$SID" \
      --model opus --permission-mode auto --output-format stream-json --verbose < /dev/null >> $U/review_stream.jsonl 2>> $U/review_stderr.log
  else
    claude -p "你剛才被中斷了。現在時間 $(date -u '+%F %H:%M') UTC。請重讀 $U/REVIEW_PROMPT.md，從中斷處繼續，直到 $T/OPUS_REVIEW.md 最後一行寫上 REVIEW DONE 或 REVIEW BLOCK。" --resume "$SID" \
      --model opus --permission-mode auto --output-format stream-json --verbose < /dev/null >> $U/review_stream.jsonl 2>> $U/review_stderr.log
  fi
  last=$(tail -c +$((start+1)) $U/review_stream.jsonl | grep '"type":"result"' | tail -1 | python3 -c 'import sys,json
l=sys.stdin.read().strip(); print(json.loads(l).get("result","") if l else "")' 2>/dev/null)
  if echo "$last" | grep -qi "hit your.*limit"; then
    rt=$(echo "$last" | grep -oiE 'resets [0-9]{1,2}(:[0-9]{2})?(am|pm)' | sed 's/resets //I'); now=$(date -u +%s)
    tgt=$(date -u -d "$rt" +%s 2>/dev/null || echo $((now+1800))); [ "$tgt" -le "$now" ] && tgt=$((tgt+86400))
    log "usage limit; sleeping $((tgt-now+120))s"; sleep $((tgt-now+120)); continue
  fi
  sleep 60
done
# 3. 審查通過才啟動階段 4
if tail -1 $T/OPUS_REVIEW.md 2>/dev/null | grep -q "REVIEW DONE"; then
  log "review DONE; launching stage4"; cd $R && setsid nohup bash devset_v0/stage4/watch.sh >/dev/null 2>&1 &
else
  log "review BLOCK or missing; stage4 NOT launched"
fi
log "chain finished"
