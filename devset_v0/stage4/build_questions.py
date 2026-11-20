"""B 節：出題。python3 -I build_questions.py → questions.json、build_report.json（不用 GPU，可重跑，結果固定）。"""
import collections, itertools, json, random, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
T = Path(__file__).resolve().parent; D = T.parent; S = D / 'stage2'; R = D.parent
sys.path.insert(0, str(S)); sys.path.insert(0, str(R / 'overnight_2026-11-14' / 'D_main_table')); sys.path.insert(0, str(R / 'overnight_2026-11-14' / 'C1_category'))
from common2 import CELLS, CELL_STYLE, CELL_ITEM, read_jsonl, STYLES, ITEMS, stage1_items, stage2_items   # noqa
import metrics as M            # 原樣 import oracle / free_dims
import c1_stats                # STYLE_REGEX（同 stage0）
K = 5
STYLE_PAT = re.compile('|'.join(c1_stats.STYLE_REGEX.values()), re.I)


def clean(title):   # 同 pilot2 build_pilot2.clean：刪風格字詞，再整理空白 / 標點
    t = STYLE_PAT.sub('', title)
    return re.sub(r'\s{2,}', ' ', re.sub(r'\s+([,.;)])', r'\1', t)).strip(' ,-')


def vote(vals, claude):
    vs = [v for v in vals if v]
    c = collections.Counter(vs)
    if c and c.most_common(1)[0][1] >= 2:
        return c.most_common(1)[0][0], 'majority'
    return (claude or (vs[0] if vs else None)), 'claude'


def load():
    items = {it['id']: it for it in stage1_items() + stage2_items()}
    si = {r['id']: r for r in read_jsonl(S / 'ann_single_item.jsonl') if r.get('ok')}
    P = {}; tie = 0
    for r in read_jsonl(S / 'annotations_all.jsonl'):
        a = [r['claude'], r['qwen'], r['gemma']]
        if not r['complete'] or any(x is None for x in a):
            continue          # 「三方都標過」：三位都有成功的標註
        it = items[r['id']]
        attrs = {}
        for d in ('color', 'material', 'shape', 'category', 'style'):
            attrs[d], how = vote([x[d] for x in a], r['claude'][d])
            if d in ('color', 'material', 'shape'):
                tie += how == 'claude'
        cs, ci = r['cell'].split('|')
        if r['qualified']:
            attrs['style'], attrs['category'] = CELL_STYLE[cs], CELL_ITEM[ci]
        P[r['id']] = dict(id=r['id'], parent_asin=r['parent_asin'], cell=r['cell'], cs=cs, ci=ci, qualified=r['qualified'], attrs=attrs,
                          styles={x['style'] for x in a}, title=it['title'], title_clean=clean(it['title']), claude=r['claude'], single=si.get(r['id']), allthree=a)
    return P, tie


