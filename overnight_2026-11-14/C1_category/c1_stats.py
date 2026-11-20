"""C1：Amazon Reviews 2023 家具／家飾／燈具子集的 6 項資料確認（任務文件附錄 A）。

每個來源檔只串流讀一次（gzip + 逐行 json），同一趟同時累計：
  (1) 類別路徑統計  (2) 燈具位置  (3) details 屬性覆蓋率與值分布
  (4) title 風格字詞  (5) 風格 × 品項交叉表  (6) 圖片可用性、parent_asin 唯一性
每筆商品另外判斷是否屬於 complete（與 build_amazon_complete_subset.py 的 REQUIRED/filled 相同），
所以 subset 與 complete 兩個版本的數字一次算完，不必再讀 *_complete.jsonl.gz。

用法（專案根目錄）：
    .venv/bin/python overnight_2026-11-14/C1_category/c1_stats.py            # 全量
    .venv/bin/python overnight_2026-11-14/C1_category/c1_stats.py --limit 50000   # 每檔只讀前 N 筆（測試用）
輸出：overnight_2026-11-14/C1_category/c1_stats.json
"""
import argparse
import collections
import gzip
import json
import re
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from build_amazon_complete_subset import REQUIRED, filled  # noqa: E402  與 complete 子集同一判準

DATA = ROOT / 'data' / 'external' / 'amazon_reviews_2023'
# 來源名稱 -> 檔名。dining 是 C1 補抓的（fetch_dining_subset.py），不存在就略過。
SOURCES = {
    'home': 'home_decor_subset.jsonl.gz',
    'dining': 'dining_subset.jsonl.gz',
    'lighting': 'lighting_subset.jsonl.gz',
    'patio': 'patio_furniture_subset.jsonl.gz',
    'handmade': 'handmade_home_subset.jsonl.gz',
}

# ---------------------------------------------------------------- (4) 風格字詞
# 大小寫不敏感、用 \b 字界；一個商品可同時命中多個風格（multi-label）。
STYLE_REGEX = {
    'mid_century': r'\bmid[\s\-]*century\b|\bmcm\b',
    'farmhouse': r'\bfarm\s*house\b',
    'rustic': r'\brustic\b',
    'boho': r'\bboho\b|\bbohemian\b',
    'industrial': r'\bindustrial\b',
    'modern': r'\bmodern\b',
    'contemporary': r'\bcontemporary\b',
    'minimalist': r'\bminimal(ist|istic|ism)?\b',
    'scandinavian': r'\bscandinavian\b|\bnordic\b|\bscandi\b',
    'coastal': r'\bcoastal\b|\bnautical\b',
    'glam': r'\bglam(orous|our)?\b|\bhollywood\s+regency\b',
    'vintage': r'\bvintage\b',
    'retro': r'\bretro\b',
    'traditional': r'\btraditional\b',
    'transitional': r'\btransitional\b',
    'japandi': r'\bjapandi\b',
    'shabby_chic': r'\bshabby[\s\-]*chic\b',
    'french_country': r'\bfrench\s+country\b',
    'art_deco': r'\bart[\s\-]*deco\b',
}
STYLE_RE = {k: re.compile(v, re.I) for k, v in STYLE_REGEX.items()}


def styles_of(text):
    if not text:
        return []
    out = [k for k, r in STYLE_RE.items() if r.search(text)]
    # 「modern」若只出現在 mid-century modern 中，另外記 modern_excl_mcm 讓兩者可分開看
    if 'modern' in out:
        rest = re.sub(r'mid[\s\-]*century\s+modern', ' ', text, flags=re.I)
        if STYLE_RE['modern'].search(rest):
            out.append('modern_excl_mcm')
    return out


