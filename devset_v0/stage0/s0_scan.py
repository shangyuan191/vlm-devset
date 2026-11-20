"""階段 0 第 1 步：掃本機 Amazon Reviews 2023 子集，把 5 個品項的候選（含無風格字詞的）存成精簡快取。

品項 = C1 的 item_of（ITEM_RULES，原樣 import，不改原檔）；風格 = C1 的 STYLE_REGEX（標題或 details['Style']）。
這一步只「原樣」套 C1 規則並把需要的欄位存下來；品項規則的修正在 s0_build_pool.py（讀這個快取，幾秒就能重跑）。

用法（專案根目錄）： .venv/bin/python -B devset_v0/stage0/s0_scan.py
輸出： devset_v0/stage0/candidates_raw.jsonl.gz、scan_summary.json
"""
import gzip
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'overnight_2026-11-14' / 'C1_category'))
import c1_stats as c1  # noqa: E402

ITEMS = ('chair', 'table', 'lamp', 'chandelier_pendant', 'wall_art')
SOURCES = {k: v for k, v in c1.SOURCES.items() if k != 'dining'}  # dining 用另一套品項規則，不會產生這 5 個品項
OUT = HERE / 'candidates_raw.jsonl.gz'


def main_image(images):
    """回傳 (url, 種類)。優先 MAIN 的 hi_res（最大），其次 MAIN 的 large。沒有 MAIN 就不用（只用有主圖的商品）。"""
    for im in images or []:
        if isinstance(im, dict) and im.get('variant') == 'MAIN':
            if im.get('hi_res'):
                return im['hi_res'], 'hi_res'
            if im.get('large'):
                return im['large'], 'large'
    return None, None


def scan(job):
    name, fname = job
    rows, n, kept = [], 0, 0
    t0 = time.time()
    with gzip.open(c1.DATA / fname, 'rt', encoding='utf-8') as f:
        for line in f:
            n += 1
            r = json.loads(line)
            cats = r.get('categories') or []
            title = r.get('title') or ''
            item, src = c1.item_of(cats, title)
            if item not in ITEMS:
                continue
            details = r.get('details') if isinstance(r.get('details'), dict) else {}
            url, kind = main_image(r.get('images'))
            dstyle = details.get('Style') if c1.filled(details.get('Style')) else None
            st_title = c1.styles_of(title)
            st_detail = c1.styles_of(c1.norm_val(dstyle)) if dstyle else []
            # 「任何風格字詞」：標題 + details 的所有值（干擾池要求兩者都不含）
            dtext = ' | '.join(c1.norm_val(v) for v in details.values())
            st_any_detail = c1.styles_of(dtext)
            rows.append(json.dumps({
                'parent_asin': r.get('parent_asin'), 'title': title, 'store': r.get('store'),
                'source': name, 'categories': cats, 'item_c1': item, 'item_src': src,
                'style_title': st_title, 'style_detail': st_detail, 'style_any_detail': st_any_detail,
                'details_style': dstyle, 'img_url': url, 'img_kind': kind,
            }, ensure_ascii=False))
            kept += 1
    print(f'[{name}] {n:,} rows, kept {kept:,}, {time.time() - t0:.0f}s', flush=True)
    return name, n, rows


def main():
    jobs = [(n, f) for n, f in SOURCES.items() if (c1.DATA / f).exists()]
    with Pool(len(jobs)) as pool:
        res = pool.map(scan, jobs)
    summary = {}
    with gzip.open(OUT, 'wt', encoding='utf-8') as out:
        for name, n, rows in res:
            summary[name] = {'rows_read': n, 'kept': len(rows)}
            for line in rows:
                out.write(line + '\n')
    (HERE / 'scan_summary.json').write_text(json.dumps(summary, indent=1))
    print(summary)


if __name__ == '__main__':
    main()
