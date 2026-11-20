"""階段 4 計分。python3 -I score4.py → results/scores4.json、results/scores4.md（可重跑，結果固定）。
定義同階段 3 score.py（metrics.py 的 score / is_valid；Div 只算 |V|>=2；失敗 = 0 分）。S1/S2 的 tmpl_zh 直接讀階段 3 的 img 結果（同題、同 prompt）。"""
import collections, json, statistics, sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
U = Path(__file__).resolve().parent; D = U.parent; T3 = D / 'stage3'; R = D.parent
sys.path.insert(0, str(R / 'overnight_2026-11-14' / 'D_main_table'))
import metrics as M
K = 5; ORDERS = ['o0', 'o1', 'o2']
MODELS = ['qwen38-27b', 'qwen36-35b', 'gemma4-12b', 'qwen35-9b', 'qwen35-4b', 'internvl35-1tile', 'llavaov2-8b']
BASE = ['siglip2-top5', 'siglip2-mmr-std', 'siglip2-mmr-free']
LABEL = {'qwen38-27b': 'qwen38-27b‡', 'gemma4-12b': 'gemma4-12b‡', 'siglip2-mmr-free': 'siglip2-mmr-free†'}
SCEN = ['S1', 'S2', 'T3', 'T4']; WORDINGS = ['tmpl_zh', 'tmpl_en', 'syn_en']
QS = json.load(open(U / 'questions4.json')); QD = {q['qid']: q for q in QS}
ATTR_TRAP = {'attr_trap', 'attr_trap_fill'}; STYLE_TRAP = {'style_trap', 'style_trap_loose'}
lab = lambda m: LABEL.get(m, m)


def mean(x):
    x = [v for v in x if v is not None]
    return sum(x) / len(x) if x else None


def sd(x):
    x = [v for v in x if v is not None]
    return statistics.pstdev(x) if len(x) > 1 else None


def f(x, p=3):
    return '–' if x is None else f'{x:.{p}f}'


def pm(m, s):
    return '–' if m is None else (f'{m:.3f}±{s:.3f}' if s is not None else f'{m:.3f}')


PRE = {}
for q in QS:
    pool = [dict(id=c['id'], style=c['style'], category=c['category'], color=c['color'], material=c['material'], shape=c['shape'], pos=c['pos']) for c in q['candidates']]
    PRE[q['qid']] = (pool, {k: set(v) for k, v in q['allowed'].items()}, {c['pos']: c['bucket'] for c in q['candidates']})


def eval_sel(q, sel):
    if sel is None:
        return {'Align': 0.0, 'Div': None, 'EffCov': 0.0, 'failed': True, 'trap': None, 'attr_trap': None, 'style_trap': None}
    pool, allowed, bucket = PRE[q['qid']]; byp = {p['pos']: p for p in pool}
    s = M.score([byp[p] for p in sel], pool, allowed, K)
    bs = [bucket[p] for p in sel]
    return {'Align': s['Align'], 'Div': s['Div'], 'EffCov': s['EffCov'], 'failed': False,
            'trap': sum(b == 'trap' for b in bs) / K, 'attr_trap': sum(b in ATTR_TRAP for b in bs) / K, 'style_trap': sum(b in STYLE_TRAP for b in bs) / K}


def load(path):
    p = Path(path)
    return {} if not p.exists() else {r['qid']: r for r in map(json.loads, open(p))}


def rec_path(m, wording, order, scen):
    """S1/S2 的 tmpl_zh 來自階段 3 img；其餘來自階段 4 out。"""
    if wording == 'tmpl_zh' and scen in ('S1', 'S2') and m in MODELS:
        return T3 / 'out' / m / f'select_img_{order}.jsonl'
    return U / 'out' / m / f'select_{wording}_{order}.jsonl'


def boot_ci(diffs, n=10000, seed=0):
    a = np.array([d for d in diffs if d is not None], dtype=float)
    if len(a) == 0:
        return None
    rng = np.random.default_rng(seed); m = a[rng.integers(0, len(a), size=(n, len(a)))].mean(1)
    return {'mean': float(a.mean()), 'lo': float(np.percentile(m, 2.5)), 'hi': float(np.percentile(m, 97.5)), 'n': int(len(a))}


