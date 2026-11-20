"""階段 3 共用：圖片前處理（同 run_chain.img_url）、請求、容錯解析器（同 run_chain.parse_last_json）。"""
import base64, io, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path
from PIL import Image
sys.dont_write_bytecode = True
T = Path(__file__).resolve().parent; D = T.parent; R = D.parent
IMG = R / 'data/derived/devset_images'
K = 5
IMG_MAX = int(os.environ.get('IMG_MAX', '900'))   # 預設 900（同 run_chain.img_url）；只有 LLaVA-OV2 因 token 數降到 560（DECISIONS 12）
MAX_TOKENS = 512
LAST = {}
sys.path.insert(0, str(D / 'stage1'))
from common import OPTIONS, CELL_STYLE, CELL_ITEM   # noqa: E402

CAT_ZH = {'chair': '椅子', 'table': '桌子', 'lamp': '檯燈 / 落地燈', 'chandelier_pendant': '吊燈', 'wall_art': '壁面裝飾畫'}
# 每個風格的一句話定義（濃縮自 stage1/guideline_v1.md 的風格表；不含任何商品標題字詞）
STYLE_DEF = {
    'mid-century modern': '中世紀現代：胡桃木 / 柚木的中深棕色，斜張的錐形細腳、圓角或有機曲線，常見黃銅細節與球形燈泡，裝飾很少。',
    'industrial': '工業風：黑鐵 / 鋼管、鑄鐵、粗糙原木，水管接頭、鉚釘、X 形或 U 形金屬腳、金屬籠形燈罩，結構外露。',
    'farmhouse/rustic': '農舍鄉村風：刷白或做舊的木頭、粗木紋、鍍鋅金屬、麻與格紋布，X 形支架、穀倉門，樸實有手作感。',
    'bohemian': '波西米亞：多色或暖色大地色，藤、麻、流蘇、編織、刺繡，圖案多、不對稱、手工感強。',
    'coastal': '海岸風：白、沙色、淺藍、海軍藍，漂流木、繩、貝殼、白色或淺色藤編，有航海或海洋元素，明亮輕盈。',
    'traditional': '傳統古典風：深色實木、酒紅 / 墨綠 / 古銅，雕花、彎腿或獅爪腳、捲邊扶手、燭台式吊燈，繁複對稱。',
    'modern minimalist': '現代極簡：黑白灰單色或單一金屬色，光滑烤漆 / 金屬 / 玻璃，純直線或純幾何，沒有復古細節。',
    'scandinavian': '北歐風：淺色實木（樺、橡）配白、淺灰、粉嫩色，簡潔圓角、細木腳、柔軟溫暖的布料。',
    'glam': '華麗風：金、銀、鏡面、寶石色，絲絨、水晶、亮面金屬、大理石，高光澤、閃亮。',
    'other': '其他：有明確風格，但不是上面列出的任何一種（例如 Art Deco、日式 / 亞洲、熱帶、摩洛哥、卡通童趣）。',
    'mixed/none': '混合 / 無風格：看不出明確風格（一般普通的商品），或兩種以上風格的特徵分量相當。',
}
assert set(STYLE_DEF) == set(OPTIONS['style'])


def img_url(asin):
    with Image.open(IMG / f'{asin}.jpg') as im:
        im = im.convert('RGB'); im.thumbnail((IMG_MAX, IMG_MAX)); b = io.BytesIO(); im.save(b, format='JPEG', quality=85)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def post(url, model, content, nothink):
    payload = {'model': model, 'messages': [{'role': 'user', 'content': content}], 'max_tokens': MAX_TOKENS, 'temperature': 0}
    if nothink:
        payload['chat_template_kwargs'] = {'enable_thinking': False}
    t0 = time.time()
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=900) as resp:
        r = json.loads(resp.read().decode())
    text = r['choices'][0]['message'].get('content') or ''
    LAST.update(raw=text, latency=round(time.time() - t0, 3), usage=r.get('usage'), finish=r['choices'][0].get('finish_reason'))
    return text


def parse_last_json(text, key):
    dec = json.JSONDecoder(); found = None
    for i, ch in enumerate(text):
        if ch != '{':
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and key in obj:
            found = obj
    if found is None:
        raise ValueError('no JSON object with ' + key)
    return found


def done_keys(path, key):
    return {json.loads(l)[key] for l in open(path)} if Path(path).exists() else set()


def request_with_retry(url, model, content, nothink, validate, key):
    """最多 3 次；伺服器連不上 → SystemExit（不寫 failed）。回傳 (status, parsed, attempts)。"""
    for attempt in range(1, 4):
        try:
            text = post(url, model, content, nothink)
            obj = parse_last_json(text, key)
            return 'ok', validate(obj), attempt
        except urllib.error.HTTPError as ex:
            print('HTTP', ex.code, ex.read().decode()[:150], flush=True); time.sleep(3)
        except (urllib.error.URLError, ConnectionError, TimeoutError) as ex:
            raise SystemExit(f'server unreachable ({ex}); stop (no failed row written)')
        except Exception as ex:
            print('error:', str(ex)[:150], flush=True); time.sleep(1)
    return 'failed', None, 3
