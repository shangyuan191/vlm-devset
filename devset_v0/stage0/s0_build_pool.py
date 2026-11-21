"""階段 0 第 2 步：套用修正後的品項規則（v1）→ 30 格命中數 → 同店標題去重 → 每格排序（seed 0）→ 下載清單。

讀 candidates_raw.jsonl.gz（s0_scan.py 的輸出，C1 規則原樣），不讀原始大檔，幾十秒可重跑、結果固定。

品項規則 v1（和 C1 的差別，理由見 DECISIONS.md）：
  * 只用「類別路徑」決定品項（白名單），不用標題關鍵字補抓。
  * 每個品項有標題排除字（成套、配件、按摩椅等）。
風格格子：標題或 details['Style'] 命中 C1 STYLE_REGEX；6 個目標風格中「剛好命中 1 個」才進格子。

用法： .venv/bin/python -B devset_v0/stage0/s0_build_pool.py
輸出： stage0/download_list.jsonl（每格前 KEEP+RESERVE 件）、stage0/build_stats.json
"""
import collections
import gzip
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 0
KEEP, RESERVE = 300, 40          # 每格入池上限 300；多下載 40 件當遞補（下載失敗、pHash 重複時依序補上）
JACCARD = 0.8

TARGET = {'mid_century': 'mid_century', 'industrial': 'industrial', 'farmhouse': 'farmhouse_rustic',
          'rustic': 'farmhouse_rustic', 'boho': 'boho', 'coastal': 'coastal', 'traditional': 'traditional'}
STYLES = ['mid_century', 'industrial', 'farmhouse_rustic', 'boho', 'coastal', 'traditional']
ITEMS = ['chair', 'table', 'lamp', 'chandelier_pendant', 'wall_art']

# ---- 品項規則 v1：類別路徑白名單（對 ' > '.join(categories[1:]) 做 regex search）+ 標題排除字
PATH_RULES = {
    'chair': r'^Furniture > Living Room Furniture > Chairs$'
             r'|^Furniture > Dining Room Furniture > Chairs$'
             r'|^Furniture > Home Office Furniture > Home Office Chairs( > Home Office Desk Chairs)?$'
             r'|^Patio Furniture & Accessories > Patio Seating > Chairs( > (Patio Dining Chairs|Lounge Chairs|Adirondack Chairs|Rocking Chairs|Sling Chairs))?$'
             r'|^Patio Furniture & Accessories > Outdoor Furniture > Chairs$'
             r'|^Patio Furniture & Accessories > Hammocks, Stands & Accessories > Hammock Chairs$'
             r'|^Home & Kitchen > Furniture > Living Room Furniture > Chairs$',
    'table': r'^Furniture > Living Room Furniture > Tables( > (End Tables|Coffee Tables|Sofa & Console Tables|Nesting Tables|Pedestal Tables|Telephone Tables))?$'
             r'|^Furniture > Dining Room Furniture > Tables$'
             r'|^Patio Furniture & Accessories > Tables( > (Side Tables|Dining Tables|Coffee Tables|Bar Tables|Bistro Tables))?$'
             r'|^Home & Kitchen > Furniture > Living Room Furniture > Tables$',
    'lamp': r'^Lighting & Ceiling Fans > Lamps & Shades > (Table Lamps|Floor Lamps)$'
            r'|^Home & Kitchen > Lighting > Lamps > (Bedside & Table Lamps|Floor Lamps)$',
    'chandelier_pendant': r'^Lighting & Ceiling Fans > Ceiling Lights > (Pendant Lights|Chandeliers|Island Lights)$'
                          r'|^Lighting & Ceiling Fans > Outdoor Lighting > Porch & Patio Lights > Pendant Lights$',
    'wall_art': r'^Wall Art( > (Posters & Prints|Paintings|Photographs|Mixed Media))?$'
                r'|^Home & Kitchen > Artwork > (Prints|Photographs|Paintings|Posters|Mixed Media)$'
                r'|^Home D[ée]cor Products > Tapestries$'
                r'|^Home & Kitchen > Home D[ée]cor > Tapestries$'
                r'|^Home D[ée]cor Products > Home D[ée]cor Accents > Sculptures > Wall Sculptures$',
}
TITLE_EXCLUDE = {
    # 按摩 / 電動起身 / 加熱躺椅（C4 示範 #1 的誤抓）、吧台凳、桌椅組、椅墊椅套
    'chair': r'\bmassag|\bpower lift\b|\blift (chair|recliner)s?\b|\bheat(ed|ing)?\b|\bstools?\b'
             r'|\b(table|desk)s?\s+(and|&|with)\s+(\d+\s+)?chairs?\b|\bchairs?\s+(and|&|with)\s+(a\s+)?(table|desk)\b'
             r'|\b(dining|bistro|conversation|patio)\s+sets?\b|\b(chair|seat)\s+(pad|cushion|cover)s?\b|\bslipcovers?\b|\breplacement\b',
    # 桌椅組（含椅子、凳子、長凳）、桌布桌墊桌腳等配件
    'table': r'\bchairs?\b|\bstools?\b|\bbench(es)?\b|\b(dining|bistro|dinette)\s+sets?\b'
             r'|\btable\s*(cloth|cover|runner|legs?|top only|pad|protector)s?\b|\btablecloths?\b|\breplacement\b',
    'lamp': r'\blamp\s*shades?\b(?!.*\b(table|floor)\s+lamp)|\breplacement\b|\b(harp|finial)s?\b|\bbulbs? only\b',
    'chandelier_pendant': r'\breplacement\b|\b(shade|cord|chain|canopy)\s+(only|kit|set)\b|\blight kit\b|\bceiling fans?\b',
    'wall_art': r'\b(decal|sticker)s?\b|\bwall\s*paper\b|\bframes?\s+only\b',
}
PATH_RE = {k: re.compile(v) for k, v in PATH_RULES.items()}
EXCL_RE = {k: re.compile(v, re.I) for k, v in TITLE_EXCLUDE.items()}


