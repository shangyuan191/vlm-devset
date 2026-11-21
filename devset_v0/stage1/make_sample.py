"""階段 1 抽樣：每格從商品池隨機抽 30 件（seed 0；不足全取）→ sample.jsonl；並做 768 px 標註用縮圖 img768/<id>.jpg。

id（item_0001…）依全體打亂後的順序編號（seed 0），所以 id 與檔名不透露格子，連續 20 個 id 就是一批跨格混合的商品。
用法： R/.venv/bin/python -B make_sample.py   （結果固定；已存在的縮圖會重做成相同內容）
"""
import collections, json, random
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
N, SEED, LONG = 30, 0, 768
pool = [json.loads(l) for l in open(HERE.parent / 'stage0' / 'pool.jsonl')]
cells = collections.defaultdict(list)
for p in pool:
    cells[p['cell']].append(p)
picked, short = [], {}
for c in sorted(cells):
    rows = sorted(cells[c], key=lambda p: p['parent_asin'])
    k = min(N, len(rows))
    if k < N:
        short[c] = k
    picked += random.Random(f'{SEED}-sample-{c}').sample(rows, k)
random.Random(f'{SEED}-order').shuffle(picked)
(HERE / 'img768').mkdir(exist_ok=True)
with open(HERE / 'sample.jsonl', 'w', encoding='utf-8') as f:
    for i, p in enumerate(picked, 1):
        iid = f'item_{i:04d}'
        im = Image.open(R / p['image_path'])
        if im.mode != 'RGB':
            bg = Image.new('RGB', im.size, 'white'); im = im.convert('RGBA'); bg.paste(im, mask=im.split()[3]); im = bg
        if max(im.size) > LONG:
            s = LONG / max(im.size); im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        im.save(HERE / 'img768' / f'{iid}.jpg', 'JPEG', quality=90)
        f.write(json.dumps({'id': iid, 'ann_image': f'img768/{iid}.jpg', 'ann_wh': list(im.size), 'batch': (i - 1) // 20 + 1,
                            **{k: p[k] for k in ('parent_asin', 'cell', 'item', 'kw_style', 'title', 'store', 'source', 'categories', 'image_path', 'sha256')}},
                           ensure_ascii=False) + '\n')
print(len(picked), 'sampled; cells short of 30:', short)
