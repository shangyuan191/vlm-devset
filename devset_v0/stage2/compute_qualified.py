"""3.4 合併階段 1（27 格 810 件）與階段 2 的三方標註 → annotations_all.jsonl、qualified.jsonl、cell_status.json。可重跑，結果固定。
用法： python3 -I compute_qualified.py
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common2 import *  # noqa: F401,F403


def main():
    ann = {}
    for a in ANN1:
        ann[a] = {**load_ann(ANN1[a]), **load_ann(ANN2[a])}
    items = stage1_items() + stage2_items()
    q = queue_by_cell()
    topup_done = len(json.load(open(S / 'topup_rounds.json'))) if (S / 'topup_rounds.json').exists() else 0
    cells = {c: {'labeled': 0, 'claude_pos': 0, 'qualified': 0, 'qualified_stage1': 0, 'qualified_stage2': 0, 'n_stage1': 0, 'n_stage2': 0,
                 'incomplete': 0, 'target': target(c)} for c in CELLS}
    rows = []
    for it in items:
        c = it['cell']; i = it['id']
        t = {a: ann[a].get(i) for a in ANN1}
        has = {a: i in ann[a] for a in ANN1}      # 該標註者是否已有紀錄（None = 標註失敗）
        complete = all(has.values())
        pos = claude_positive(c, t['claude'])
        qual = qualified(c, t['claude'], t['qwen'], t['gemma']) if complete else False
        v = cells[c]
        v['labeled'] += 1; v['claude_pos'] += pos; v['qualified'] += qual; v['incomplete'] += (not complete)
        k = 'stage1' if it['round'] == 0 else 'stage2'
        v['n_' + k] += 1; v['qualified_' + k] += qual
        rows.append({'id': i, 'cell': c, 'parent_asin': it['parent_asin'], 'round': it['round'], 'claude': t['claude'], 'qwen': t['qwen'], 'gemma': t['gemma'],
                     'complete': complete, 'claude_positive': pos, 'qualified': qual})
    with open(S / 'annotations_all.jsonl', 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(S / 'qualified.jsonl', 'w', encoding='utf-8') as f:
        for r in rows:
            if r['qualified']:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    issued = {c: 0 for c in CELLS}
    for it in stage2_items():
        issued[it['cell']] += 1
    out = {}
    for c in CELLS:
        v = cells[c]
        v['queue_total'] = len(q[c]); v['queue_left'] = len(q[c]) - issued[c]
        v['confirm_rate'] = round(v['qualified'] / v['claude_pos'], 4) if v['claude_pos'] else None
        if v['qualified'] >= v['target']:
            v['status'] = '達標'
        elif v['queue_left'] == 0 and v['incomplete'] == 0:
            v['status'] = '不足但已標完'
        elif topup_done >= 2 and v['incomplete'] == 0:
            v['status'] = '不足（補標 2 輪用完）'
        else:
            v['status'] = '進行中'
        out[c] = v
    tot = {'cells_done': sum(1 for v in out.values() if v['status'] == '達標'), 'n_cells': len(CELLS),
           'qualified_total': sum(v['qualified'] for v in out.values()), 'labeled_total': sum(v['labeled'] for v in out.values()), 'topup_rounds_done': topup_done}
    json.dump({'cells': out, 'total': tot}, open(S / 'cell_status.json', 'w'), ensure_ascii=False, indent=1)
    print(tot)
    for c, v in out.items():
        print(f"{c:34s} labeled {v['labeled']:4d} pos {v['claude_pos']:3d} qual {v['qualified']:3d}/{v['target']} left {v['queue_left']:3d} {v['status']}")


if __name__ == '__main__':
    main()