def main():
    P, tie = load()
    edges = collections.defaultdict(set)
    for e in json.load(open(R / 'devset_v0/stage0/phash_dups.json')):
        edges[e['removed']].add(e['kept']); edges[e['kept']].add(e['removed'])
    QUAL = collections.defaultdict(list)       # cell → 合格商品（依 id 排序）
    for p in sorted(P.values(), key=lambda p: p['id']):
        if p['qualified']:
            QUAL[p['cell']].append(p)
    report = {'dropped': [], 'queries_per_cell': {}, 'n_questions': collections.Counter(), 'relaxed': [], 'n_d': collections.defaultdict(collections.Counter),
              'F_size': collections.defaultdict(collections.Counter), 'attr_ties_to_claude': tie}
    # B2 query
    queries = []
    for cell in CELLS:
        if cell.endswith('|wall_art'):
            continue
        cs = CELL_STYLE[cell.split('|')[0]]
        ok = [p for p in QUAL[cell] if all(x['style'] == cs for x in p['allthree']) and p['claude']['style_conf'] == 3
              and p['single'] and p['single']['single_item'] == 'yes' and p['single']['single_item_conf'] >= 2]
        rng = random.Random(f'0-stage3-query-{cell}')
        pick = ok[:] ; rng.shuffle(pick); pick = pick[:5]
        report['queries_per_cell'][cell] = {'eligible': len(ok), 'used': len(pick)}
        queries += pick
    allp = sorted(P.values(), key=lambda p: p['id'])

    def dup(a, b):
        return a['parent_asin'] == b['parent_asin'] or b['parent_asin'] in edges[a['parent_asin']]

    def clash(x, chosen):
        return any(dup(x, c) for c in chosen)

    def take(rng, pool, n, chosen, key=None, spread=None):
        """從 pool（已打亂副本）取 n 件，不和 chosen 重複；spread = 依該鍵輪流取（盡量平均）。"""
        pool = pool[:]; rng.shuffle(pool); out = []
        if spread:
            groups = collections.defaultdict(list)
            for x in pool:
                groups[spread(x)].append(x)
            keys = sorted(groups); rng.shuffle(keys)
            while len(out) < n and any(groups[k] for k in keys):
                for k in keys:
                    while groups[k]:
                        x = groups[k].pop(0)
                        if not clash(x, chosen + out):
                            out.append(x); break
                    if len(out) == n:
                        break
        else:
            for x in pool:
                if len(out) == n:
                    break
                if not clash(x, chosen + out):
                    out.append(x)
        return out

    def build(q, scen, tr):
        rng = random.Random(f'0-stage3-{scen}-{q["id"]}-{tr}')
        qs, qc = q['cs'], q['ci']; X = CELL_STYLE[qs]; C = CELL_ITEM[qc]
        chosen = [q]; notes = []
        qual_other = lambda x: x['id'] != q['id']
        if scen == 'S2':
            valid = take(rng, [x for x in QUAL[q['cell']] if qual_other(x)], 12, chosen)
        else:
            same = [x for x in QUAL[q['cell']] if qual_other(x)]
            ncat = rng.choice([2, 3]); v1 = take(rng, same, ncat, chosen)
            others = [x for c in CELLS if c.split('|')[0] == qs and c != q['cell'] for x in QUAL[c]]
            v2 = take(rng, others, 12 - len(v1), chosen + v1, spread=lambda x: x['ci'])
            valid = v1 + v2
            if len({x['ci'] for x in valid}) < min(4, len({c.split('|')[1] for c in CELLS if c.split('|')[0] == qs})):
                return None, 'S1 合格品項數不足 4'
        if len(valid) != 12:
            return None, '合格不足 12'
        chosen += valid
        h1 = take(rng, [x for c in CELLS if c.split('|')[1] == qc and c.split('|')[0] != qs for x in QUAL[c]], 12, chosen, spread=lambda x: x['cs'])
        chosen += h1
        if scen == 'S2':
            pool2 = [x for c in CELLS if c.split('|')[0] == qs and c.split('|')[1] != qc for x in QUAL[c]]
            h2 = take(rng, pool2, 8, chosen)
        else:
            pool2 = [x for c in CELLS if c.split('|')[0] != qs and c.split('|')[1] != qc for x in QUAL[c]]
            m = [x for x in pool2 if x['attrs']['color'] == q['attrs']['color'] or x['attrs']['material'] == q['attrs']['material']]
            h2 = take(rng, m, 8, chosen)
            if len(h2) < 8:
                notes.append(f'S1 困難干擾2 只有 {len(h2)} 件 color/material 相同，放寬補 {8 - len(h2)} 件')
                h2 += take(rng, [x for x in pool2 if x not in h2], 8 - len(h2), chosen + h2)
        if len(h2) != 8:
            return None, '困難干擾2 不足'
        chosen += h2
        rnd = take(rng, [x for x in allp if X not in x['styles'] and not x['id'] == q['id']], 8, chosen)
        if len(rnd) != 8:
            return None, '隨機不足'
        chosen += rnd
        cands = [(x, b) for b, g in (('valid', valid), ('hard1', h1), ('hard2', h2), ('random', rnd)) for x in g]
        # 硬性檢查 1：干擾項確定不是 X；S2 干擾項不可同時是 X 與 C
        for x, b in cands:
            if b != 'valid':
                if b == 'random' and X in x['styles']:
                    return None, '隨機含 X'
                if b != 'random' and x['attrs']['style'] == X and (scen == 'S1' or x['attrs']['category'] == C):
                    return None, '干擾項是合格'
        random.Random(f'0-stage3-order-{scen}-{q["id"]}-{tr}').shuffle(cands)
        pool = [dict(id=x['id'], style=x['attrs']['style'], category=x['attrs']['category'], color=x['attrs']['color'],
                     material=x['attrs']['material'], shape=x['attrs']['shape']) for x, b in cands]
        allowed = {'style': {X}, 'category': {C}} if scen == 'S2' else {'style': {X}}
        F = M.free_dims(pool, allowed)
        if len(F) < 2:
            return None, '|F|<2'
        if scen == 'S2' and not set(F) <= {'color', 'material', 'shape'}:
            return None, 'S2 F 含 style/category'
        o, sel = M.oracle(pool, allowed, K)
        if o['EffCov'] < 1.0 - 1e-9:
            return None, f'Oracle EffCov={o["EffCov"]:.3f}'
        vv = [p for p in pool if M.is_valid(p, allowed)]
        pairs = sum(1 for a, b in itertools.combinations(vv, 2) if all(a[d] == b[d] for d in ('color', 'material', 'shape')))
        rec = {'qid': f'{q["id"]}-{scen}', 'scenario': scen, 'query_id': q['id'], 'cell': q['cell'], 'style': X, 'category': C,
               'query': {'id': q['id'], 'parent_asin': q['parent_asin'], 'title': q['title'], 'title_clean': q['title_clean'], 'color': q['attrs']['color'],
                         'material': q['attrs']['material'], 'shape': q['attrs']['shape']},
               'allowed': {k: sorted(v) for k, v in allowed.items()}, 'free_dims': F, 'dup_pairs_valid': pairs, 'try': tr, 'notes': notes,
               'oracle_selection': [x['id'] for x in sel],
               'n_same_cat_valid': sum(1 for p in vv if p['category'] == C), 'seed': f'0-stage3-{scen}-{q["id"]}-{tr}',
               'candidates': [dict(pos=i + 1, id=x['id'], parent_asin=x['parent_asin'], title=x['title'], title_clean=x['title_clean'], bucket=b,
                                   valid=M.is_valid(pool[i], allowed), cell=x['cell'], style=pool[i]['style'], category=pool[i]['category'], color=pool[i]['color'],
                                   material=pool[i]['material'], shape=pool[i]['shape']) for i, (x, b) in enumerate(cands)]}
        return rec, None

    out = []
    for q in sorted(queries, key=lambda p: p['id']):
        for scen in ('S1', 'S2'):
            why = collections.Counter(); rec = None
            for tr in range(200):
                rec, err = build(q, scen, tr)
                if rec:
                    break
                why[err] += 1
            if rec is None:
                report['dropped'].append({'qid': f'{q["id"]}-{scen}', 'cell': q['cell'], 'reasons': dict(why)}); continue
            if rec['try'] > 0:
                rec['retry_reasons'] = dict(why)
            out.append(rec)
            report['n_questions'][f'{scen}|{q["cell"]}'] += 1; report['n_questions'][scen] += 1
            report['F_size'][scen][len(rec['free_dims'])] += 1
            for d, n in rec['free_dims'].items():
                report['n_d'][f'{scen}|{d}'][n] += 1
            if rec['notes']:
                report['relaxed'].append({'qid': rec['qid'], 'notes': rec['notes']})
    report['n_queries'] = len(queries); report['n_questions_total'] = len(out)
    report['n_retried'] = sum(1 for r in out if r['try'] > 0)
    json.dump(out, open(T / 'questions.json', 'w'), ensure_ascii=False, indent=1)
    json.dump(report, open(T / 'build_report.json', 'w'), ensure_ascii=False, indent=1, default=lambda x: dict(x))
    print(json.dumps({k: report[k] for k in ('n_queries', 'n_questions_total', 'n_retried')}), 'dropped', len(report['dropped']))


if __name__ == '__main__':
    main()