def main():
    EV = {}   # (m, wording, order, qid) → eval
    for m in MODELS + BASE:
        for w in WORDINGS:
            for o in ORDERS:
                for sc in SCEN:
                    for qid, r in load(rec_path(m, w, o, sc)).items():
                        if QD.get(qid, {}).get('scenario') == sc:
                            EV[(m, w, o, qid)] = eval_sel(QD[qid], r['selected_positions'] if r['status'] == 'ok' else None) | {'rec': r}
    rand = json.load(open(U / 'results/random_expect.json')); orc = json.load(open(U / 'results/oracle.json'))

    def sel_q(sc, pred=lambda q: True):
        return [q for q in QS if q['scenario'] == sc and pred(q)]

    def cell(m, w, qs, orders=ORDERS):
        per = {}
        for o in orders:
            rows = [EV[(m, w, o, q['qid'])] for q in qs if (m, w, o, q['qid']) in EV]
            if rows:
                per[o] = {'n': len(rows), 'n_expected': len(qs), 'Align': mean([r['Align'] for r in rows]), 'Div': mean([r['Div'] for r in rows]), 'EffCov': mean([r['EffCov'] for r in rows]),
                          'fail': mean([1.0 if r['failed'] else 0.0 for r in rows]), 'trap': mean([r['trap'] for r in rows]), 'attr_trap': mean([r['attr_trap'] for r in rows]),
                          'style_trap': mean([r['style_trap'] for r in rows])}
        if not per:
            return None
        out = {'orders': per}
        for k in ('Align', 'Div', 'EffCov', 'fail', 'trap', 'attr_trap', 'style_trap'):
            v = [x[k] for x in per.values()]; out[k] = mean(v); out[k + '_sd'] = sd(v)
        return out

    out = {'meta': {'n_questions': {sc: len(sel_q(sc)) for sc in SCEN}}, 'models': {}, 'baselines': {}}
    t3_groups = {'color': lambda q: q['attr'] == 'color', 'material': lambda q: q['attr'] == 'material',
                 'query_eq_v': lambda q: q['query_attr_equals_v'], 'query_neq_v': lambda q: not q['query_attr_equals_v']}
    for m in MODELS + BASE:
        res = {}
        for sc in SCEN:
            c = cell(m, 'tmpl_zh', sel_q(sc))
            if c:
                res[f'tmpl_zh|{sc}'] = c
        for g, pred in t3_groups.items():
            c = cell(m, 'tmpl_zh', sel_q('T3', pred))
            if c:
                res[f'tmpl_zh|T3|{g}'] = c
        # 措辭比較：只取 o0（每題一個配對）
        for sc in SCEN:
            qs = sel_q(sc); wc = {}
            for w in WORDINGS:
                c = cell(m, w, qs, ['o0'])
                if c:
                    wc[w] = {k: c[k] for k in ('Align', 'EffCov', 'fail')} | {'n': c['orders']['o0']['n']}
            if wc:
                paired = {}
                for key in ('Align', 'EffCov'):
                    for a, b in (('tmpl_en', 'tmpl_zh'), ('syn_en', 'tmpl_en'), ('syn_en', 'tmpl_zh')):
                        d = [EV[(m, a, 'o0', q['qid'])][key] - EV[(m, b, 'o0', q['qid'])][key] for q in qs if (m, a, 'o0', q['qid']) in EV and (m, b, 'o0', q['qid']) in EV]
                        paired[f'{key}|{a}-{b}'] = boot_ci(d, seed=7)
                res[f'wording|{sc}'] = {'by_wording': wc, 'paired': paired}
        if res:
            (out['models'] if m in MODELS else out['baselines'])[m] = res
    # Random / Oracle
    for name, src in (('random', rand), ('oracle', orc)):
        r = {}
        for sc in SCEN:
            qs = sel_q(sc)
            r[sc] = {'Align': mean([src[q['qid']]['Align'] for q in qs]), 'EffCov': mean([src[q['qid']]['EffCov'] for q in qs]), 'Div': mean([src[q['qid']].get('Div') for q in qs])}
        out['baselines'][name] = r
    # Random 的陷阱比例 = 該桶件數 / 40（隨機選 5 件期望相同）；Oracle 全是合格 → 0
    exp = lambda qs, bs: mean([sum(1 for c in q['candidates'] if c['bucket'] in bs) / len(q['candidates']) for q in qs])
    out['random_trap'] = {'T4': exp(sel_q('T4'), {'trap'}), 'T3_attr': exp(sel_q('T3'), ATTR_TRAP), 'T3_style': exp(sel_q('T3'), STYLE_TRAP)}
    out['n_t3'] = {g: len(sel_q('T3', p)) for g, p in t3_groups.items()}
    json.dump(out, open(U / 'results/scores4.json', 'w'), ensure_ascii=False, indent=1)
    write_md(out)


