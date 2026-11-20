"""階段 3 A 節：補標緩衝。沿用 stage2 的 annotate_claude2（issue_round / run_round）；Claude 預算 = 階段 3 開始時累計 + $5。
用法： python3 -I topup_a.py plan|claude|single     （compute_qualified 與本地標註另外跑）
"""
import json, math, sys
from pathlib import Path
T = Path(__file__).resolve().parent
sys.path.insert(0, str(T.parent / 'stage2'))
sys.dont_write_bytecode = True
import annotate_claude2 as ac
import annotate_single_item as asi
from common2 import *  # noqa
BASE = json.load(open(T / 'budget_base.json'))['spent_at_start'] if (T / 'budget_base.json').exists() else None
if BASE is None:
    BASE = spent_usd(); json.dump({'spent_at_start': BASE}, open(T / 'budget_base.json', 'w'))
ac.BUDGET_USD = asi.BUDGET_USD = BASE + 5.0
BUFFER_CELLS = ['mid_century|lamp', 'coastal|table', 'farmhouse_rustic|chandelier_pendant', 'mid_century|wall_art']
CHAIR = 'industrial|chair'


def single_yes(cell):
    si = {r['id']: r for r in read_jsonl(S / 'ann_single_item.jsonl')}
    n = 0
    for r in read_jsonl(S / 'qualified.jsonl'):
        if r['cell'] == cell:
            s = si.get(r['id'])
            n += bool(s and s.get('ok') and s['single_item'] == 'yes' and s['single_item_conf'] >= 2)
    return n


def plan():
    cs = json.load(open(S / 'cell_status.json'))['cells']
    st = ac.cell_state(); take = {}
    for c in CELLS:
        v = cs[c]; tgt = v['target'] + 4
        deficit = tgt - v['qualified']
        if c == CHAIR:
            new = sum(1 for it in stage2_items() if it['cell'] == c and it['round'] >= 5)
            y = single_yes(c)
            if y >= 13 or new >= 100 or v['queue_left'] <= 0:
                continue
            need = 13 - y
            per_label = (v['qualified'] / v['labeled']) * max(y / max(v['qualified'], 1), 0.1)   # 每標一件預期增加幾個 single yes
            k = math.ceil(need / per_label * 1.1)
            take[c] = min(k, 100 - new, v['queue_left']); continue
        if c not in BUFFER_CELLS or deficit <= 0 or v['queue_left'] <= 0:
            continue
        conf = v['confirm_rate'] or CONFIRM_RATE
        need_pos = math.ceil(deficit / max(conf, 0.3)) + 2
        rate = st[c]['pos'] / st[c]['labeled'] if st[c]['labeled'] else 0
        take[c] = min(40 if rate == 0 else max(10, math.ceil(need_pos / rate)), v['queue_left'])
    return take


if __name__ == '__main__':
    mode = sys.argv[1]
    try:
        if mode == 'plan':
            print(plan())
        elif mode == 'claude':
            for it in {it['round'] for it in stage2_items()}:
                ac.run_round(it)
            take = plan()
            if take:
                rnd = max(it['round'] for it in stage2_items()) + 1
                progress(f'階段3/A Claude 第 {rnd} 輪 — 發出 {sum(take.values())} 件（{take}）')
                ac.issue_round(take, rnd); ac.run_round(rnd)
            print('claude done; spent since start', spent_usd() - BASE)
        elif mode == 'single':
            asi.main()
    except ac.Limit:
        sys.exit(75)
    except (ac.Budget, asi.Budget) as e:
        print('BUDGET', e); sys.exit(76)
