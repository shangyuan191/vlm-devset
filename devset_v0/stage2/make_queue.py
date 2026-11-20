"""3.1 準備：建 queue.jsonl = 27 格中每格還沒標過的商品（pool 的格子部分扣掉 stage1/sample.jsonl 的 parent_asin），
每格依 random.Random('0-stage2-<cell>').shuffle(依 parent_asin 排序的清單) 排序。結果固定；已存在就不重建。
用法： python3 -I devset_v0/stage2/make_queue.py
"""
import collections
import json
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common2 import S, D, S1, CELLS, read_jsonl  # noqa: E402

out = S / 'queue.jsonl'
if out.exists():
    print('queue.jsonl exists; skip'); sys.exit(0)
seen = {r['parent_asin'] for r in read_jsonl(S1 / 'sample.jsonl')}
cells = collections.defaultdict(list)
for p in read_jsonl(D / 'stage0' / 'pool.jsonl'):
    if not p['distractor'] and p['cell'] in CELLS and p['parent_asin'] not in seen:
        cells[p['cell']].append(p)
n = {}
with open(out, 'w', encoding='utf-8') as f:
    for c in CELLS:
        rows = sorted(cells[c], key=lambda p: p['parent_asin'])
        random.Random(f'0-stage2-{c}').shuffle(rows)
        n[c] = len(rows)
        for k, p in enumerate(rows):
            f.write(json.dumps({'cell': c, 'qpos': k, **{x: p[x] for x in ('parent_asin', 'item', 'kw_style', 'title', 'store', 'source', 'categories', 'image_path', 'sha256')}}, ensure_ascii=False) + '\n')
json.dump(n, open(S / 'queue_counts.json', 'w'), indent=1)
print(sum(n.values()), 'queued;', n)
