"""D 節：計分。python3 -I score.py → results/scores.json、results/scores.md（可重跑，結果固定）。"""
import collections, itertools, json, random, statistics, sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
T = Path(__file__).resolve().parent; R = T.parent.parent
sys.path.insert(0, str(R / 'overnight_2026-11-14' / 'D_main_table'))
import metrics as M
K = 5; ORDERS = ['o0', 'o1', 'o2']; DIMS3 = ['color', 'material', 'shape']
MODELS = ['qwen38-27b', 'qwen36-35b', 'gemma4-12b', 'qwen35-9b', 'qwen35-4b', 'internvl35-1tile', 'llavaov2-8b']
BASE = ['siglip2-top5', 'siglip2-mmr-free', 'siglip2-mmr-std']
QS = json.load(open(T / 'questions.json')); QD = {q['qid']: q for q in QS}
STYLES = ['mid-century modern', 'industrial', 'farmhouse/rustic', 'bohemian', 'coastal', 'traditional']


def mean(x):
    x = [v for v in x if v is not None]
    return sum(x) / len(x) if x else None


def sd(x):
    x = [v for v in x if v is not None]
    return statistics.pstdev(x) if len(x) > 1 else 0.0 if x else None


def prep(q):
    pool = [dict(id=c['id'], style=c['style'], category=c['category'], color=c['color'], material=c['material'], shape=c['shape'], pos=c['pos']) for c in q['candidates']]
    return pool, {k: set(v) for k, v in q['allowed'].items()}


PRE = {q['qid']: prep(q) for q in QS}


def eval_sel(q, sel):
    """sel = 原始 pos 清單（5 個）或 None（失敗 → 0 分）。回傳 dict。"""
    if sel is None:
        return {'Align': 0.0, 'Div': None, 'EffCov': 0.0, 'failed': True, 'samecat': None, 'dup': None, 'divd': {}, 'effd': {}}
    pool, allowed = PRE[q['qid']]; byp = {p['pos']: p for p in pool}
    chosen = [byp[p] for p in sel]
    s = M.score(chosen, pool, allowed, K)
    V = [c for c in chosen if M.is_valid(c, allowed)]
    F = s['free_dims']; divd = {}
    for d, n in F.items():
        if len(V) >= 2:
            divd[d] = len({c[d] for c in V}) / min(len(V), n)
    samecat = (sum(1 for c in chosen if c['category'] == q['category']) / K) if q['scenario'] == 'S1' else None
    dup = sum(1 for a, b in itertools.combinations(chosen, 2) if all(a[d] == b[d] for d in DIMS3))
    return {'Align': s['Align'], 'Div': s['Div'], 'EffCov': s['EffCov'], 'failed': False, 'samecat': samecat, 'dup': dup, 'divd': divd, 'n_valid': s['n_valid']}


def load(path):
    p = Path(path)
    return {} if not p.exists() else {r['qid']: r for r in map(json.loads, open(p))}


def agg(rows):
    """rows = eval 結果清單 → 平均。Div 只算 |V|>=2。"""
    return {'n': len(rows), 'Align': mean([r['Align'] for r in rows]), 'Div': mean([r['Div'] for r in rows]), 'EffCov': mean([r['EffCov'] for r in rows]),
            'fail': mean([1.0 if r['failed'] else 0.0 for r in rows])}


def boot_ci(diffs, n=10000, seed=0):
    a = np.array([d for d in diffs if d is not None], dtype=float)
    if len(a) == 0:
        return None
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(a), size=(n, len(a)))
    m = a[idx].mean(1)
    return {'mean': float(a.mean()), 'lo': float(np.percentile(m, 2.5)), 'hi': float(np.percentile(m, 97.5)), 'n': int(len(a))}