# ---------------------------------------------------------------- (5) 品項類型
# 判斷順序：先看類別路徑（從最深層往上，每層找第一個命中的品項）；類別沒命中才看 title。
# 每個品項 = (類別層名稱 regex, title regex)。順序有意義：較具體的放前面。
ITEM_RULES = [
    # (品項, 類別層名稱 regex, title regex)；順序有意義：較具體／容易混淆的放前面
    ('candle_holder', r'candleholder|candlestick|candle lanterns|candelabra|candle sconces|candle chandeliers|menorahs|tea light holders',
     r'\bcandle\s*holders?\b|\bcandlesticks?\b|\bcandelabras?\b'),
    ('lamp_shade', r'lamp shades|lamp finials|replacement globes', r'\blamp\s*shades?\b'),
    ('ceiling_fan', r'^ceiling fans', r'\bceiling fans?\b'),
    ('chandelier_pendant', r'chandeliers|pendant lights|close to ceiling|^ceiling lights|track lighting|island lights',
     r'\bchandeliers?\b|\bpendant lights?\b|\bflush mount\b|\bceiling lights?\b'),
    ('wall_sconce', r'sconces|vanity lights', r'\bsconces?\b|\bvanity lights?\b'),
    ('lamp', r'^(table|floor|desk) lamps|^lamp sets|^lamps & shades|lamps & lighting|^lamps$',
     r'\b(table|floor|desk|bedside|arc|torchiere|reading)\s+lamps?\b|\blamps?\b'),
    ('slipcover', r'slipcover|stool covers', r'\bslipcovers?\b|\b(sofa|couch|chair)\s+covers?\b'),
    ('bath_textile', r'shower curtain|towel|bath rugs|bath mats', r'\bshower curtains?\b|\btowels?\b|\bbath (mat|rug)s?\b'),
    ('table_chair_set', r'table & chair sets|tables & chairs|dining (room )?sets', r'\bdining (table )?set\b|\btable and chairs?\b'),
    ('sofa', r'sofas|couches|loveseats|sectional|^futons$|futon sets|chaise', r'\bsofas?\b|\bcouch(es)?\b|\bloveseats?\b|\bsectionals?\b'),
    ('dresser_nightstand', r'dressers|nightstands|chests|armoires|vanities|trunks',
     r'\bdressers?\b|\bnightstands?\b|\bchest of drawers\b'),
    ('stool', r'stools', r'\bstools?\b'),
    ('bench', r'benches', r'\bbench(es)?\b'),
    ('ottoman_pouf', r'ottomans|poufs', r'\bottomans?\b|\bpoufs?\b'),
    ('chair', r'chairs|recliners|gliders|rocking|seats$|theater seating', r'\bchairs?\b|\brecliners?\b|\barmchairs?\b'),
    ('desk', r'desks', r'\bdesks?\b'),
    ('table', r'^tables$|tables$|tv trays', r'\b(coffee|end|side|console|dining|accent|nightstand)?\s*tables?\b'),
    ('bed_frame', r'^beds$|bed frames|headboards|bases & foundations|daybed', r'\bbed frames?\b|\bheadboards?\b|\bplatform bed\b'),
    ('cabinet_sideboard', r'cabinets|sideboards|buffets|television stands|media storage|bar & serving carts|bars & wine|pantries|baker|islands & carts|over-the-toilet',
     r'\bcabinets?\b|\bsideboards?\b|\bbuffets?\b|\btv stands?\b'),
    ('shelf_bookcase', r'shel(f|ves|ving)|bookcases', r'\bshel(f|ves)\b|\bbookcases?\b|\bbookshel(f|ves)\b'),
    ('mirror', r'mirrors', r'\bmirrors?\b'),
    ('rug_accessory', r'rug pads|rug grip|rug protectors', r'\brug pads?\b'),
    ('rug', r'rugs|runners$', r'\brugs?\b|\brunner rug\b'),
    ('curtain_hardware', r'window treatment hardware|rods$|holdbacks', r'\bcurtain rods?\b|\bholdbacks?\b'),
    ('curtain', r'curtain|drapes|valances', r'\bcurtains?\b|\bdrapes?\b|\bvalances?\b'),
    ('throw_pillow', r'throw pillow|decorative pillows|floor pillows',
     r'\b(throw|decorative|accent)\s+pillows?\b|\bpillow\s*covers?\b|\bcushion covers?\b'),
    ('sheets', r'sheet|pillowcases|pillow shams', r'\bsheets?\b|\bpillowcases?\b'),
    ('duvet_comforter', r'duvet|comforter|^quilts|quilt sets|bedspread|coverlet|bedding sets',
     r'\bduvet\b|\bcomforters?\b|\bquilts?\b|\bbedspreads?\b|\bcoverlets?\b'),
    ('throw_blanket', r'^throws$|blankets', r'\bthrows?\b|\bblankets?\b'),
    ('sign_plaque', r'signs & plaques', r'\bsigns?\b|\bplaques?\b'),
    ('wall_art', r'wall art|posters|prints|paintings|photographs|tapestries|wall sculptures|wall stickers|murals|wall d[ée]cor',
     r'\bwall art\b|\bcanvas\b|\bposters?\b|\bprints?\b|\bpaintings?\b|\btapestr(y|ies)\b|\bwall d[ée]cor\b'),
    ('clock', r'clocks', r'\bclocks?\b'),
    ('vase', r'^vases$', r'\bvases?\b'),
    ('picture_frame', r'picture frames|tabletop frames', r'\bpicture frames?\b|\bphoto frames?\b'),
    ('planter', r'planters', r'\bplanters?\b|\bflower\s*pots?\b'),
    ('basket_box', r'baskets|decorative boxes', r'\bbaskets?\b'),
    ('artificial_plant', r'^artificial', r'\bartificial (plants?|flowers?)\b'),
    ('sculpture_figurine', r'sculptures|statues|figurines', r'\bsculptures?\b|\bstatues?\b|\bfigurines?\b'),
]
# Kitchen & Dining > Dining & Entertaining 底下改用這組（避免 Decorative Bowls 被當成餐具）
DINING_RULES = [
    ('bar_tools', r'^bar tools$', r'\bcocktail shaker\b|\bbar tools?\b|\bjiggers?\b'),
    ('flatware', r'flatware|silverware|cutlery|forks|spoons|knives|chopsticks', r'\bflatware\b|\bsilverware\b|\bcutlery\b'),
    ('glassware', r'glassware|drinkware|glasses|tumblers|cups|mugs|stemware|goblets', r'\bglass(es|ware)\b|\btumblers?\b|\bmugs?\b|\bcups?\b'),
    ('dinnerware', r'dinnerware|plates|bowls|place settings', r'\bdinnerware\b|\bplates?\b|\bbowls?\b'),
    ('serveware', r'^serveware$|serving|trays|platters|pitchers|cake stands|tureens|butter dishes|teapots|cream & sugar|egg cups', r'\bserving\b|\bplatters?\b|\btrays?\b'),
    ('table_linen', r'linens|napkins|placemats|tablecloths|table runners', r'\bplacemats?\b|\bnapkins?\b|\btablecloths?\b'),
]


