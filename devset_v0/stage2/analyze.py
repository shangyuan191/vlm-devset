"""階段 2 分析：每格合格數、合格率（階段 1 vs 2）、合格商品屬性分布與情境二自由維度、單一商品候選數、三方一致性、成本。
用法： python3 -I devset_v0/stage2/analyze.py     （先跑 compute_qualified.py；結果固定，可重跑）
輸出： S/results/stage2_analysis.json、stage2_analysis.md
"""
import collections
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common2 import *  # noqa: F401,F403

PAIRS = [('claude', 'qwen'), ('claude', 'gemma'), ('qwen', 'gemma')]
ATTRS = ['color', 'material', 'shape']


def fleiss(rows, cats):
    n, N = 3, len(rows)
    if N == 0:
        return None
    tot = collections.Counter(); P = 0.0
    for r in rows:
        c = collections.Counter(r); tot.update(c)
        P += (sum(v * v for v in c.values()) - n) / (n * (n - 1))
    P /= N
    Pe = sum((tot[c] / (N * n)) ** 2 for c in cats)
    return (P - Pe) / (1 - Pe) if Pe < 1 else 1.0


def agreement(rows3, dims=DIMS):
    """rows3：每件 {claude, qwen, gemma}（三位都成功）。回傳每維度 κ 與兩兩一致率。"""
    out = {}
    for d in dims:
        vals = [[r[a][d] for a in ('claude', 'qwen', 'gemma')] for r in rows3]
        out[d] = {'kappa': fleiss(vals, OPTIONS[d]), 'n': len(vals),
                  'pairs': {f'{a}-{b}': (sum(1 for r in rows3 if r[a][d] == r[b][d]) / len(rows3) if rows3 else None) for a, b in PAIRS}}
    return out


def mode_of(vals):
    c = collections.Counter(v for v in vals if v is not None).most_common(1)
    return c[0][0] if c and c[0][1] >= 2 else None


