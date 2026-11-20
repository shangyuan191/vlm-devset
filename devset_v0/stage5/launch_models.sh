#!/bin/bash
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
for m in qwen38-27b gemma4-12b qwen36-35b qwen35-9b internvl35-1tile llavaov2-8b qwen35-4b; do
  ( for a in 1 2 3 4; do ATTEMPT=$a bash devset_v0/stage5/job5.sh $m tasks_run5.sh C && break; sleep 120; done ) >/dev/null 2>&1 &
  sleep 20
done
