"""階段 5 計分：python3 -I score5.py → results/scores5.json、scores5.md、ladder_S1.svg、ladder_S2.svg（可重跑，結果固定）。
計分定義直接 import stage3/score.py 的 eval_sel / boot_ci / mean / sd（不複製改寫）。"""
import json, sys, collections
from pathlib import Path
sys.dont_write_bytecode = True
V = Path(__file__).resolve().parent; T = V.parent / 'stage3'; R = V.parent.parent
sys.path.insert(0, str(T)); import score as S3   # noqa（import 時只讀 questions.json）
M = S3.M; QS = S3.QS; QD = S3.QD; mean = S3.mean; sd = S3.sd; boot_ci = S3.boot_ci
MODELS = S3.MODELS; ORDERS = ['o0', 'o1', 'o2']
ANNOT = {'qwen38-27b', 'gemma4-12b'}
CAPC = ['cap_g0', 'cap_g1', 'cap_g2', 'cap_g3', 'cap_g4', 'cap_g5', 'cap_g5_nostyle']
LADDER = ['img'] + CAPC            # img 來自階段 3
ALLC = LADDER   # USER_DECISIONS ⑬：拿掉 img_goldstyle、style_given
TXT = ['siglip2txt-top5', 'siglip2txt-mmr-std']; TXTC = [c for c in CAPC if c != 'cap_g0']
PATH = lambda m, c, o: (T if c in ('img', 'style_given') else V) / 'out' / m / f'select_{c}_{o}.jsonl'
LBL = {'img': 'img', 'cap_g0': 'g0', 'cap_g1': 'g1', 'cap_g2': 'g2', 'cap_g3': 'g3', 'cap_g4': 'g4', 'cap_g5': 'g5', 'cap_g5_nostyle': 'g5−style', 'img_goldstyle': 'img+gold', 'style_given': 'img+self'}


def nm(m): return m + ('‡' if m in ANNOT else '')


def copyq(q, sel):
    if sel is None: return None
    pool, allowed = S3.PRE[q['qid']]; byp = {p['pos']: p for p in pool}
    V_ = [byp[p] for p in sel if M.is_valid(byp[p], allowed)]
    if not V_: return None
    return {'color': sum(c['color'] == q['query']['color'] for c in V_) / len(V_), 'material': sum(c['material'] == q['query']['material'] for c in V_) / len(V_)}


