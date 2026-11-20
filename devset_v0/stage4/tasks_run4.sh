#!/bin/bash
# 階段 4：每個模型的請求。用法：tasks_run4.sh NAME PORT QWEN。qwen38-27b 先做合成 query（gen_syn）。第一次先 smoke。
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval/devset_v0/stage4
NAME=$1; PORT=$2; QWEN=$3; URL=http://127.0.0.1:$PORT/v1/chat/completions; NT=(); [ "$QWEN" = 1 ] && NT=(--no-think)
short=${NAME%-devset4}
[ "$short" = llavaov2-8b ] && export IMG_MAX=560
if [ "$short" = qwen38-27b ] && [ ! -f logs/query_texts_done ]; then
  python3 -I gen_syn.py --model $NAME --url $URL >> logs/gen_syn.out 2>&1 || exit 1
  touch logs/query_texts_done
  echo "[$(date -u '+%F %H:%M')] C/gen_syn — 合成 query 完成（query_texts.json）" >> PROGRESS.md
fi
if [ ! -f logs/smoke_done_$short ]; then
  python3 -I run_select4.py --model $NAME --url $URL --wording tmpl_zh --orders o0 --limit-queries 3 --tag _smoke "${NT[@]}" > logs/smoke_$short.out 2>&1
  python3 -I - $short <<'P' || exit 3
import json,sys,time
rs=[json.loads(l) for l in open(f'out/{sys.argv[1]}/select_smoke_tmpl_zh_o0.jsonl')]
pt=[(r['usage'] or {}).get('prompt_tokens',0) for r in rs]; mx=max(pt); ok=sum(r['status']=='ok' for r in rs)
open('PROGRESS.md','a').write(f"[{time.strftime('%F %H:%M',time.gmtime())}] C/smoke {sys.argv[1]} — {len(rs)} 題，解析成功 {ok}，prompt tokens 最大 {mx}（+512 = {mx+512}，上限 16384）、最小 {min(pt)}\n")
sys.exit(0 if ok==len(rs) and mx+512<=16384 else 1)
P
  [ $? -eq 0 ] || exit 3
  touch logs/smoke_done_$short
fi
python3 -I run_select4.py --model $NAME --url $URL --wording tmpl_zh --scenarios T3,T4 --orders o0,o1,o2 "${NT[@]}" || exit 1
python3 -I run_select4.py --model $NAME --url $URL --wording tmpl_en --scenarios S1,S2,T3,T4 --orders o0 "${NT[@]}" || exit 1
# 合成 query 還沒好就先離開、釋放 GPU（避免佔著卡讓 qwen38-27b 等不到卡）；job 重試時會從這裡續跑
if [ ! -f logs/query_texts_done ]; then echo "[$(date -u '+%F %H:%M')] C/$short — tmpl_zh、tmpl_en 完成，syn_en 等合成 query（釋放 GPU）" >> PROGRESS.md; exit 4; fi
python3 -I run_select4.py --model $NAME --url $URL --wording syn_en --scenarios S1,S2,T3,T4 --orders o0 "${NT[@]}" || exit 1