def main():
    out = {'models': {}, 'baselines': {}, 'meta': {'n_questions': len(QS), 'n_queries': len({q['query_id'] for q in QS})}}
    rand = json.load(open(T / 'results/random_expect.json')) if (T / 'results/random_expect.json').exists() else {}
    orc = json.load(open(T / 'results/oracle.json')) if (T / 'results/oracle.json').exists() else {}
    EV = {}     # (model, cond, order, qid) → eval
    for m in MODELS + BASE:
        for cond in ('img', 'style_given'):
            for o in ORDERS:
                recs = load(T / 'out' / m / f'select_{cond}_{o}.jsonl')
                for qid, r in recs.items():
                    EV[(m, cond, o, qid)] = eval_sel(QD[qid], r['selected_positions'] if r['status'] == 'ok' else None) | {'rec': r}
    cells = sorted({q['cell'] for q in QS}); styles = sorted({q['style'] for q in QS})
    for m in MODELS + BASE:
        res = {}
        for cond in ('img', 'style_given'):
            for sc in ('S1', 'S2'):
                per_order = {}
                for o in ORDERS:
                    rows = [EV[(m, cond, o, q['qid'])] for q in QS if q['scenario'] == sc and (m, cond, o, q['qid']) in EV]
                    if rows:
                        per_order[o] = agg(rows) | {'n_expected': sum(1 for q in QS if q['scenario'] == sc)}
                if not per_order:
                    continue
                cell = {'orders': per_order}
                for k in ('Align', 'Div', 'EffCov', 'fail'):
                    vals = [v[k] for v in per_order.values()]
                    cell[k] = mean(vals); cell[k + '_sd'] = sd(vals)
                # H3 / H6 / 位置偏誤（所有順序合併）
                allr = [EV[(m, cond, o, q['qid'])] for o in per_order for q in QS if q['scenario'] == sc and (m, cond, o, q['qid']) in EV]
                cell['SameCat'] = mean([r['samecat'] for r in allr]); cell['Dup'] = mean([r['dup'] for r in allr])
                shown = [r['rec'].get('shown_positions') for r in allr if r['rec'].get('status') == 'ok' and r['rec'].get('shown_positions')]
                cell['pos1_rate'] = mean([1.0 if 1 in s else 0.0 for s in shown]) if shown else None
                cell['pos1to5_rate'] = mean([1.0 if sorted(s) == [1, 2, 3, 4, 5] else 0.0 for s in shown]) if shown else None
                # 每格 / 每風格 EffCov（順序平均）
                bycell = {}; bystyle = collections.defaultdict(list)
                for c in cells:
                    v = [EV[(m, cond, o, q['qid'])]['EffCov'] for o in per_order for q in QS if q['scenario'] == sc and q['cell'] == c and (m, cond, o, q['qid']) in EV]
                    if v:
                        bycell[c] = mean(v)
                for q in QS:
                    if q['scenario'] == sc:
                        bystyle[q['style']] += [EV[(m, cond, o, q['qid'])]['EffCov'] for o in per_order if (m, cond, o, q['qid']) in EV]
                cell['by_cell'] = bycell; cell['by_style'] = {k: mean(v) for k, v in bystyle.items()}
                res[f'{cond}|{sc}'] = cell
            e1, e2 = res.get(f'{cond}|S1', {}).get('EffCov'), res.get(f'{cond}|S2', {}).get('EffCov')
            if e1 is not None and e2 is not None:
                res[f'{cond}|avg_EffCov'] = (e1 + e2) / 2
        # Style Acc
        sp = load_style(m)
        if sp:
            ok = [r for r in sp if r['status'] == 'ok']
            acc = mean([1.0 if (r['status'] == 'ok' and r['answer'] == r['gold']) else 0.0 for r in sp])
            per = {}; wrong = {}
            for s in STYLES:
                rs = [r for r in sp if r['gold'] == s]
                if rs:
                    per[s] = mean([1.0 if r['answer'] == s else 0.0 for r in rs])
                    c = collections.Counter(r['answer'] for r in rs if r['answer'] != s)
                    wrong[s] = c.most_common(1)[0] if c else None
            res['style_acc'] = {'acc': acc, 'n': len(sp), 'n_failed': len(sp) - len(ok), 'per_style': per, 'top_wrong': wrong}
        if res:
            (out['models'] if m in MODELS else out['baselines'])[m] = res
    # Random / Oracle
    for name, src in (('random', rand), ('oracle', orc)):
        if not src:
            continue
        r = {}
        for sc in ('S1', 'S2'):
            qs = [q['qid'] for q in QS if q['scenario'] == sc]
            r[sc] = {'Align': mean([src[i]['Align'] for i in qs]), 'EffCov': mean([src[i]['EffCov'] for i in qs]), 'Div': mean([src[i].get('Div') for i in qs])}
        r['avg_EffCov'] = (r['S1']['EffCov'] + r['S2']['EffCov']) / 2
        out['baselines'][name] = r
    # SameCat 的參照：合格候選中同品項的比例、Oracle 解的比例
    s1 = [q for q in QS if q['scenario'] == 'S1']
    out['samecat_ref'] = {'valid_pool': mean([q['n_same_cat_valid'] / 12 for q in s1]),
                          'oracle': mean([sum(1 for i in q['oracle_selection'] if next(c for c in q['candidates'] if c['id'] == i)['category'] == q['category']) / K for q in s1])}
    out['dup_ref'] = {'valid_pairs_per_question': {sc: mean([q['dup_pairs_valid'] for q in QS if q['scenario'] == sc]) for sc in ('S1', 'S2')},
                      'oracle_dup': {sc: mean([eval_sel(q, [next(c['pos'] for c in q['candidates'] if c['id'] == i) for i in q['oracle_selection']])['dup'] for q in QS if q['scenario'] == sc]) for sc in ('S1', 'S2')}}
    # H5 / H2
    for m in MODELS:
        if m not in out['models']:
            continue
        sp = {r['query_id']: r for r in load_style(m)}
        if not sp:
            continue
        right = {qid for qid, r in sp.items() if r['status'] == 'ok' and r['answer'] == r['gold']}
        def qmean(cond, qid, key):
            v = [EV[(m, cond, o, qid)][key] for o in ORDERS if (m, cond, o, qid) in EV]
            return mean(v) if v else None
        h5 = {'groups': {}, 'paired': {}}
        for gname, sel in (('style_right', lambda qq: qq['query_id'] in right), ('style_wrong', lambda qq: qq['query_id'] not in right)):
            qs = [q for q in QS if sel(q)]
            h5['groups'][gname] = {'n_questions': len(qs), 'n_queries': len({q['query_id'] for q in qs}),
                                   'img_Align': mean([qmean('img', q['qid'], 'Align') for q in qs]), 'style_given_Align': mean([qmean('style_given', q['qid'], 'Align') for q in qs]),
                                   'img_EffCov': mean([qmean('img', q['qid'], 'EffCov') for q in qs]), 'style_given_EffCov': mean([qmean('style_given', q['qid'], 'EffCov') for q in qs])}
        for key in ('Align', 'EffCov'):
            for gname, sel in (('all', lambda qq: True), ('style_right', lambda qq: qq['query_id'] in right), ('style_wrong', lambda qq: qq['query_id'] not in right)):
                d = []
                for q in QS:
                    if sel(q):
                        a, b = qmean('style_given', q['qid'], key), qmean('img', q['qid'], key)
                        if a is not None and b is not None:
                            d.append(a - b)
                h5['paired'][f'{key}|{gname}'] = boot_ci(d, seed=5)
        out['models'][m]['H5'] = h5
        h2 = {}
        for d in DIMS3:
            diffs = []
            for qid_ in sorted({q['query_id'] for q in QS}):
                a, b = [], []
                for o in ORDERS:
                    x = EV.get((m, 'img', o, f'{qid_}-S1')); y = EV.get((m, 'img', o, f'{qid_}-S2'))
                    if x and y and d in x['divd'] and d in y['divd']:
                        a.append(x['divd'][d]); b.append(y['divd'][d])
                if a:
                    diffs.append(mean(a) - mean(b))
            h2[d] = boot_ci(diffs, seed=2)
        out['models'][m]['H2'] = h2
    # SigLIP baselines 的 H2
    json.dump(out, open(T / 'results/scores.json', 'w'), ensure_ascii=False, indent=1)
    write_md(out)


