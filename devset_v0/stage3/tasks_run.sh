#!/bin/bash
# C 節：風格判斷 + 選品 img + style_given。用法：tasks_run.sh NAME PORT QWEN。第一個模型先跑 smoke（logs/smoke_done_$short 不存在時）。
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval/devset_v0/stage3
NAME=$1; PORT=$2; QWEN=$3; URL=http://127.0.0.1:$PORT/v1/chat/completions; NT=(); [ "$QWEN" = 1 ] && NT=(--no-think)
short=${NAME%-devset3}
[ "$short" = llavaov2-8b ] && export IMG_MAX=560
if [ ! -f logs/smoke_done_$short ]; then
  python3 -I run_select.py --model $NAME --url $URL --condition img --orders o0 --limit-queries 5 --tag _smoke "${NT[@]}" > logs/smoke_$short.out 2>&1
  python3 -I - $short <<'P' || exit 3
import json,sys
rs=[json.loads(l) for l in open(f'out/{sys.argv[1]}/select_smoke_img_o0.jsonl')]
mx=max((r['usage'] or {}).get('prompt_tokens',0) for r in rs); ok=sum(r['status']=='ok' for r in rs)
open('PROGRESS.md','a').write(f"[{__import__('time').strftime('%F %H:%M',__import__('time').gmtime())}] C/smoke {sys.argv[1]} — {len(rs)} 題 × 1 順序，解析成功 {ok}，prompt tokens 最大 {mx}、最小 {min((r['usage'] or {}).get('prompt_tokens',0) for r in rs)}\n")
sys.exit(0 if ok==len(rs) and mx<16384 else 1)
P
  [ $? -eq 0 ] || exit 3
  touch logs/smoke_done_$short
fi
python3 -I run_style.py --model $NAME --url $URL "${NT[@]}" || exit 1
python3 -I run_select.py --model $NAME --url $URL --condition img "${NT[@]}" || exit 1
python3 -I run_select.py --model $NAME --url $URL --condition style_given "${NT[@]}" || exit 1
