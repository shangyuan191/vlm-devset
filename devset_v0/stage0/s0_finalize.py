"""階段 0 第 4 步：算 sha256 與 pHash → pHash 去重 → 每格依序取到 300 件 → pool.jsonl、cell_counts.json。

pHash：自己用 PIL + numpy 寫（R/.venv 沒有 imagehash，不安裝套件）。做法同 imagehash.phash：
灰階 → 縮成 32×32 → 2D DCT → 取左上 8×8 低頻 → 和中位數比大小 → 64 bit。兩張圖的距離 = 不同 bit 數（Hamming）。
距離 <= PHASH_T 視為近似重複，只留先出現的（順序 = 格子順序 → 格內 rank）。

用法： .venv/bin/python -B devset_v0/stage0/s0_finalize.py     （結果固定，可重跑）
"""
import collections, hashlib, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
IMG = R / 'data' / 'derived' / 'devset_images'
KEEP = 300
PHASH_T = 4
N = 32
_k = np.arange(N)
DCT = np.cos(np.pi * (2 * _k[None, :] + 1) * _k[:, None] / (2 * N))   # DCT-II 基底（未正規化，不影響和中位數比大小）


def phash(path):
    im = Image.open(path)
    if im.mode in ('RGBA', 'LA', 'P'):           # 透明底貼到白底
        im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, (255, 255, 255, 255)); im = Image.alpha_composite(bg, im)
    g = np.asarray(im.convert('L').resize((N, N), Image.LANCZOS), dtype=np.float64)
    low = (DCT @ g @ DCT.T)[:8, :8]
    bits = (low > np.median(low)).flatten()
    return int(''.join('1' if b else '0' for b in bits), 2), im.size


def work(asin):
    p = IMG / f'{asin}.jpg'
    try:
        h, size = phash(p)
        return asin, hashlib.sha256(p.read_bytes()).hexdigest(), h, size, p.stat().st_size
    except Exception as e:  # noqa
        return asin, None, None, None, f'{type(e).__name__}: {e}'


def main():
    rows = [json.loads(l) for l in open(HERE / 'download_list.jsonl')]
    dl = {}
    for l in open(HERE / 'download_log.jsonl'):
        d = json.loads(l); dl[d['parent_asin']] = d
    have = [r['parent_asin'] for r in rows if dl.get(r['parent_asin'], {}).get('ok') and (IMG / f"{r['parent_asin']}.jpg").exists()]
    with ProcessPoolExecutor(16) as ex:
        info = {a: (sha, h, size, nbytes) for a, sha, h, size, nbytes in ex.map(work, have, chunksize=64)}
    build = json.load(open(HERE / 'build_stats.json'))
    kept_hash, kept_asin, kept_sha = [], [], {}
    pool, per = [], collections.defaultdict(lambda: collections.Counter())
    dup_pairs = []
    for r in rows:                                  # download_list 的順序 = 格子順序 → rank
        a, c = r['parent_asin'], r['cell']
        if per[c]['in_pool'] >= KEEP:
            per[c]['unused_reserve'] += 1; continue
        per[c]['considered'] += 1
        if a not in info or info[a][0] is None:
            per[c]['download_failed'] += 1; continue
        sha, h, size, nbytes = info[a]
        dup = kept_sha.get(sha)
        dist = 0
        if dup is None and kept_hash:
            x = np.bitwise_xor(np.array(kept_hash, dtype=np.uint64), np.uint64(h))
            d = np.unpackbits(x.view(np.uint8)).reshape(len(kept_hash), 64).sum(1)
            j = int(d.argmin()); dist = int(d[j])
            if dist <= PHASH_T:
                dup = kept_asin[j]
        if dup is not None:
            per[c]['phash_dup_removed'] += 1; dup_pairs.append({'removed': a, 'kept': dup, 'dist': dist, 'cell': c}); continue
        kept_hash.append(h); kept_asin.append(a); kept_sha[sha] = a
        per[c]['in_pool'] += 1
        style, item = c.split('|')
        pool.append({'parent_asin': a, 'title': r['title'], 'store': r['store'], 'source': r['source'],
                     'categories': r['categories'], 'item': item, 'kw_style': r['kw_style'], 'cell': c,
                     'kw_style_title': r['style_title'], 'kw_style_detail': r['style_detail'], 'details_style': r['details_style'],
                     'image_path': f'data/derived/devset_images/{a}.jpg', 'image_wh': list(size), 'image_bytes': nbytes,
                     'img_kind': r['img_kind'], 'sha256': sha, 'phash': f'{h:016x}', 'rank': r['rank']})
    with open(HERE / 'pool.jsonl', 'w', encoding='utf-8') as f:
        for p in pool:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')
    cells = {}
    for c, b in build['cells'].items():
        pc = per[c]
        base = {'in_pool': pc['in_pool'], 'download_failed': pc['download_failed'], 'phash_dup_removed': pc['phash_dup_removed'],
                'downloaded_candidates': b['to_download']}
        cells[c] = {'kw_hits': b['kw_hits'], 'after_title_dedup': b['after_title_dedup'], **base}
    out = {'phash_threshold': PHASH_T, 'keep': KEEP, 'n_pool': len(pool), 'n_pool_cells': len(pool),
           'images_total_bytes_in_pool': sum(p['image_bytes'] for p in pool),
           'images_total_bytes_on_disk': sum((IMG / f"{a}.jpg").stat().st_size for a, d in dl.items() if d['ok']),
           'download_ok': sum(1 for d in dl.values() if d['ok']), 'download_failed_total': sum(1 for d in dl.values() if not d['ok']),
           'cells': cells}
    (HERE / 'cell_counts.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    (HERE / 'phash_dups.json').write_text(json.dumps(dup_pairs, indent=0), encoding='utf-8')
    print({k: v for k, v in out.items() if k != 'cells'})
    print('phash dups', len(dup_pairs), collections.Counter(d['dist'] for d in dup_pairs))
    for c, v in cells.items():
        print(c, v)


if __name__ == '__main__':
    main()
