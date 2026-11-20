"""階段 1 分析：三方標註 → 每格關鍵字準確率 / 一致率 / 可用量、各維度 κ、成本、階段 2 推估、人工抽查樣本。

用法： python3 -I devset_v0/stage1/analyze.py        （只用標準函式庫；結果固定，可重跑）
輸出： devset_v0/results/stage1_analysis.json、stage1_analysis.md、devset_v0/stage1/review_sample.json
"""
import collections
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import DIMS, OPTIONS, CELL_STYLE, CELL_ITEM  # noqa: E402

D = HERE.parent
ANN = {'claude': 'ann_claude.jsonl', 'qwen': 'ann_qwen38-27b.jsonl', 'gemma': 'ann_gemma4-12b.jsonl'}
NAMES = {'claude': 'Claude Opus 5.5', 'qwen': 'Qwen3.8-27B-FP8', 'gemma': 'gemma-4-12b-it'}
PAIRS = [('claude', 'qwen'), ('claude', 'gemma'), ('qwen', 'gemma')]
STYLES = ['mid_century', 'industrial', 'farmhouse_rustic', 'boho', 'coastal', 'traditional']
ITEMS = ['chair', 'table', 'lamp', 'chandelier_pendant', 'wall_art']
# 階段 2 規劃（見 main_table_draft.md 4.2：每題 12 個合格；開發集情境一、二各 50 題）
NEED_MIN = 13      # 方案 A：每格 12 個合格 + 1 張 query 圖（同格的題目共用合格商品）
NEED_NOREUSE = 26  # 方案 B：每格 2 題、合格商品不重複使用（2 × 13）
QUOTA_USD = (10, 15)  # 1 個「五小時額度」約 10–15 美元（經驗值，不是實測）


def load(fn):
    out = {}
    p = HERE / fn
    if p.exists():
        for l in open(p, encoding='utf-8'):
            r = json.loads(l)
            out[r['id']] = r
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def fleiss(rows, cats):
    """rows：每件商品 3 位標註者的值（list of 3）。回傳 Fleiss kappa。"""
    n, N = 3, len(rows)
    if N == 0:
        return None
    tot = collections.Counter()
    P = 0.0
    for r in rows:
        c = collections.Counter(r)
        tot.update(c)
        P += (sum(v * v for v in c.values()) - n) / (n * (n - 1))
    P /= N
    Pe = sum((tot[c] / (N * n)) ** 2 for c in cats)
    return (P - Pe) / (1 - Pe) if Pe < 1 else 1.0


def majority(vals):
    c = collections.Counter(v for v in vals if v is not None).most_common(1)
    return c[0][0] if c and c[0][1] >= 2 else None


def r3(x):
    return None if x is None else round(x, 4)


