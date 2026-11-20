"""階段 4：三種 query 文字（tmpl_zh / tmpl_en / syn_en）的固定模板、同義詞表、自動檢查。run_select4.py 與 gen_syn.py 共用。"""
import re, sys
from pathlib import Path
sys.dont_write_bytecode = True
U = Path(__file__).resolve().parent; D = U.parent; R = D.parent
sys.path.insert(0, str(R / 'overnight_2026-11-14' / 'C1_category'))
import c1_stats  # noqa: E402

K = 5
STYLE_PAT = re.compile('|'.join(c1_stats.STYLE_REGEX.values()), re.I)
CAT_KEY = lambda c: c.replace('/', '_').replace(' ', '_')
CAT_ZH = {'chair': '椅子', 'table': '桌子', 'lamp': '檯燈 / 落地燈', 'chandelier_pendant': '吊燈', 'wall_art': '壁面裝飾畫'}
CAT_EN = {'chair': 'chairs', 'table': 'tables', 'lamp': 'lamps (table or floor lamps)', 'chandelier_pendant': 'chandeliers / pendant lights', 'wall_art': 'wall art'}
CAT_EN_SHORT = {'chair': 'chairs', 'table': 'tables', 'lamp': 'lamps', 'chandelier_pendant': 'chandeliers or pendant lights', 'wall_art': 'wall art'}
DIM_ZH = {'category': '品項', 'color': '顏色', 'material': '材質', 'shape': '形狀'}
DIM_EN = {'category': 'item type', 'color': 'color', 'material': 'material', 'shape': 'shape'}
VAL_ZH = {'white': '白色', 'black': '黑色', 'gray': '灰色', 'beige/cream': '米色 / 奶油色', 'brown': '棕色', 'natural wood': '原木色', 'blue': '藍色', 'green': '綠色',
          'red/pink': '紅色 / 粉紅色', 'yellow/orange': '黃色 / 橘色', 'metallic': '金屬色', 'multicolor': '多色',
          'wood': '木頭', 'metal': '金屬', 'fabric': '布料', 'leather': '皮革', 'rattan/wicker/rope': '藤 / 編織 / 繩', 'plastic/acrylic': '塑膠 / 壓克力', 'glass': '玻璃',
          'stone/ceramic/concrete': '石材 / 陶瓷 / 水泥', 'paper/canvas': '紙 / 畫布'}
VAL_EN = {'white': 'white', 'black': 'black', 'gray': 'gray', 'beige/cream': 'beige or cream', 'brown': 'brown', 'natural wood': 'natural wood color', 'blue': 'blue', 'green': 'green',
          'red/pink': 'red or pink', 'yellow/orange': 'yellow or orange', 'metallic': 'metallic', 'multicolor': 'multicolored',
          'wood': 'wood', 'metal': 'metal', 'fabric': 'fabric', 'leather': 'leather', 'rattan/wicker/rope': 'rattan, wicker or rope', 'plastic/acrylic': 'plastic or acrylic',
          'glass': 'glass', 'stone/ceramic/concrete': 'stone, ceramic or concrete', 'paper/canvas': 'paper or canvas'}
# 同義詞表（自動檢查用）
VAL_SYN = {'white': r'white|ivory|off-white', 'black': r'black|ebony', 'gray': r'gr[ae]y|charcoal|slate', 'beige/cream': r'beige|cream|tan|ivory|off-white|neutral',
           'brown': r'brown|chocolate|espresso|walnut|dark wood|coffee|tan', 'natural wood': r'natural wood|wood|wooden|light wood|oak|timber|natural',
           'blue': r'blue|navy|teal|turquoise|aqua', 'green': r'green|olive|sage|emerald', 'red/pink': r'red|pink|rose|burgundy|blush|magenta',
           'yellow/orange': r'yellow|orange|gold|mustard|amber', 'metallic': r'metallic|metal|gold|silver|brass|chrome|copper|bronze|steel|nickel',
           'multicolor': r'multi-?colou?r(ed)?|colou?rful|rainbow|assorted|bright colou?rs|many colou?rs',
           'wood': r'wood|wooden|timber|oak|walnut|pine|bamboo', 'metal': r'metal|metallic|iron|steel|brass|aluminum|aluminium|chrome|copper|bronze',
           'fabric': r'fabric|upholster\w*|cloth|linen|cotton|textile|velvet|soft', 'leather': r'leather|faux leather',
           'rattan/wicker/rope': r'rattan|wicker|rope|cane|seagrass|jute|woven', 'plastic/acrylic': r'plastic|acrylic|resin|lucite', 'glass': r'glass',
           'stone/ceramic/concrete': r'stone|ceramic|concrete|marble|porcelain|cement|clay', 'paper/canvas': r'paper|canvas'}
CAT_SYN = {'chair': r'chairs?|armchairs?|seat(s|ing)?|stools?|recliners?', 'table': r'tables?|desks?|consoles?|nightstands?',
           'lamp': r'lamps?|lighting|lights?', 'chandelier_pendant': r'chandeliers?|pendants?|hanging lights?|ceiling lights?|light fixtures?|lights?|lighting',
           'wall_art': r'wall art|artwork|paintings?|prints?|posters?|canvas|wall decor|wall hangings?'}