def _compile(rules):
    return ([(n, re.compile(c, re.I)) for n, c, _ in rules], [(n, re.compile(t, re.I)) for n, _, t in rules])


HOME_CAT_RE, HOME_TITLE_RE = _compile(ITEM_RULES)
DINING_CAT_RE, DINING_TITLE_RE = _compile(DINING_RULES)
# Tools & Home Improvement > Lighting & Ceiling Fans 底下只用燈具類規則（避免 neon sign、under-cabinet light 被誤判）
LIGHT_ITEMS = ('candle_holder', 'lamp_shade', 'ceiling_fan', 'chandelier_pendant', 'wall_sconce', 'lamp')
LIGHT_CAT_RE, LIGHT_TITLE_RE = _compile([r for r in ITEM_RULES if r[0] in LIGHT_ITEMS])


def item_of(cats, title):
    """回傳 (品項, 判斷依據)。先從類別路徑最深層往上找，找不到才用 title 關鍵字。"""
    if 'Dining & Entertaining' in cats:
        cat_re, title_re, fallback = DINING_CAT_RE, DINING_TITLE_RE, 'dining_other'
    elif 'Lighting & Ceiling Fans' in cats[1:2]:
        cat_re, title_re, fallback = LIGHT_CAT_RE, LIGHT_TITLE_RE, 'lighting_other'
    else:
        cat_re, title_re, fallback = HOME_CAT_RE, HOME_TITLE_RE, 'other'
    for level in reversed(cats[1:]):
        for name, r in cat_re:
            if r.search(level):
                return name, 'category'
    for name, r in title_re:
        if title and r.search(title):
            return name, 'title'
    return fallback, 'none'


# ---------------------------------------------------------------- (3) details 屬性
ATTR_KEYS = ['Style', 'Color', 'Material', 'Shape', 'Pattern', 'Finish Type', 'Frame Material',
             'Furniture Finish', 'Theme', 'Room Type', 'Fabric Type', 'Base Material',
             'Top Material Type', 'Seat Material Type', 'Shade Material', 'Product Style',
             'Furniture Base Movement', 'Special Feature', 'Color Name', 'Material Type']
