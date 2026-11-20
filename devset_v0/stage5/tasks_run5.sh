#!/bin/bash
# 階段 5：每個模型 8 條件 × 3 順序。用法：tasks_run5.sh NAME PORT QWEN。先 smoke（2 query × 2 情境 × 8 條件）。
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval/devset_v0/stage5
NAME=$1; PORT=$2; QWEN=$3; URL=http://127.0.0.1:$PORT/v1/chat/completions; NT=(); [ "$QWEN" = 1 ] && NT=(--no-think)
short=${NAME%-devset5}
[ "$short" = llavaov2-8b ] && export IMG_MAX=560
if [ ! -f logs/smoke_done_$short ]; then
  rm -f out/$short/select_smoke_*.jsonl
  python3 -I run_caption.py --model $NAME --url $URL --orders o0 --limit-queries 2 --tag _smoke "${NT[@]}" > logs/smoke_$short.out 2>&1
  python3 -I - $short <<'P' || exit 3
import json,sys,glob,time
rs=[json.loads(l) for f in glob.glob(f'out/{sys.argv[1]}/select_smoke_*_o0.jsonl') for l in open(f)]
pt=[(r['usage'] or {}).get('prompt_tokens',0) for r in rs]; mx=max(pt); ok=sum(r['status']=='ok' for r in rs)
img_ok=all((r['has_image']==1)==(r['condition']=='img_goldstyle') and (r['has_image'] in (0,1)) for r in rs)
open('PROGRESS.md','a').write(f"[{time.strftime('%F %H:%M',time.gmtime())}] smoke {sys.argv[1]} — {len(rs)} 筆（應 32），解析成功 {ok}，prompt tokens 最大 {mx}（+512 = {mx+512}，上限 16384），cap_* 無參考圖檢查 {'通過' if img_ok else '失敗'}\n")
sys.exit(0 if ok==len(rs) and len(rs)==32 and mx+512<=16384 and img_ok else 1)
P
  [ $? -eq 0 ] || exit 3
  touch logs/smoke_done_$short
fi
python3 -I run_caption.py --model $NAME --url $URL "${NT[@]}" || exit 1