def main():
    sample = [json.loads(l) for l in open(HERE / 'sample.jsonl', encoding='utf-8')]
    raw = {a: load(f) for a, f in ANN.items()}
    ann = {a: {i: (r['ann'] if r.get('ok') else None) for i, r in raw[a].items()} for a in ANN}
    cc = json.load(open(D / 'stage0' / 'cell_counts.json'))['cells']
    A = list(ANN)
    status = {a: {'n_records': len(raw[a]), 'n_ok': sum(1 for v in ann[a].values() if v), 'n_failed': sum(1 for v in ann[a].values() if v is None),
                  'n_missing': sum(1 for s in sample if s['id'] not in raw[a])} for a in A}

    def get(a, i, k):
        v = ann[a].get(i)
        return v[k] if v else None

    # ---------------- 每格
    cells, per_item = {}, {}
    for s in sample:
        i = s['id']
        st = [get(a, i, 'style') for a in A]
        cf = [get(a, i, 'style_conf') for a in A]
        ct = [get(a, i, 'category') for a in A]
        tgt_s, tgt_c = CELL_STYLE[s['kw_style']], CELL_ITEM[s['item']]
        complete = all(v is not None for v in st)
        unan = complete and len(set(st)) == 1
        per_item[i] = {
            'complete': complete, 'maj_style': majority(st), 'maj_cat': majority(ct), 'unanimous_style': unan,
            'kw_correct': majority(st) == tgt_s,
            'qualified': unan and st[0] == tgt_s and min(cf) >= 2,
            'qualified_with_cat': unan and st[0] == tgt_s and min(cf) >= 2 and all(c == tgt_c for c in ct),
            'cat_mismatch_majority': majority(ct) != tgt_c, 'cat_mismatch_any': any(c != tgt_c for c in ct),
            'n_distinct_style': len(set(v for v in st if v is not None)), 'any_conf1': any(c == 1 for c in cf if c is not None),
        }
    for stl in STYLES:
        for it in ITEMS:
            c = f'{stl}|{it}'
            ids = [s['id'] for s in sample if s['cell'] == c]
            n = len(ids)
            k = {m: sum(per_item[i][m] for i in ids) for m in ('kw_correct', 'unanimous_style', 'qualified', 'qualified_with_cat',
                                                                'cat_mismatch_majority', 'cat_mismatch_any', 'complete')}
            lo, hi = wilson(k['qualified'], n)
            hits, dd = cc[c]['kw_hits'], cc[c]['after_title_dedup']
            pc = k['qualified'] / n
            q_ids = [i for i in ids if per_item[i]['qualified_with_cat']]
            distinct = {d: len({majority([get(a, i, d) for a in A]) for i in q_ids} - {None}) for d in ('color', 'material', 'shape')}
            est_dd = dd * pc
            # 建議：用 (c2)（風格合格且品項正確）乘「去重後數量」估這一格到底有多少件合格商品
            p2 = k['qualified_with_cat'] / n
            lo2 = wilson(k['qualified_with_cat'], n)[0]
            sup, sup_lo = dd * p2, dd * lo2
            if sup < NEED_MIN:
                verdict = '建議拿掉（合格商品估計不到 13 件）'
            elif sup < NEED_NOREUSE or sup_lo < NEED_MIN:
                verdict = '勉強（量少：估計 13–26 件，或 95% 下界不到 13 件）'
            elif p2 < 0.2:
                verdict = '可留但貴（合格率 < 20%，要標很多件）'
            else:
                verdict = '保留'
            cells[c] = {
                'n': n, 'n_all3_valid': k['complete'], 'kw_hits': hits, 'after_title_dedup': dd, 'in_pool': cc[c]['in_pool'],
                'a_kw_accuracy': r3(k['kw_correct'] / n), 'b_unanimous_style': r3(k['unanimous_style'] / n),
                'c_qualified': r3(pc), 'c_qualified_k': k['qualified'], 'c_ci95': [r3(lo), r3(hi)],
                'c2_qualified_and_item_ok': r3(k['qualified_with_cat'] / n), 'c2_k': k['qualified_with_cat'],
                'd_usable_est': round(hits * pc), 'd_usable_ci95': [round(hits * lo), round(hits * hi)],
                'd_usable_est_dedup': round(est_dd), 'd_usable_dedup_ci95': [round(dd * lo), round(dd * hi)],
                'supply_c2_est': round(sup), 'supply_c2_ci_low': round(sup_lo),
                'e_item_mismatch_majority': r3(k['cat_mismatch_majority'] / n), 'e_item_mismatch_any': r3(k['cat_mismatch_any'] / n),
                'majority_style_dist': dict(collections.Counter(per_item[i]['maj_style'] or '(無多數)' for i in ids).most_common()),
                'distinct_values_among_c2': distinct, 'verdict': verdict,
            }

    def agg(keys):
        ids = [s['id'] for s in sample if s['cell'] in keys]
        n = len(ids)
        return {'n': n, 'a_kw_accuracy': r3(sum(per_item[i]['kw_correct'] for i in ids) / n),
                'b_unanimous_style': r3(sum(per_item[i]['unanimous_style'] for i in ids) / n),
                'c_qualified': r3(sum(per_item[i]['qualified'] for i in ids) / n),
                'c2_qualified_and_item_ok': r3(sum(per_item[i]['qualified_with_cat'] for i in ids) / n),
                'e_item_mismatch_majority': r3(sum(per_item[i]['cat_mismatch_majority'] for i in ids) / n)}
    by_style = {s: agg([f'{s}|{i}' for i in ITEMS]) for s in STYLES}
    by_item = {i: agg([f'{s}|{i}' for s in STYLES]) for i in ITEMS}
    overall = agg(list(cells))
    # 各標註者自己的「風格 = 格子風格」比例
    per_annotator_kw = {a: r3(sum(get(a, s['id'], 'style') == CELL_STYLE[s['kw_style']] for s in sample) / len(sample)) for a in A}

    # ---------------- 每個維度
    full_ids = [s['id'] for s in sample if all(ann[a].get(s['id']) for a in A)]
    dims = {}
    for d in DIMS:
        rows = [[ann[a][i][d] for a in A] for i in full_ids]
        dims[d] = {
            'n_items_all3_valid': len(rows), 'fleiss_kappa': r3(fleiss(rows, OPTIONS[d])),
            'unanimous': r3(sum(len(set(r)) == 1 for r in rows) / len(rows)) if rows else None,
            'pairwise': {f'{x}-{y}': r3(sum(ann[x][i][d] == ann[y][i][d] for i in full_ids) / len(full_ids)) if full_ids else None for x, y in PAIRS},
            'conf_dist': {a: {str(c): sum(1 for v in ann[a].values() if v and v[f'{d}_conf'] == c) for c in (1, 2, 3)} for a in A},
            'value_dist': {a: dict(collections.Counter(v[d] for v in ann[a].values() if v).most_common()) for a in A},
        }
    # 風格的常見分歧配對（哪兩個風格最常被不同標註者分別選）
    conf_pairs = collections.Counter()
    for i in full_ids:
        vs = sorted({ann[a][i]['style'] for a in A})
        for x in range(len(vs)):
            for y in range(x + 1, len(vs)):
                conf_pairs[f'{vs[x]} ↔ {vs[y]}'] += 1
    # 關鍵字風格 → Claude 標的風格（列 = 格子風格）
    kw_vs = {a: {s: dict(collections.Counter(get(a, x['id'], 'style') or '(失敗)' for x in sample if x['kw_style'] == s).most_common()) for s in STYLES} for a in A}

    # ---------------- 成本
    calls = [json.loads(l) for l in open(HERE / 'claude_calls.jsonl', encoding='utf-8')] if (HERE / 'claude_calls.jsonl').exists() else []
    main_calls = [c for c in calls if c['tag'].startswith('main')]
    re_calls = [c for c in calls if c['tag'].startswith('recheck')]

    def tok(cs):
        u = collections.Counter()
        for c in cs:
            x = c.get('usage') or {}
            u['input'] += x.get('input_tokens', 0); u['cache_write'] += x.get('cache_creation_input_tokens', 0)
            u['cache_read'] += x.get('cache_read_input_tokens', 0); u['output'] += x.get('output_tokens', 0)
            u['thinking'] += (x.get('output_tokens_details') or {}).get('thinking_tokens', 0)
        return dict(u)
    n_claude_ok = status['claude']['n_ok']
    main_cost = sum(c.get('total_cost_usd') or 0 for c in main_calls)
    mt = tok(main_calls)
    claude_cost = {
        'n_calls_main': len(main_calls), 'n_calls_limited': sum(1 for c in main_calls if c.get('limited')),
        'n_calls_resend': sum(1 for c in main_calls if 'resend' in c['tag']),
        'n_items_ok': n_claude_ok, 'usd_main_total': round(main_cost, 4),
        'usd_per_item': r3(main_cost / n_claude_ok) if n_claude_ok else None,
        'tokens_main_total': mt, 'tokens_per_item': {k: round(v / n_claude_ok, 1) for k, v in mt.items()} if n_claude_ok else None,
        'wall_s_per_item': r3(sum(c['wall_s'] for c in main_calls) / n_claude_ok) if n_claude_ok else None,
        'models_seen': sorted({m for c in calls for m in c.get('models_seen', []) if m != '<synthetic>'}),
        'recheck': {'n_calls': len(re_calls), 'usd_total': round(sum(c.get('total_cost_usd') or 0 for c in re_calls), 4)},
        'usd_all_calls': round(sum(c.get('total_cost_usd') or 0 for c in calls), 4),
    }
    local = {}
    for a in ('qwen', 'gemma'):
        rs = list(raw[a].values())
        lat = [sum(t['latency_s'] for t in r['tries']) for r in rs]
        pt = [r['tries'][0]['usage']['prompt_tokens'] for r in rs if r['tries'][0].get('usage')]
        local[a] = {'n': len(rs), 'n_ok': sum(r['ok'] for r in rs), 'n_retried': sum(len(r['tries']) > 1 for r in rs),
                    'sec_per_item_mean': r3(sum(lat) / len(lat)) if lat else None, 'total_min': r3(sum(lat) / 60),
                    'prompt_tokens_mean': round(sum(pt) / len(pt), 1) if pt else None,
                    'failure_reasons': dict(collections.Counter(e.split(' ::')[0] for r in rs if not r['ok'] for e in r['tries'][-1]['errors']).most_common())}

    # 批量檢查（每批 20 vs 每批 5）
    rc = load('ann_claude_recheck5.jsonl')
    ids = [i for i, r in rc.items() if r.get('ok') and ann['claude'].get(i)]
    recheck = {'n': len(ids), 'agreement': {d: r3(sum(ann['claude'][i][d] == rc[i]['ann'][d] for i in ids) / len(ids)) for d in DIMS} if ids else {}}

    # ---------------- 階段 2 推估
    usd = claude_cost['usd_per_item'] or 0
    plan = {}
    for name, need in (('A_每格13件合格（同格題目共用）', NEED_MIN), ('B_每格26件合格（2題不重複）', NEED_NOREUSE)):
        rows, tot_new, infeasible, capped = {}, 0, [], []
        for c, v in cells.items():
            p, lo = v['c2_qualified_and_item_ok'], wilson(v['c2_k'], v['n'])[0]
            if p == 0:
                infeasible.append(c); rows[c] = {'need_total': None, 'new': 0, 'feasible': False}; continue
            n_tot = math.ceil(need / p)
            cap = v['after_title_dedup']
            feas = n_tot <= cap
            if not feas:
                capped.append(c)
            n_tot_c = min(n_tot, cap)
            new = max(0, n_tot_c - v['n'])
            tot_new += new
            rows[c] = {'need_total': n_tot, 'annotate_total_capped': n_tot_c, 'new': new, 'feasible': feas,
                       'need_total_if_ci_low': math.ceil(need / lo) if lo > 0 else None}
        plan[name] = {'need_qualified_per_cell': need, 'new_items_to_annotate': tot_new, 'cells_infeasible_c0': infeasible,
                      'cells_capped_by_supply': capped, 'claude_usd': round(tot_new * usd, 2),
                      'quotas_5h': [round(tot_new * usd / QUOTA_USD[1], 1), round(tot_new * usd / QUOTA_USD[0], 1)],
                      'qwen_hours': r3(tot_new * (local['qwen']['sec_per_item_mean'] or 0) / 3600),
                      'gemma_hours': r3(tot_new * (local['gemma']['sec_per_item_mean'] or 0) / 3600), 'per_cell': rows}
    n_pool_cells = sum(v['in_pool'] for v in cells.values())
    plan['C_標完整個商品池（格子部分）'] = {'new_items_to_annotate': n_pool_cells - len(sample), 'claude_usd': round((n_pool_cells - len(sample)) * usd, 2),
                                  'quotas_5h': [round((n_pool_cells - len(sample)) * usd / QUOTA_USD[1], 1), round((n_pool_cells - len(sample)) * usd / QUOTA_USD[0], 1)],
                                  'qwen_hours': r3((n_pool_cells - len(sample)) * (local['qwen']['sec_per_item_mean'] or 0) / 3600),
                                  'gemma_hours': r3((n_pool_cells - len(sample)) * (local['gemma']['sec_per_item_mean'] or 0) / 3600)}

    # ---------------- 人工抽查樣本：每格 2 件，優先三方不一致
    review = []
    for stl in STYLES:
        for it in ITEMS:
            c = f'{stl}|{it}'
            rows = [s for s in sample if s['cell'] == c]

            def prio(s):
                p = per_item[s['id']]
                if not p['complete']:
                    return 1
                if p['n_distinct_style'] == 3:
                    return 0
                if p['n_distinct_style'] == 2:
                    return 1
                return 2 if p['any_conf1'] else 3
            rnd = random.Random(f'0-review-{c}')
            rows = sorted(rows, key=lambda s: (prio(s), rnd.random()))
            for s in rows[:2]:
                p = per_item[s['id']]
                review.append({'id': s['id'], 'parent_asin': s['parent_asin'], 'cell': c, 'kw_style': CELL_STYLE[s['kw_style']],
                               'rule_item': CELL_ITEM[s['item']], 'title': s['title'], 'image_768': f"devset_v0/stage1/{s['ann_image']}",
                               'image_original': s['image_path'], 'url': f"https://www.amazon.com/dp/{s['parent_asin']}",
                               'why_picked': ['三方風格各不相同', '風格 2 比 1 或有標註失敗', '三方一致但有人信心 1', '三方一致'][prio(s)],
                               'annotations': {a: ann[a].get(s['id']) for a in A}, 'majority_style': p['maj_style'],
                               'human': {'style': None, 'category': None, 'color': None, 'material': None, 'shape': None, 'note': ''}})
    (HERE / 'review_sample.json').write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding='utf-8')

    out = {'n_sample': len(sample), 'annotators': NAMES, 'annotation_status': status, 'overall': overall, 'per_annotator_kw_accuracy': per_annotator_kw,
           'cells': cells, 'by_style': by_style, 'by_item': by_item, 'dims': dims, 'style_disagreement_pairs': dict(conf_pairs.most_common(15)),
           'kw_style_vs_annotator_style': kw_vs, 'claude_cost': claude_cost, 'local_cost': local, 'batch_size_recheck': recheck,
           'stage2_plan': plan, 'quota_usd_assumption': list(QUOTA_USD),
           'review_sample': {'n': len(review), 'why': dict(collections.Counter(r['why_picked'] for r in review))}}
    (D / 'results').mkdir(exist_ok=True)
    (D / 'results' / 'stage1_analysis.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    # ---------------- Markdown
    pct = lambda x: '—' if x is None else f'{100 * x:.0f}%'  # noqa: E731
    L = ['# 階段 1 分析（自動產生：`python3 -I devset_v0/stage1/analyze.py`）', '',
         f"樣本 {len(sample)} 件（30 格 × 30）。標註狀態：" + '；'.join(f"{NAMES[a]} 成功 {status[a]['n_ok']}、失敗 {status[a]['n_failed']}、未標 {status[a]['n_missing']}" for a in A), '',
         '## 表 1：30 格', '',
         '欄位：(a) 多數決風格 = 格子風格；(b) 三位風格完全一致；(c) 三位一致 = 格子風格且無人信心 1；(c2) = (c) 且三位品項都 = 規則品項；(d) 命中總數 × (c)，括號是 95% 區間（Wilson，n=30）；(e) 多數決品項 ≠ 規則品項。標註失敗的商品在 (b)(c) 算「不一致」。', '',
         '| 格子 | 命中總數 | 去重後 | (a) 關鍵字準確率 | (b) 三方一致 | (c) 可當合格 | (c) 95% 區間 | (c2) | (d) 推估可用量（命中） | (d) 去重後 | (e) 品項不符 | 建議 |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c, v in cells.items():
        L.append(f"| {c.replace('|', ' × ')} | {v['kw_hits']:,} | {v['after_title_dedup']:,} | {pct(v['a_kw_accuracy'])} | {pct(v['b_unanimous_style'])} | {pct(v['c_qualified'])}（{v['c_qualified_k']}/30） | {pct(v['c_ci95'][0])}–{pct(v['c_ci95'][1])} | {pct(v['c2_qualified_and_item_ok'])} | {v['d_usable_est']:,}（{v['d_usable_ci95'][0]:,}–{v['d_usable_ci95'][1]:,}） | {v['d_usable_est_dedup']:,}（{v['d_usable_dedup_ci95'][0]:,}–{v['d_usable_dedup_ci95'][1]:,}） | {pct(v['e_item_mismatch_majority'])} | {v['verdict']} |")
    L += ['', '## 表 2：依風格、依品項彙總', '', '| 分組 | n | (a) | (b) | (c) | (c2) | (e) |', '|---|---|---|---|---|---|---|']
    for k, v in list(by_style.items()) + list(by_item.items()) + [('全部', overall)]:
        L.append(f"| {k} | {v['n']} | {pct(v['a_kw_accuracy'])} | {pct(v['b_unanimous_style'])} | {pct(v['c_qualified'])} | {pct(v['c2_qualified_and_item_ok'])} | {pct(v['e_item_mismatch_majority'])} |")
    L += ['', '各標註者自己標的風格 = 格子風格的比例：' + '、'.join(f'{NAMES[a]} {pct(per_annotator_kw[a])}' for a in A), '',
          '## 表 3：各維度一致性', '', f"只用三位都有合法標註的 {len(full_ids)} 件。", '',
          '| 維度 | Fleiss κ | 三方一致 | Claude–Qwen | Claude–Gemma | Qwen–Gemma | 信心 1/2/3：Claude | Qwen | Gemma |', '|---|---|---|---|---|---|---|---|---|']
    for d in DIMS:
        v = dims[d]
        cd = lambda a: '/'.join(str(v['conf_dist'][a][c]) for c in '123')  # noqa: E731
        L.append(f"| {d} | {v['fleiss_kappa']:.2f} | {pct(v['unanimous'])} | {pct(v['pairwise']['claude-qwen'])} | {pct(v['pairwise']['claude-gemma'])} | {pct(v['pairwise']['qwen-gemma'])} | {cd('claude')} | {cd('qwen')} | {cd('gemma')} |")
    L += ['', '最常見的風格分歧配對（同一件商品被不同標註者分別選了這兩個風格的件數）：', '']
    L += [f'- {k}：{v}' for k, v in conf_pairs.most_common(10)]
    L += ['', '## 表 4：每格多數決風格的分布（看關鍵字錯的時候被標成什麼）', '', '| 格子 | 多數決風格分布 |', '|---|---|']
    for c, v in cells.items():
        L.append(f"| {c.replace('|', ' × ')} | " + '、'.join(f'{k} {n}' for k, n in v['majority_style_dist'].items()) + ' |')
    cl = claude_cost
    L += ['', '## 成本', '',
          f"- Claude（{'、'.join(cl['models_seen'])}）：主標註 {cl['n_calls_main']} 次呼叫（其中 {cl['n_calls_limited']} 次碰到用量上限、{cl['n_calls_resend']} 次是重送），成功 {cl['n_items_ok']} 件，共 ${cl['usd_main_total']:.2f}，**每件 ${cl['usd_per_item']:.4f}**；每件 tokens：{cl['tokens_per_item']}；每件 {cl['wall_s_per_item']} 秒。批量檢查另花 ${cl['recheck']['usd_total']:.2f}；全部呼叫合計 ${cl['usd_all_calls']:.2f}。",
          f"- 批量檢查（每批 20 vs 每批 5，{recheck['n']} 件）一致率：{recheck['agreement']}"]
    for a in ('qwen', 'gemma'):
        v = local[a]
        L.append(f"- {NAMES[a]}：{v['n']} 件、成功 {v['n_ok']}、重試過 {v['n_retried']}；每件 {v['sec_per_item_mean']:.2f} 秒（共 {v['total_min']:.0f} 分鐘）；每件輸入約 {v['prompt_tokens_mean']} tokens。失敗原因：{v['failure_reasons'] or '無'}")
    L += ['', '## 階段 2 推估', '', f'用 (c2)（風格合格且品項正確）的點估計；每格最多標到「去重後數量」。1 個五小時額度 ≈ ${QUOTA_USD[0]}–{QUOTA_USD[1]}（經驗值）。', '',
          '| 方案 | 還要新標幾件 | Claude 美元 | 五小時額度數 | Qwen 小時 | Gemma 小時 | 做不到的格子（c2 = 0） | 商品不夠的格子 |', '|---|---|---|---|---|---|---|---|']
    for k, v in plan.items():
        L.append(f"| {k} | {v['new_items_to_annotate']:,} | ${v['claude_usd']:.0f} | {v['quotas_5h'][0]}–{v['quotas_5h'][1]} | {v['qwen_hours']:.1f} | {v['gemma_hours']:.1f} | {'、'.join(v.get('cells_infeasible_c0', [])) or '—'} | {'、'.join(v.get('cells_capped_by_supply', [])) or '—'} |")
    L += ['', '每格需要標的總件數（方案 A / B；括號 = 用 (c2) 的 95% 下界算）與合格商品在自由維度上的不同值數：', '',
          '| 格子 | (c2) | A 總件數 | B 總件數 | 去重後數量 | 合格商品的不同值數（color / material / shape） |', '|---|---|---|---|---|---|']
    for c, v in cells.items():
        a_, b_ = plan['A_每格13件合格（同格題目共用）']['per_cell'][c], plan['B_每格26件合格（2題不重複）']['per_cell'][c]
        f = lambda r: '做不到' if r['need_total'] is None else f"{r['need_total']}（{r['need_total_if_ci_low'] or '∞'}）"  # noqa: E731
        dv = v['distinct_values_among_c2']
        L.append(f"| {c.replace('|', ' × ')} | {v['c2_k']}/30 | {f(a_)} | {f(b_)} | {v['after_title_dedup']:,} | {dv['color']} / {dv['material']} / {dv['shape']} |")
    L += ['', f"人工抽查樣本：`stage1/review_sample.json`，{len(review)} 件（{dict(collections.Counter(r['why_picked'] for r in review))}）。", '']
    (D / 'results' / 'stage1_analysis.md').write_text('\n'.join(L), encoding='utf-8')
    print('wrote results; overall', overall, status)


if __name__ == '__main__':
    main()
