#!/bin/bash
# A 節：本地標註者（沿用 stage2/annotate_local2.py，寫入 stage2/ann_<short>.jsonl）。用法：tasks_annot.sh NAME PORT QWEN
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
NAME=$1; PORT=$2; QWEN=$3; NT=(); [ "$QWEN" = 1 ] && NT=(--no-think)
python3 -I devset_v0/stage2/annotate_local2.py --model $NAME --url http://127.0.0.1:$PORT/v1/chat/completions --out ann_${NAME%-devset3}.jsonl "${NT[@]}"