# 「類似鍵」：鍵名中含這些字（大小寫不敏感）也算該維度有值
DIM_KEY_RE = {
    'style': re.compile(r'style', re.I),
    'color': re.compile(r'colou?r|finish', re.I),
    'material': re.compile(r'material|fabric', re.I),
    'shape': re.compile(r'shape', re.I),
    'pattern': re.compile(r'pattern', re.I),
}
TOP_VALUES = 40


def norm_val(v):
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    return re.sub(r'\s+', ' ', str(v)).strip().lower()


# ---------------------------------------------------------------- 單一來源掃描
def new_group():
    return {
        'n': 0,
        'level2': collections.Counter(),
        'level23': collections.Counter(),
        'level234': collections.Counter(),
        'detail_keys': collections.Counter(),
        'attr_values': {k: collections.Counter() for k in ATTR_KEYS},
        'dim_any': collections.Counter(),          # 該維度（含類似鍵）有值的商品數
        'style_title': collections.Counter(),
        'style_title_any': 0,
        'style_detail': collections.Counter(),      # details['Style'] 值經同一組 regex 歸類
        'style_detail_present': 0,
        'style_title_or_detail': collections.Counter(),
        'item': collections.Counter(),
        'item_source': collections.Counter(),
        'cross_title': collections.Counter(),       # (style, item)
        'cross_title_or_detail': collections.Counter(),
        'examples': {},                             # "style|item" -> 前 2 個 title
        'img': collections.Counter(),
        'n_images_hist': collections.Counter(),
        'lighting_paths': collections.Counter(),    # 燈具相關路徑
        'other_paths': collections.Counter(),       # 沒歸到任何品項的商品，類別路徑前 4 層
        'item_paths': collections.Counter(),        # (品項, 類別路徑前 4 層)：檢查規則是否合理
    }


LIGHT_PATH_RE = re.compile(r'lamp|lighting|light fixture|chandelier|sconce', re.I)


def update(g, row, cats, title, details):
    g['n'] += 1
    g['level2'][cats[1] if len(cats) > 1 else '(none)'] += 1
    if len(cats) > 2:
        g['level23'][' > '.join(cats[1:3])] += 1
    if len(cats) > 3:
        g['level234'][' > '.join(cats[1:4])] += 1
    path = ' > '.join(cats)
    if LIGHT_PATH_RE.search(path):
        g['lighting_paths'][' > '.join(cats[:4])] += 1

    # (3) details
    present_keys = [k for k, v in details.items() if filled(v)]
    for k in present_keys:
        g['detail_keys'][k] += 1
    for k in ATTR_KEYS:
        if k in details and filled(details[k]):
            g['attr_values'][k][norm_val(details[k])] += 1
    for dim, r in DIM_KEY_RE.items():
        if any(r.search(k) for k in present_keys):
            g['dim_any'][dim] += 1

    # (4) 風格
    st = styles_of(title)
    for s in st:
        g['style_title'][s] += 1
    if st:
        g['style_title_any'] += 1
    dstyle = details.get('Style') if filled(details.get('Style')) else None
    sd = styles_of(norm_val(dstyle)) if dstyle else []
    if dstyle:
        g['style_detail_present'] += 1
    for s in sd:
        g['style_detail'][s] += 1
    both = sorted(set(st) | set(sd))
    for s in both:
        g['style_title_or_detail'][s] += 1

    # (5) 品項與交叉表
    item, src = item_of(cats, title)
    g['item'][item] += 1
    g['item_source'][src] += 1
    p4 = ' > '.join(cats[1:4])
    if src == 'none':
        g['other_paths'][p4] += 1
    g['item_paths'][(item, p4)] += 1
    for s in st:
        g['cross_title'][(s, item)] += 1
        key = f'{s}|{item}'
        ex = g['examples'].setdefault(key, [])
        if len(ex) < 2:
            ex.append(f"{row.get('parent_asin')} :: {title[:120]}")
    for s in both:
        g['cross_title_or_detail'][(s, item)] += 1

    # (6) 圖片
    imgs = row.get('images') or []
    g['n_images_hist'][min(len(imgs), 10)] += 1
    usable = [i for i in imgs if isinstance(i, dict) and (i.get('large') or i.get('hi_res'))]
    main = [i for i in imgs if isinstance(i, dict) and i.get('variant') == 'MAIN']
    g['img']['has_any_image'] += bool(imgs)
    g['img']['has_usable_large_or_hires'] += bool(usable)
    g['img']['has_large'] += any(isinstance(i, dict) and i.get('large') for i in imgs)
    g['img']['has_hi_res'] += any(isinstance(i, dict) and i.get('hi_res') for i in imgs)
    g['img']['has_MAIN_variant'] += bool(main)
    g['img']['MAIN_large'] += any(i.get('large') for i in main)
    g['img']['MAIN_hi_res'] += any(i.get('hi_res') for i in main)
    g['img']['first_image_is_MAIN'] += bool(imgs) and isinstance(imgs[0], dict) and imgs[0].get('variant') == 'MAIN'