def write_md(o):
    L = ['# 階段 4 計分（scripts 產生；數字來源 results/scores4.json）\n',
         f"題數：{o['meta']['n_questions']}。表中 ± 為 3 個候選順序的標準差（基準線只有原順序，無 ±）。‡ = 標註者模型；† = 用了標註屬性的非公平基準線。\n"]
    rows = [(m, o['models'][m]) for m in MODELS if m in o['models']] + [(b, o['baselines'][b]) for b in BASE if b in o['baselines']]
    rt = o['random_trap']

    def g(c, k):
        return '–' if not c else pm(c[k], c.get(k + '_sd'))
    L.append('\n## T4 Negation 主表（tmpl_zh，3 順序）— Trap@5 = 5 件中選到「同風格同品項」陷阱的比例\n')
    L.append('| 模型 | Align@5 | Div@5 | EffCov@5 | Trap@5 | 失敗率 |\n|---|---|---|---|---|---|')
    for m, r in rows:
        c = r.get('tmpl_zh|T4')
        if c:
            L.append(f"| {lab(m)} | {g(c,'Align')} | {g(c,'Div')} | **{g(c,'EffCov')}** | {g(c,'trap')} | {f(c['fail'])} |")
    for k in ('random', 'oracle'):
        b = o['baselines'][k]['T4']; L.append(f"| {k} | {f(b['Align'])} | {f(b['Div'])} | {f(b['EffCov'])} | {f(rt['T4']) if k == 'random' else '0.000'} | 0 |")
    L.append('\n## T3 多重限制主表（tmpl_zh，3 順序）— 屬性陷阱 = 風格對但屬性 ≠ 指定值；風格陷阱 = 品項 / 屬性對但風格不對\n')
    for grp, title in (('color', '顏色限制'), ('material', '材質限制'), (None, '全部 T3')):
        L.append(f"\n### {title}（{o['n_t3'].get(grp, sum(o['n_t3'][x] for x in ('color', 'material')))} 題）\n\n| 模型 | Align@5 | Div@5 | EffCov@5 | 屬性陷阱@5 | 風格陷阱@5 | 失敗率 |\n|---|---|---|---|---|---|---|")
        for m, r in rows:
            c = r.get(f'tmpl_zh|T3|{grp}') if grp else r.get('tmpl_zh|T3')
            if c:
                L.append(f"| {lab(m)} | {g(c,'Align')} | {g(c,'Div')} | **{g(c,'EffCov')}** | {g(c,'attr_trap')} | {g(c,'style_trap')} | {f(c['fail'])} |")
        if grp is None:
            b = o['baselines']['random']['T3']; L.append(f"| random | {f(b['Align'])} | {f(b['Div'])} | {f(b['EffCov'])} | {f(rt['T3_attr'])} | {f(rt['T3_style'])} | 0 |")
            b = o['baselines']['oracle']['T3']; L.append(f"| oracle | {f(b['Align'])} | {f(b['Div'])} | {f(b['EffCov'])} | 0.000 | 0.000 | 0 |")
    L.append(f"\n### query 本身的屬性是否等於指定值（T3，tmpl_zh；等於 {o['n_t3']['query_eq_v']} 題 / 不等於 {o['n_t3']['query_neq_v']} 題）\n\n| 模型 | 等於：Align | 等於：EffCov | 等於：屬性陷阱 | 不等於：Align | 不等於：EffCov | 不等於：屬性陷阱 |\n|---|---|---|---|---|---|---|")
    for m, r in rows:
        a, b = r.get('tmpl_zh|T3|query_eq_v'), r.get('tmpl_zh|T3|query_neq_v')
        if a and b:
            L.append(f"| {lab(m)} | {f(a['Align'])} | {f(a['EffCov'])} | {f(a['attr_trap'])} | {f(b['Align'])} | {f(b['EffCov'])} | {f(b['attr_trap'])} |")
    L.append('\n## 措辭比較（只取原順序 o0；tmpl_zh = 中文模板、tmpl_en = 英文直譯、syn_en = 合成 query）\n')
    L.append('配對差 = 同一題兩種措辭的分數相減，題目層級 bootstrap 95% CI（10,000 次）。syn_en 由 Claude Sonnet 5.5 改寫。\n')
    for key in ('Align', 'EffCov'):
        L.append(f'\n### {key}@5\n\n| 模型 | 題型 | tmpl_zh | tmpl_en | syn_en | tmpl_en − tmpl_zh [95% CI] | syn_en − tmpl_en [95% CI] | syn_en − tmpl_zh [95% CI] |\n|---|---|---|---|---|---|---|---|')
        for m in MODELS:
            for sc in SCEN:
                w = o['models'].get(m, {}).get(f'wording|{sc}')
                if not w:
                    continue
                ci = lambda k: (lambda p: '–' if not p else f"{p['mean']:+.3f} [{p['lo']:+.3f}, {p['hi']:+.3f}]")(w['paired'].get(f'{key}|{k}'))
                L.append(f"| {lab(m)} | {sc} | " + ' | '.join(f(w['by_wording'].get(x, {}).get(key)) for x in WORDINGS) + f" | {ci('tmpl_en-tmpl_zh')} | {ci('syn_en-tmpl_en')} | {ci('syn_en-tmpl_zh')} |")
    L.append('\n## 總表：所有題型 × 模型（tmpl_zh 主條件，EffCov@5；S1、S2 來自階段 3 的 img）\n')
    L.append('| 模型 | S1 | S2 | T3 | T4 | 4 題型平均 |\n|---|---|---|---|---|---|')
    for m, r in rows:
        v = [r.get(f'tmpl_zh|{sc}', {}).get('EffCov') for sc in SCEN]
        L.append(f"| {lab(m)} | " + ' | '.join(f(x) for x in v) + f" | {f(mean(v) if all(x is not None for x in v) else None)} |")
    for k in ('random', 'oracle'):
        v = [o['baselines'][k][sc]['EffCov'] for sc in SCEN]; L.append(f"| {k} | " + ' | '.join(f(x) for x in v) + f" | {f(mean(v))} |")
    L.append('\n## 總表：Align@5\n\n| 模型 | S1 | S2 | T3 | T4 |\n|---|---|---|---|---|')
    for m, r in rows:
        L.append(f"| {lab(m)} | " + ' | '.join(f(r.get(f'tmpl_zh|{sc}', {}).get('Align')) for sc in SCEN) + ' |')
    L.append('\n## 完成題數（模型 × 措辭 × 題型 的已完成 / 應有；tmpl_zh 為 3 順序）\n')
    for m in MODELS:
        r = o['models'].get(m, {})
        for sc in SCEN:
            c = r.get(f'tmpl_zh|{sc}')
            if c:
                L.append(f"- {m} tmpl_zh {sc}: " + ', '.join(f"{k}={v['n']}/{v['n_expected']}" for k, v in c['orders'].items()))
            for w in ('tmpl_en', 'syn_en'):
                x = r.get(f'wording|{sc}', {}).get('by_wording', {}).get(w)
                if x:
                    L.append(f"- {m} {w} {sc}: o0={x['n']}")
    (U / 'results/scores4.md').write_text('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
