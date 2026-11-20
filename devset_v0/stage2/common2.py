"""階段 2 共用：路徑、27 格、目標數、讀檔、合格條件。標註選項 / system prompt / 解析器直接 import 階段 1 的 common.py（不複製、不修改）。"""
import collections
import json
import math
import sys
from pathlib import Path

S = Path(__file__).resolve().parent          # devset_v0/stage2
D = S.parent                                 # devset_v0
R = D.parent
S1 = D / 'stage1'
sys.path.insert(0, str(S1))
from common import SYSTEM_PROMPT, FINAL_TEXT, DIMS, OPTIONS, CELL_STYLE, CELL_ITEM, parse_lines  # noqa: E402,F401

REMOVED = ['boho|table', 'coastal|chandelier_pendant', 'traditional|wall_art']   # USER_DECISIONS ①
STYLES = ['mid_century', 'industrial', 'farmhouse_rustic', 'boho', 'coastal', 'traditional']
ITEMS = ['chair', 'table', 'lamp', 'chandelier_pendant', 'wall_art']
CELLS = [f'{s}|{i}' for s in STYLES for i in ITEMS if f'{s}|{i}' not in REMOVED]
assert len(CELLS) == 27
BUDGET_USD = 40.0
CALL_MARGIN_USD = 0.30     # 一次 20 張的呼叫最多約 $0.25；花費 + 這個餘裕 > $40 就不再呼叫，確保不超過上限
CONFIRM_RATE = 0.9         # RUNBOOK 3.2：Claude 說合格時本地模型至少一位同意的比例（階段 1 實測）
ANN1 = {'claude': S1 / 'ann_claude.jsonl', 'qwen': S1 / 'ann_qwen38-27b.jsonl', 'gemma': S1 / 'ann_gemma4-12b.jsonl'}
ANN2 = {'claude': S / 'ann_claude.jsonl', 'qwen': S / 'ann_qwen38-27b.jsonl', 'gemma': S / 'ann_gemma4-12b.jsonl'}
NAMES = {'claude': 'Claude Opus 5.5', 'qwen': 'Qwen3.8-27B-FP8', 'gemma': 'gemma-4-12b-it'}
CALL_FILES = [S / 'claude_calls.jsonl', S / 'single_item_calls.jsonl']


def target(cell):
    """目標合格數：wall_art 格 13，其他 26（RUNBOOK 第 2 節）。"""
    return 13 if cell.endswith('|wall_art') else 26


def claude_target0(cell):
    """第一階段的 Claude 目標數 = ceil(目標 ÷ 0.9) + 2（26 → 31，13 → 17）。"""
    return math.ceil(target(cell) / CONFIRM_RATE - 1e-9) + 2


def cell_labels(cell):
    s, i = cell.split('|')
    return CELL_STYLE[s], CELL_ITEM[i]


def read_jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    out = []
    for l in open(p, encoding='utf-8'):
        l = l.strip()
        if l:
            out.append(json.loads(l))
    return out


def load_ann(p):
    """id → 標註 dict（失敗 = None）。同一 id 多行時取第一行。"""
    out = {}
    for r in read_jsonl(p):
        if r['id'] not in out:
            out[r['id']] = r['ann'] if r.get('ok') else None
    return out


def stage1_items():
    """階段 1 的 900 件中屬於 27 格的 810 件（round = 0）。"""
    return [dict(r, round=0) for r in read_jsonl(S1 / 'sample.jsonl') if r['cell'] in CELLS]


def stage2_items():
    return read_jsonl(S / 'items.jsonl')


def claude_positive(cell, c):
    """Claude 正票：style = 格子風格、style_conf >= 2、category = 格子品項。"""
    cs, ci = cell_labels(cell)
    return bool(c and c['style'] == cs and c['style_conf'] >= 2 and c['category'] == ci)


def qualified(cell, c, q, g):
    """合格條件（USER_DECISIONS ⑨ / RUNBOOK 第 2 節）。標註失敗（None）算不同意。"""
    cs, ci = cell_labels(cell)
    if not (c and c['style'] == cs and c['style_conf'] >= 2):
        return False
    if sum(1 for x in (c, q, g) if x and x['style'] == cs) < 2:
        return False
    return sum(1 for x in (c, q, g) if x and x['category'] == ci) >= 2


def spent_usd():
    return sum((r.get('total_cost_usd') or 0) for f in CALL_FILES for r in read_jsonl(f))


def queue_by_cell():
    q = collections.defaultdict(list)
    for r in read_jsonl(S / 'queue.jsonl'):
        q[r['cell']].append(r)
    return q


def utcnow():
    import time
    return time.strftime('%F %H:%M', time.gmtime())


def progress(msg):
    with open(S / 'PROGRESS.md', 'a', encoding='utf-8') as f:
        f.write(f'[{utcnow()}] {msg}\n')