def finalize(g):
    out = dict(g)
    out['level2'] = g['level2'].most_common()
    out['level23'] = g['level23'].most_common()
    out['level234'] = g['level234'].most_common(300)
    out['detail_keys'] = g['detail_keys'].most_common(80)
    out['attr_values'] = {k: {'n_present': sum(c.values()), 'n_unique': len(c),
                              'top': c.most_common(TOP_VALUES)} for k, c in g['attr_values'].items()}
    for k in ('dim_any', 'style_title', 'style_detail', 'style_title_or_detail', 'item',
              'item_source', 'img'):
        out[k] = dict(g[k].most_common())
    out['n_images_hist'] = dict(sorted(g['n_images_hist'].items()))
    out['cross_title'] = [[s, i, n] for (s, i), n in g['cross_title'].most_common()]
    out['cross_title_or_detail'] = [[s, i, n] for (s, i), n in g['cross_title_or_detail'].most_common()]
    out['lighting_paths'] = g['lighting_paths'].most_common(60)
    out['other_paths'] = g['other_paths'].most_common(60)
    out['item_paths'] = [[i, p, n] for (i, p), n in g['item_paths'].most_common(400)]
    return out


def scan(args):
    name, fname, limit = args
    path = DATA / fname
    groups = {'subset': new_group(), 'complete': new_group()}
    asin_count = collections.Counter()
    t0 = time.time()
    n = 0
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            if limit and n >= limit:
                break
            n += 1
            row = json.loads(line)
            cats = row.get('categories') or []
            title = row.get('title') or ''
            details = row.get('details') or {}
            if not isinstance(details, dict):
                details = {}
            asin_count[row.get('parent_asin')] += 1
            update(groups['subset'], row, cats, title, details)
            if all(filled(row.get(k)) for k in REQUIRED):
                update(groups['complete'], row, cats, title, details)
            if n % 200_000 == 0:
                print(f'[{name}] {n:,} rows {time.time() - t0:.0f}s', flush=True)
    dup = {a: c for a, c in asin_count.items() if c > 1}
    res = {
        'file': str(path.relative_to(ROOT)),
        'rows_read': n,
        'limit': limit,
        'parent_asin': {'rows': n, 'unique': len(asin_count), 'n_asins_duplicated': len(dup),
                        'null': asin_count.get(None, 0), 'dup_examples': list(dup.items())[:10]},
        'groups': {k: finalize(v) for k, v in groups.items()},
        'seconds': round(time.time() - t0, 1),
    }
    print(f'[{name}] done {n:,} rows {res["seconds"]}s', flush=True)
    return name, res, set(asin_count)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='每檔只讀前 N 筆（0 = 全量）')
    ap.add_argument('--out', default=str(HERE / 'c1_stats.json'))
    a = ap.parse_args()
    jobs = [(n, f, a.limit) for n, f in SOURCES.items() if (DATA / f).exists()]
    skipped = [n for n, f in SOURCES.items() if not (DATA / f).exists()]
    with Pool(len(jobs)) as pool:
        results = pool.map(scan, jobs)
    out = {'style_regex': STYLE_REGEX,
           'item_rules': [{'item': n, 'category_regex': c, 'title_regex': t} for n, c, t in ITEM_RULES],
           'dining_item_rules': [{'item': n, 'category_regex': c, 'title_regex': t} for n, c, t in DINING_RULES],
           'attr_keys': ATTR_KEYS, 'dim_key_regex': {k: v.pattern for k, v in DIM_KEY_RE.items()},
           'required_for_complete': list(REQUIRED), 'skipped_sources': skipped, 'sources': {}}
    asins = {}
    for name, res, s in results:
        out['sources'][name] = res
        asins[name] = s
    names = list(asins)
    out['parent_asin_overlap_between_sources'] = {
        f'{x}&{y}': len(asins[x] & asins[y]) for i, x in enumerate(names) for y in names[i + 1:]}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('wrote', a.out)


if __name__ == '__main__':
    main()