def main():
    cs = json.load(open(S / 'cell_status.json'))
    rows = read_jsonl(S / 'annotations_all.jsonl')
    single = {r['id']: r for r in read_jsonl(S / 'ann_single_item.jsonl') if r.get('ok')}
    by_cell = collections.defaultdict(list)
    for r in rows:
        by_cell[r['cell']].append(r)

    cells = {}
    for c in CELLS:
        v = dict(cs['cells'][c]); R_ = by_cell[c]
        for k, rd in (('stage1', lambda r: r['round'] == 0), ('stage2', lambda r: r['round'] > 0)):
            sub = [r for r in R_ if rd(r)]
            v[f'{k}_n'] = len(sub); v[f'{k}_qualified'] = sum(r['qualified'] for r in sub)
            v[f'{k}_qualified_rate'] = round(v[f'{k}_qualified'] / len(sub), 4) if sub else None
            v[f'{k}_claude_pos_rate'] = round(sum(r['claude_positive'] for r in sub) / len(sub), 4) if sub else None
        Q = [r for r in R_ if r['qualified']]
        attrs = {}
        for d in ATTRS:
            maj = [mode_of([r[a][d] for a in ('claude', 'qwen', 'gemma') if r[a]]) for r in Q]
            cnt = collections.Counter(m for m in maj if m is not None)
            attrs[d] = {'n_values': len(cnt), 'values': dict(cnt.most_common()), 'n_no_majority': sum(1 for m in maj if m is None)}
        v['attrs'] = attrs
        # 情境二自由維度（USER_DECISIONS ③）：合格商品中 >= 2 種值；wall_art 不出情境二
        v['scenario2'] = None if c.endswith('|wall_art') else {'free_dims': {d: attrs[d]['n_values'] for d in ATTRS if attrs[d]['n_values'] >= 2},
                                                              'n_free': sum(1 for d in ATTRS if attrs[d]['n_values'] >= 2)}
        v['single_item_yes_conf2'] = sum(1 for r in Q if single.get(r['id'], {}).get('single_item') == 'yes' and single[r['id']]['single_item_conf'] >= 2)
        v['single_item_labeled'] = sum(1 for r in Q if r['id'] in single)
        v['scene'] = dict(collections.Counter(single[r['id']]['scene'] for r in Q if r['id'] in single))
        cells[c] = v

    def three(rs):
        return [r for r in rs if r['claude'] and r['qwen'] and r['gemma']]
    s1 = three([r for r in rows if r['round'] == 0]); s2 = three([r for r in rows if r['round'] > 0])
    consistency = {'stage1_27cells': {'n_items': len([r for r in rows if r['round'] == 0]), 'n_all3_ok': len(s1), **{'dims': agreement(s1)}},
                   'stage2_new': {'n_items': len([r for r in rows if r['round'] > 0]), 'n_all3_ok': len(s2), **{'dims': agreement(s2)}}}
    fail = {a: sum(1 for r in rows if r['complete'] and not r[a]) for a in ('claude', 'qwen', 'gemma')}

    # 成本
    def cost(files):
        recs = [r for f in files for r in read_jsonl(f)]
        return {'usd': round(sum(r.get('total_cost_usd') or 0 for r in recs), 4), 'calls': len(recs), 'limited_calls': sum(1 for r in recs if r.get('limited')),
                'output_tokens': sum(((r.get('usage') or {}).get('output_tokens') or 0) for r in recs),
                'cache_creation_tokens': sum(((r.get('usage') or {}).get('cache_creation_input_tokens') or 0) for r in recs)}
    main_c = cost([S / 'claude_calls.jsonl']); single_c = cost([S / 'single_item_calls.jsonl'])
    n_main = len(stage2_items()); n_single = len(single)
    main_c['per_item_usd'] = round(main_c['usd'] / n_main, 5) if n_main else None
    single_c['per_item_usd'] = round(single_c['usd'] / n_single, 5) if n_single else None
    local = {}
    for a in ('qwen', 'gemma'):
        recs = read_jsonl(ANN2[a]); secs = [sum(t['latency_s'] for t in r['tries']) for r in recs]
        local[a] = {'n': len(recs), 'total_hours': round(sum(secs) / 3600, 3), 'sec_per_item': round(sum(secs) / len(secs), 2) if secs else None,
                    'failed': sum(1 for r in recs if not r['ok'])}
    tot_cost = round(main_c['usd'] + single_c['usd'], 4)

    res = {'cells': cells, 'total': cs['total'], 'consistency': consistency, 'failed_annotations_in_complete_items': fail,
           'cost': {'claude_main': main_c, 'claude_single_item': single_c, 'claude_total_usd': tot_cost, 'budget_usd': BUDGET_USD, 'local': local,
                    'n_stage2_items': n_main, 'n_single_labeled': n_single},
           'summary': {'qualified_total': sum(v['qualified'] for v in cells.values()), 'target_total': sum(v['target'] for v in cells.values()),
                       'cells_met': [c for c, v in cells.items() if v['status'] == '達標'],
                       'cells_short': [c for c, v in cells.items() if v['status'] != '達標'],
                       'single_item_candidates_total': sum(v['single_item_yes_conf2'] for v in cells.values())}}
    (S / 'results').mkdir(exist_ok=True)
    json.dump(res, open(S / 'results' / 'stage2_analysis.json', 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    L = ['# 階段 2 分析（由 analyze.py 產生）', '', f"合格商品 {res['summary']['qualified_total']} / 目標 {res['summary']['target_total']}；Claude 花費 ${tot_cost}（主標註 ${main_c['usd']}、單一商品欄位 ${single_c['usd']}）", '',
         '| 格子 | 已標 | Claude 正票 | 合格/目標 | 狀態 | 階段1合格率 | 階段2合格率 | queue 剩 | 單一商品候選 | 情境二自由維度 |', '|---|---|---|---|---|---|---|---|---|---|']
    pc = lambda x: '-' if x is None else f'{100 * x:.0f}%'  # noqa: E731
    for c, v in cells.items():
        fd = '（不出情境二）' if v['scenario2'] is None else ', '.join(f'{d}:{n}' for d, n in v['scenario2']['free_dims'].items()) or '無'
        L.append(f"| {c} | {v['labeled']} | {v['claude_pos']} | {v['qualified']}/{v['target']} | {v['status']} | {pc(v['stage1_qualified_rate'])} | {pc(v['stage2_qualified_rate'])} | {v['queue_left']} | {v['single_item_yes_conf2']} | {fd} |")
    L += ['', '## 三方一致性（κ / 兩兩一致率）']
    for k, v in consistency.items():
        L.append(f"- {k}：三位都成功 {v['n_all3_ok']} 件")
        for d, x in v['dims'].items():
            L.append(f"  - {d}: κ={x['kappa'] if x['kappa'] is None else round(x['kappa'], 3)}；" + '、'.join(f'{p}={pc(q)}' for p, q in x['pairs'].items()))
    (S / 'results' / 'stage2_analysis.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('ok', res['summary']['qualified_total'], res['summary']['target_total'])


if __name__ == '__main__':
    main()
