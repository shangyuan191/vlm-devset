"""階段 1 共用：選項清單、輸出解析與檢查。三位標註者用同一份 guideline_v1.md 與同一個解析器。"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUIDELINE = (HERE / 'guideline_v1.md').read_text(encoding='utf-8')
# 三位標註者共用、每次呼叫完全相同的 system prompt（RUNBOOK 3.3）
SYSTEM_PROMPT = GUIDELINE.rstrip() + '\n\n每個 item_id 只輸出一行 JSON（id、style、style_conf、category、category_conf、color、color_conf、material、material_conf、shape、shape_conf），不要任何其他文字、不要解釋、不要 Markdown。\n'
FINAL_TEXT = '依準則標註以上每一件，只輸出 JSON lines。'
DIMS = ['style', 'category', 'color', 'material', 'shape']
OPTIONS = {
    'style': ['mid-century modern', 'industrial', 'farmhouse/rustic', 'bohemian', 'coastal', 'traditional',
              'modern minimalist', 'scandinavian', 'glam', 'other', 'mixed/none'],
    'category': ['chair', 'sofa', 'table', 'stool/ottoman', 'cabinet/storage', 'shelf', 'bed', 'lamp',
                 'chandelier/pendant', 'other lighting', 'wall art', 'rug', 'other'],
    'color': ['white', 'black', 'gray', 'beige/cream', 'brown', 'natural wood', 'blue', 'green', 'red/pink',
              'yellow/orange', 'metallic', 'multicolor'],
    'material': ['wood', 'metal', 'fabric', 'leather', 'rattan/wicker/rope', 'plastic/acrylic', 'glass',
                 'stone/ceramic/concrete', 'paper/canvas'],
    'shape': ['rectilinear', 'curved', 'round', 'angular/geometric', 'organic/irregular'],
}
# 格子名稱 ↔ 標註選項
CELL_STYLE = {'mid_century': 'mid-century modern', 'industrial': 'industrial', 'farmhouse_rustic': 'farmhouse/rustic',
              'boho': 'bohemian', 'coastal': 'coastal', 'traditional': 'traditional'}
CELL_ITEM = {'chair': 'chair', 'table': 'table', 'lamp': 'lamp', 'chandelier_pendant': 'chandelier/pendant', 'wall_art': 'wall art'}


def check(obj):
    """檢查一筆標註是否合法；合法回傳整理後的 dict，否則丟 ValueError。只做大小寫與前後空白的正規化，不猜測。"""
    out = {'id': str(obj['id']).strip()}
    for d in DIMS:
        v = str(obj[d]).strip().lower()
        if v not in OPTIONS[d]:
            raise ValueError(f'{d}={v!r} not in options')
        c = int(obj[f'{d}_conf'])
        if c not in (1, 2, 3):
            raise ValueError(f'{d}_conf={c}')
        out[d], out[f'{d}_conf'] = v, c
    return out


def parse_lines(text):
    """從模型輸出抓出所有含 "id" 的 JSON 物件（容忍 ```json 框與前後文字）。回傳 (合法清單, 錯誤清單)。"""
    good, bad = [], []
    for m in re.finditer(r'\{[^{}]*"id"[^{}]*\}', text or ''):
        try:
            good.append(check(json.loads(m.group(0))))
        except Exception as e:  # noqa
            bad.append(f'{type(e).__name__}: {e} :: {m.group(0)[:120]}')
    return good, bad