def main():
    EV = {}
    def add(name, c, orders):
        for o in orders:
            p = PATH(name, c, o)
            for qid, r in S3.load(p).items():
                sel = r['selected_positions'] if r['status'] == 'ok' else None
                e = S3.eval_sel(QD[qid], sel); e['copy'] = copyq(QD[qid], sel); EV[(name, c, o, qid)] = e
    for m in MODELS:
        for c in ALLC: add(m, c, ORDERS)
    for b in TXT:
        for c in TXTC: add(b, c, ['o0'])
    for b in ('siglip2-top5', 'siglip2-mmr-std'): add(b, 'img', ['o0'])
    # siglip2-* 在階段 3 的位置是 T/out/<b>/select_img_o0.jsonl（PATH 對 img 已指向 T）
    out = {'meta': {'n_questions': len(QS), 'models': MODELS, 'annotators': sorted(ANNOT)}, 'cells': {}, 'ladder': {}, 'paired': {}, 'loss': {}, 'copyq': {}, 'completion': {}}
    scs = ('S1', 'S2')
    def qv(name, c, qid, key):
        v = [EV[(name, c, o, qid)][key] for o in ORDERS if (name, c, o, qid) in EV]
        return mean(v) if v else None
    for name in MODELS + TXT + ['siglip2-top5', 'siglip2-mmr-std']:
        for c in ALLC:
            for sc in scs:
                per = {}
                for o in ORDERS:
                    rows = [EV[(name, c, o, q['qid'])] for q in QS if q['scenario'] == sc and (name, c, o, q['qid']) in EV]
                    if rows: per[o] = S3.agg(rows) | {'n_expected': sum(q['scenario'] == sc for q in QS)}
                if not per: continue
                cell = {'orders': per}
                for k in ('Align', 'Div', 'EffCov', 'fail'):
                    vals = [v[k] for v in per.values()]; cell[k] = mean(vals); cell[k + '_sd'] = sd(vals)
                allr = [EV[(name, c, o, q['qid'])] for o in per for q in QS if q['scenario'] == sc and (name, c, o, q['qid']) in EV]
                cq = [r['copy'] for r in allr if r['copy']]
                cell['CopyQ_color'] = mean([x['color'] for x in cq]); cell['CopyQ_material'] = mean([x['material'] for x in cq])
                qa = [qv(name, c, q['qid'], 'Align') for q in QS if q['scenario'] == sc]
                cell['Align_q'] = {q['qid']: qv(name, c, q['qid'], 'Align') for q in QS if q['scenario'] == sc}
                cell['EffCov_q'] = {q['qid']: qv(name, c, q['qid'], 'EffCov') for q in QS if q['scenario'] == sc}
                cell['CI_EffCov'] = boot_ci([x for x in cell['EffCov_q'].values()], seed=11); cell['CI_Align'] = boot_ci([x for x in cell['Align_q'].values()], seed=12)
                out['cells'][f'{name}|{c}|{sc}'] = {k: v for k, v in cell.items() if k not in ('Align_q', 'EffCov_q')}
                cell_q = cell
                out['completion'][f'{name}|{c}|{sc}'] = {o: f"{v['n']}/{v['n_expected']}" for o, v in per.items()}
    # Random / Oracle 參照（階段 3）
    rnd = json.load(open(T / 'results/random_expect.json'))
    out['random'] = {sc: {'Align': mean([rnd[q['qid']]['Align'] for q in QS if q['scenario'] == sc]), 'EffCov': mean([rnd[q['qid']]['EffCov'] for q in QS if q['scenario'] == sc])} for sc in scs}
    # 配對差
    PAIRS = [('g1−g0', 'cap_g1', 'cap_g0'), ('g2−g1', 'cap_g2', 'cap_g1'), ('g3−g2', 'cap_g3', 'cap_g2'), ('g4−g3', 'cap_g4', 'cap_g3'), ('g5−g4', 'cap_g5', 'cap_g4'),
             ('g5−g5_nostyle', 'cap_g5', 'cap_g5_nostyle'), ('g1−img', 'cap_g1', 'img')]
    for m in MODELS:
        for sc in scs:
            for lab, a, b in PAIRS:
                for key in ('Align', 'EffCov'):
                    d = []
                    for q in QS:
                        if q['scenario'] != sc: continue
                        x, y = qv(m, a, q['qid'], key), qv(m, b, q['qid'], key)
                        if x is not None and y is not None: d.append(x - y)
                    out['paired'][f'{m}|{sc}|{lab}|{key}'] = boot_ci(d, seed=7)
    json.dump(out, open(V / 'results/scores5.json', 'w'), ensure_ascii=False, indent=1)
    write_md(out); write_svgs(out)


def f(x, p=3): return '–' if x is None else f'{x:.{p}f}'
def ci(p, sig=True):
    if not p or 'mean' not in p: return '–'
    star = ' *' if p['lo'] > 0 or p['hi'] < 0 else ''
    return f"{p['mean']:+.3f} [{p['lo']:+.3f}, {p['hi']:+.3f}]{star}"