NEG_RE = re.compile(r"\b(not|no|except|other than|anything but|instead of|aside from|besides|rather than|without)\b|n't\b", re.I)
REF_RE = re.compile(r"\b(this|these|the one|the ones|the picture|the photo|the image|pictured|shown|above|attached|my photo)\b", re.I)


def ck(q):
    return CAT_KEY(q['category'])


def req_parts(q):
    """回傳 (中文限制句, 英文限制句（tmpl_en 用，粗體標記）, 英文模板句（給改寫用，純文字）, 自由維度清單)。"""
    sc, c = q['scenario'], ck(q)
    if sc == 'S1':
        return ('和參考圖片**同風格**的商品', 'in the **same style** as the reference image', 'Find products in the same style as the reference image.', ['category', 'color', 'material', 'shape'])
    if sc == 'S2':
        return (f'和參考圖片**同風格、而且同樣是{CAT_ZH[c]}**的商品', f'in the **same style as the reference image and also {CAT_EN[c]}**',
                f'Find {CAT_EN[c]} in the same style as the reference image.', ['color', 'material', 'shape'])
    if sc == 'T4':
        return (f'和參考圖片**同風格、但不是{CAT_ZH[c]}**的商品', f'in the **same style as the reference image but NOT {CAT_EN[c]}**',
                f'Find products in the same style as the reference image, but not {CAT_EN[c]}.', ['category', 'color', 'material', 'shape'])
    if sc == 'T3':
        a, v = q['attr'], q['value']
        return (f'和參考圖片**同風格、同樣是{CAT_ZH[c]}、而且{DIM_ZH[a]}是{VAL_ZH[v]}**的商品',
                f'in the **same style as the reference image, also {CAT_EN[c]}, and whose {DIM_EN[a]} is {VAL_EN[v]}**',
                f'Find {CAT_EN[c]} in the same style as the reference image, whose {DIM_EN[a]} is {VAL_EN[v]}.',
                [d for d in ('color', 'material', 'shape') if d != a])
    raise ValueError(sc)


def intro(wording):
    if wording == 'tmpl_zh':
        return '使用者附上一張參考商品圖片，想找和它風格一樣的商品。參考圖片如下：'
    if wording == 'tmpl_en':
        return 'The user attached a reference product image and wants to find products in the same style. The reference image is:'
    return 'The user attached a reference product image together with a shopping request. The reference image is:'


def task_text(q, wording, n, syn=None):
    zh, en, _, div = req_parts(q)
    if wording == 'tmpl_zh':
        return f'以下是 {n} 件候選商品。請從候選中挑 {K} 件{zh}，並且讓這 {K} 件盡量多樣：' + '、'.join(DIM_ZH[d] for d in div) + '盡量不同。'
    ds = [DIM_EN[d] for d in div]; divs = ', '.join(ds[:-1]) + ' and ' + ds[-1]
    if wording == 'tmpl_en':
        return f'Below are {n} candidate products. Pick {K} of them that are {en}, and make the {K} as diverse as possible: {divs} should differ as much as possible.'
    return (f'Below are {n} candidate products. The user\'s request is: "{syn}"\n'
            f'Pick the {K} candidates that best satisfy this request, and make the {K} as diverse as possible: {divs} should differ as much as possible.')


def json_text(wording, n):
    if wording == 'tmpl_zh':
        return ('請只回傳 JSON，不要 Markdown。格式如下（尖括號是要你填入的內容，不是答案）：{"selected_positions":[<position>, ...]}'
                f'。position 使用 1-based position；selected_positions 剛好 {K} 個且不得重複；請根據圖片和標題實際判斷後再選。')
    return ('Reply with JSON only, no Markdown. Format (angle brackets are what you fill in, not the answer): {"selected_positions":[<position>, ...]}'
            f'. Use 1-based positions; selected_positions must contain exactly {K} distinct positions; judge from the images and titles before choosing.')


def clean_style(t):
    while True:
        t2 = STYLE_PAT.sub('', t)
        if t2 == t:
            return t
        t = t2


def check_syn(q, text):
    """回傳 (ok, 失敗原因清單)。"""
    why = []; sc = q['scenario']; c = ck(q)
    nw = len(text.split())
    if not 4 <= nw <= 30:
        why.append(f'長度 {nw} 字不在 4–30')
    if STYLE_PAT.search(text) or STYLE_PAT.search(clean_style(text)):
        why.append('出現風格字詞')
    if not REF_RE.search(text):
        why.append('沒提到參考圖')
    hit = {k for k, p in CAT_SYN.items() if re.search(rf'\b({p})\b', text, re.I)}
    if sc in ('S2', 'T3') and c not in hit:
        why.append('沒提到品項字')
    if sc == 'T4':
        if not NEG_RE.search(text):
            why.append('沒有否定詞')
        if c not in hit:
            why.append('沒提到被排除的品項')
        allowed = {c} | ({'lamp', 'chandelier_pendant'} if c in ('lamp', 'chandelier_pendant') else set())   # light / lighting 兩邊字重疊
        other = hit - allowed
        if other:
            why.append(f'把品項限制成其他單一品項 {sorted(other)}')
    if sc == 'S1' and hit:
        why.append(f'限制了品項 {sorted(hit)}')
    if sc == 'T3' and not re.search(rf'\b({VAL_SYN[q["value"]]})\b', text, re.I):
        why.append('沒提到屬性值')
    return (not why), why