def load_style(m):
    p = T / 'out' / m / 'style.jsonl'
    return [json.loads(l) for l in open(p)] if p.exists() else []


def f(x, p=3):
    return '–' if x is None else f'{x:.{p}f}'


def write_md(o):
    L = ['# 階段 3 計分（scripts 產生；數字來源 results/scores.json）\n']
    L.append(f"題數 {o['meta']['n_questions']}（query {o['meta']['n_queries']}）。表中 ± 為 3 個候選順序的標準差。\n")
    for cond in ('img', 'style_given'):
        L.append(f'\n## 主表：條件 {cond}\n')
        L.append('| 模型 | S1 Align | S1 Div | S1 EffCov | S1 失敗率 | S2 Align | S2 Div | S2 EffCov | S2 失敗率 | 平均 EffCov |\n|---|---|---|---|---|---|---|---|---|---|')
        rows = list(o['models'].items()) + [(k, v) for k, v in o['baselines'].items() if k in BASE]
        for m, r in rows:
            c1, c2 = r.get(f'{cond}|S1'), r.get(f'{cond}|S2')
            if not c1 and not c2:
                continue
            g = lambda c, k: '–' if not c else (f"{f(c[k])}±{f(c[k + '_sd'])}" if c.get(k + '_sd') else f(c[k]))
            L.append(f"| {m} | {g(c1,'Align')} | {g(c1,'Div')} | **{g(c1,'EffCov')}** | {f(c1 and c1['fail'])} | {g(c2,'Align')} | {g(c2,'Div')} | **{g(c2,'EffCov')}** | {f(c2 and c2['fail'])} | {f(r.get(f'{cond}|avg_EffCov'))} |")
        if cond == 'img':
            for k in ('random', 'oracle'):
                if k in o['baselines']:
                    b = o['baselines'][k]
                    L.append(f"| {k} | {f(b['S1']['Align'])} | {f(b['S1']['Div'])} | {f(b['S1']['EffCov'])} | 0 | {f(b['S2']['Align'])} | {f(b['S2']['Div'])} | {f(b['S2']['EffCov'])} | 0 | {f(b['avg_EffCov'])} |")
    L.append('\n## Style Acc\n\n| 模型 | Acc | 失敗 | ' + ' | '.join(STYLES) + ' |\n|---|---|---|' + '---|' * len(STYLES))
    for m, r in o['models'].items():
        s = r.get('style_acc')
        if s:
            L.append(f"| {m} | {f(s['acc'])} | {s['n_failed']} | " + ' | '.join(f(s['per_style'].get(x), 2) + (f" (常錯成 {s['top_wrong'][x][0]})" if s['top_wrong'].get(x) else '') for x in STYLES) + ' |')
    L.append('\n## H5：認得出但沒用上？（Align@5，題目層級）\n\n| 模型 | 風格答對：img | 答對：style_given | 答錯：img | 答錯：style_given | style_given−img（全部，95% CI） |\n|---|---|---|---|---|---|')
    for m, r in o['models'].items():
        h = r.get('H5')
        if h:
            a, b = h['groups']['style_right'], h['groups']['style_wrong']; p = h['paired'].get('Align|all')
            L.append(f"| {m} | {f(a['img_Align'])} (n={a['n_questions']}) | {f(a['style_given_Align'])} | {f(b['img_Align'])} (n={b['n_questions']}) | {f(b['style_given_Align'])} | " + (f"{p['mean']:+.3f} [{p['lo']:+.3f}, {p['hi']:+.3f}]" if p else '–') + ' |')
    L.append('\n## H2：同一 query，S1 − S2 的逐維度 Div（img；配對差，95% CI）\n\n| 模型 | color | material | shape |\n|---|---|---|---|')
    for m, r in o['models'].items():
        h = r.get('H2')
        if h:
            L.append(f'| {m} | ' + ' | '.join((f"{h[d]['mean']:+.3f} [{h[d]['lo']:+.3f}, {h[d]['hi']:+.3f}] (n={h[d]['n']})" if h[d] else '–') for d in DIMS3) + ' |')
    L.append(f"\n## H3 SameCat@5（S1，img）— 參照：合格候選中同品項比例 {f(o['samecat_ref']['valid_pool'])}；Oracle 解 {f(o['samecat_ref']['oracle'])}\n\n| 模型 | SameCat@5 |\n|---|---|")
    for m, r in list(o['models'].items()) + [(k, v) for k, v in o['baselines'].items() if k in BASE]:
        c = r.get('img|S1')
        if c:
            L.append(f"| {m} | {f(c['SameCat'])} |")
    L.append(f"\n## H6 Dup@5 與位置偏誤（img；Dup = 5 件中 color/material/shape 三者皆相同的配對數；Oracle：S1 {f(o['dup_ref']['oracle_dup']['S1'])}、S2 {f(o['dup_ref']['oracle_dup']['S2'])}）\n\n| 模型 | S1 Dup | S2 Dup | S1 選到第 1 位 | S2 選到第 1 位 | S1 剛好 [1..5] | S2 剛好 [1..5] |\n|---|---|---|---|---|---|---|")
    for m, r in o['models'].items():
        a, b = r.get('img|S1'), r.get('img|S2')
        if a and b:
            L.append(f"| {m} | {f(a['Dup'])} | {f(b['Dup'])} | {f(a['pos1_rate'])} | {f(b['pos1_rate'])} | {f(a['pos1to5_rate'])} | {f(b['pos1to5_rate'])} |")
    L.append('\n## 附錄：每格 EffCov@5（img，順序平均）\n')
    cells = sorted({c for r in o['models'].values() for k, v in r.items() if isinstance(v, dict) and 'by_cell' in v for c in v['by_cell']})
    for sc in ('S1', 'S2'):
        L.append(f'\n### {sc}\n\n| 模型 | ' + ' | '.join(cells) + ' |\n|---|' + '---|' * len(cells))
        for m, r in o['models'].items():
            c = r.get(f'img|{sc}')
            if c:
                L.append(f'| {m} | ' + ' | '.join(f(c['by_cell'].get(x), 2) for x in cells) + ' |')
    L.append('\n## 附錄：每風格 EffCov@5（img）\n')
    for sc in ('S1', 'S2'):
        L.append(f'\n### {sc}\n\n| 模型 | ' + ' | '.join(STYLES) + ' |\n|---|' + '---|' * len(STYLES))
        for m, r in o['models'].items():
            c = r.get(f'img|{sc}')
            if c:
                L.append(f'| {m} | ' + ' | '.join(f(c['by_style'].get(x), 2) for x in STYLES) + ' |')
    L.append('\n## 完成題數（每個模型 × 條件 × 順序 的已完成題數 / 應有）\n')
    for m, r in o['models'].items():
        for cond in ('img', 'style_given'):
            for sc in ('S1', 'S2'):
                c = r.get(f'{cond}|{sc}')
                if c:
                    L.append(f"- {m} {cond} {sc}: " + ', '.join(f"{k}={v['n']}/{v['n_expected']}" for k, v in c['orders'].items()))
    (T / 'results/scores.md').write_text('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