def write_md(o):
    C = o['cells']; L = ['# 階段 5 計分（score5.py 產生；數字來源 results/scores5.json）\n',
                       'ĺ 表中數字 = 3 個順序平均；`‡` = 標註者模型；`*` = 95% CI（題目層級 bootstrap）不含 0；g5−style = cap_g5_nostyle；img = 只看參考圖（階段 3）。\n'.replace('ĺ ', '')]
    for key in ('Align', 'EffCov'):
        for sc in ('S1', 'S2'):
            L.append(f'\n## 階梯表：{key}@5（{sc}）\n\n| 模型 | ' + ' | '.join(LBL[c] for c in LADDER) + ' |\n|---|' + '---|' * len(LADDER))
            for m in MODELS:
                L.append(f'| {nm(m)} | ' + ' | '.join(f(C.get(f'{m}|{c}|{sc}', {}).get(key)) for c in LADDER) + ' |')
            for b in TXT:
                L.append(f'| {b} | ' + ' | '.join(f(C.get(f'{b}|{c}|{sc}', {}).get(key)) if c in TXTC else '–' for c in LADDER) + ' |')
            for b in ('siglip2-top5', 'siglip2-mmr-std'):
                L.append(f'| {b}（階段 3，以圖找圖） | ' + f(C.get(f'{b}|img|{sc}', {}).get(key)) + ' |' + ' – |' * (len(LADDER) - 1))
            L.append(f"| Random | " + ' | '.join(f(o['random'][sc][key]) for _ in [0]) + ' |' + ' – |' * (len(LADDER) - 1))
    for key in ('Align', 'EffCov'):
        for sc in ('S1', 'S2'):
            labs = ['g1−g0', 'g2−g1', 'g3−g2', 'g4−g3', 'g5−g4', 'g5−g5_nostyle', 'g1−img']
            L.append(f'\n## 每一階的配對差：{key}@5（{sc}）\n\n| 模型 | ' + ' | '.join(labs) + ' |\n|---|' + '---|' * len(labs))
            for m in MODELS:
                L.append(f'| {nm(m)} | ' + ' | '.join(ci(o['paired'].get(f'{m}|{sc}|{l}|{key}')) for l in labs) + ' |')
    for sc in ('S1', 'S2'):
        L.append(f'\n## 找相似的傾向：CopyQ@5 顏色 / 材質（選中的合格商品中，和參考圖相同的比例）與 EffCov@5（{sc}）\n\n| 模型 | ' + ' | '.join(LBL[c] for c in ALLC) + ' |\n|---|' + '---|' * len(ALLC))
        for m in MODELS:
            L.append(f'| {nm(m)} | ' + ' | '.join((lambda x: '–' if not x else f"{f(x['CopyQ_color'],2)}/{f(x['CopyQ_material'],2)} ({f(x['EffCov'],2)})")(C.get(f'{m}|{c}|{sc}')) for c in ALLC) + ' |')
    L.append('\n## 失敗率與完成題數\n')
    for m in MODELS:
        for c in ALLC:
            for sc in ('S1', 'S2'):
                x = C.get(f'{m}|{c}|{sc}')
                if x: L.append(f"- {m} {c} {sc}: fail={f(x['fail'])}; " + ', '.join(f'{k}={v}' for k, v in o['completion'][f'{m}|{c}|{sc}'].items()))
    (V / 'results/scores5.md').write_text('\n'.join(L) + '\n')


def write_svgs(o):
    C = o['cells']; cols = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    for sc in ('S1', 'S2'):
        W, H, ml, mb, mt = 760, 420, 60, 70, 30; xs = lambda i: ml + i * (W - ml - 160) / (len(LADDER) - 1)
        vals = [C.get(f'{m}|{c}|{sc}', {}).get('EffCov') for m in MODELS for c in LADDER]; vals = [v for v in vals if v is not None] or [0, 1]
        lo, hi = 0.0, max(vals + [o['random'][sc]['EffCov']]) * 1.1 or 1; ys = lambda v: H - mb - (v - lo) / (hi - lo) * (H - mb - mt)
        s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="11"><rect width="100%" height="100%" fill="white"/>',
             f'<text x="{ml}" y="16" font-size="13">EffCov@5 ladder — {sc}（x: img、g0…g5、g5−style；虛線 = Random）</text>']
        for t in range(0, 6):
            v = lo + (hi - lo) * t / 5; s.append(f'<line x1="{ml}" x2="{W-160}" y1="{ys(v):.0f}" y2="{ys(v):.0f}" stroke="#ddd"/><text x="{ml-6}" y="{ys(v)+4:.0f}" text-anchor="end">{v:.2f}</text>')
        for i, c in enumerate(LADDER): s.append(f'<text x="{xs(i):.0f}" y="{H-mb+16}" text-anchor="middle">{LBL[c]}</text>')
        s.append(f'<line x1="{ml}" x2="{W-160}" y1="{ys(o["random"][sc]["EffCov"]):.0f}" y2="{ys(o["random"][sc]["EffCov"]):.0f}" stroke="#888" stroke-dasharray="5,4"/>')
        for k, m in enumerate(MODELS):
            pts = [(xs(i), ys(C[f'{m}|{c}|{sc}']['EffCov'])) for i, c in enumerate(LADDER) if f'{m}|{c}|{sc}' in C and C[f'{m}|{c}|{sc}']['EffCov'] is not None]
            if pts: s.append(f'<polyline fill="none" stroke="{cols[k]}" stroke-width="2" points="' + ' '.join(f'{x:.0f},{y:.0f}' for x, y in pts) + '"/>' + ''.join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="{cols[k]}"/>' for x, y in pts))
            s.append(f'<line x1="{W-150}" x2="{W-130}" y1="{40+k*18}" y2="{40+k*18}" stroke="{cols[k]}" stroke-width="2"/><text x="{W-125}" y="{44+k*18}">{nm(m)}</text>')
        s.append('</svg>'); (V / f'results/ladder_{sc}.svg').write_text('\n'.join(s))


if __name__ == '__main__':
    main()