def item_v1(r):
    """回傳 (品項或 None, 被排除的原因或 None)。"""
    path = ' > '.join(r['categories'][1:])
    for it in ITEMS:
        if PATH_RE[it].search(path):
            if EXCL_RE[it].search(r['title'] or ''):
                return None, f'title_exclude:{it}'
            return it, None
    return None, 'path_not_whitelisted'


# ---- 同款判斷：同 store 且去掉顏色、尺寸字詞後標題 token 的 Jaccard >= 0.8（C4 第 4 節）
COLOR = set('''white black gray grey beige cream ivory brown tan taupe khaki espresso walnut oak cherry mahogany natural
blue navy teal turquoise aqua green olive sage red pink rose burgundy maroon purple lavender yellow mustard orange gold golden
silver bronze brass copper chrome nickel multicolor multi colored color colour dark light charcoal coffee'''.split())
SIZE = set('''inch inches in ft feet foot cm mm x w h d l dia diameter small medium large xl xxl mini big tall short king queen
twin full size sizes set of pack pcs pc piece pieces pair single double'''.split())


def norm_tokens(title):
    toks = re.findall(r'[a-z]+|\d+', (title or '').lower())
    return frozenset(t for t in toks if not t.isdigit() and t not in COLOR and t not in SIZE and len(t) > 1)


class Deduper:
    def __init__(self):
        self.kept = collections.defaultdict(list)   # store -> [(tokens, asin)]

    def dup_of(self, store, toks):
        if not store or not toks:
            return None
        for kt, ka in self.kept[store]:
            inter = len(toks & kt)
            if inter and inter / (len(toks) + len(kt) - inter) >= JACCARD:
                return ka
        return None

    def add(self, store, toks, asin):
        if store and toks:
            self.kept[store].append((toks, asin))


def main():
    cells = collections.defaultdict(list)       # (style, item) -> rows
    st = {'c1_item_counts': collections.Counter(), 'excluded': collections.Counter(), 'no_main_image': collections.Counter(),
          'multi_target_style': collections.Counter(), 'c1_cell_hits_same_def': collections.Counter()}
    for line in gzip.open(HERE / 'candidates_raw.jsonl.gz', 'rt', encoding='utf-8'):
        r = json.loads(line)
        tg = sorted({TARGET[s] for s in set(r['style_title']) | set(r['style_detail']) if s in TARGET})
        for s in tg:   # 對照用：C1 原規則下的格子命中數（多風格重複計，和 C1 T5b 同定義；farmhouse/rustic 已合併）
            st['c1_cell_hits_same_def'][f"{s}|{r['item_c1']}"] += 1
        it, why = item_v1(r)
        if it is None:
            if tg:
                st['excluded'][f"{r['item_c1']}|{why}"] += 1
            continue
        if not r['img_url']:
            st['no_main_image'][it] += 1
            continue
        r['item'] = it
        if len(tg) == 1:
            r['kw_style'] = tg[0]
            cells[(tg[0], it)].append(r)
        elif len(tg) > 1:
            st['multi_target_style'][it] += 1

    dd = Deduper()
    out, cell_stats = [], {}
    for s in STYLES:
        for it in ITEMS:
            rows = sorted(cells[(s, it)], key=lambda r: r['parent_asin'])
            random.Random(f'{SEED}-{s}-{it}').shuffle(rows)
            kept, ndup = [], 0
            for r in rows:
                toks = norm_tokens(r['title'])
                d = dd.dup_of(r['store'], toks)
                if d:
                    ndup += 1
                    continue
                dd.add(r['store'], toks, r['parent_asin'])
                kept.append(r)
            cell_stats[f'{s}|{it}'] = {'kw_hits': len(rows), 'title_dups_removed': ndup, 'after_title_dedup': len(kept),
                                       'to_download': min(len(kept), KEEP + RESERVE)}
            for rank, r in enumerate(kept[:KEEP + RESERVE]):
                out.append({**r, 'cell': f'{s}|{it}', 'rank': rank})

    with open(HERE / 'download_list.jsonl', 'w', encoding='utf-8') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    stats = {'seed': SEED, 'keep': KEEP, 'reserve': RESERVE, 'jaccard': JACCARD, 'path_rules': PATH_RULES,
             'title_exclude': TITLE_EXCLUDE, 'cells': cell_stats,
             **{k: dict(sorted(v.items(), key=lambda kv: -kv[1])) for k, v in st.items()}}
    (HERE / 'build_stats.json').write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')
    print('download list:', len(out))
    for k, v in cell_stats.items():
        print(k, v)
    print('multi', dict(st['multi_target_style']), 'noimg', dict(st['no_main_image']))


if __name__ == '__main__':
    main()
