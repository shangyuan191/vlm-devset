"""階段 4 出題：T4 Negation、T3 多重限制；S1/S2 原樣沿用 stage3/questions.json。
python3 -I build_questions4.py → questions4.json、build_report4.json（不用 GPU，可重跑，結果固定）。"""
import collections, itertools, json, random, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
U = Path(__file__).resolve().parent; D = U.parent; S = D / 'stage2'; T = D / 'stage3'; R = D.parent
sys.path.insert(0, str(S)); sys.path.insert(0, str(R / 'overnight_2026-11-14' / 'D_main_table')); sys.path.insert(0, str(R / 'overnight_2026-11-14' / 'C1_category'))
from common2 import CELLS, CELL_STYLE, CELL_ITEM, read_jsonl, STYLES, ITEMS, stage1_items, stage2_items   # noqa
import metrics as M
import c1_stats
K = 5
STYLE_PAT = re.compile('|'.join(c1_stats.STYLE_REGEX.values()), re.I)
ALL_CATS = set(CELL_ITEM.values())


def clean(title):
    """刪風格字詞，反覆刪到字串不再變（修 "Mid Modern Century" → "Mid Century" 這類拼接，Opus 審查 3），再整理空白 / 標點。"""
    t = title
    while True:
        t2 = re.sub(r'\s{2,}', ' ', re.sub(r'\s+([,.;)])', r'\1', STYLE_PAT.sub('', t))).strip(' ,-')
        if t2 == t:
            return t
        t = t2


def vote(vals, claude):
    vs = [v for v in vals if v]
    c = collections.Counter(vs)
    if c and c.most_common(1)[0][1] >= 2:
        return c.most_common(1)[0][0]
    return claude or (vs[0] if vs else None)


def load():
    items = {it['id']: it for it in stage1_items() + stage2_items()}
    si = {r['id']: r for r in read_jsonl(S / 'ann_single_item.jsonl') if r.get('ok')}
    P = {}
    for r in read_jsonl(S / 'annotations_all.jsonl'):
        a = [r['claude'], r['qwen'], r['gemma']]
        if not r['complete'] or any(x is None for x in a):
            continue
        it = items[r['id']]; attrs = {}
        for d in ('color', 'material', 'shape', 'category', 'style'):
            attrs[d] = vote([x[d] for x in a], r['claude'][d])
        cs, ci = r['cell'].split('|')
        if r['qualified']:
            attrs['style'], attrs['category'] = CELL_STYLE[cs], CELL_ITEM[ci]
        P[r['id']] = dict(id=r['id'], parent_asin=r['parent_asin'], cell=r['cell'], cs=cs, ci=ci, qualified=r['qualified'], attrs=attrs,
                          styles={x['style'] for x in a}, title=it['title'], title_clean=clean(it['title']), claude=r['claude'], single=si.get(r['id']), allthree=a)
    return P


def main():
    P = load()
    edges = collections.defaultdict(set)
    for e in json.load(open(D / 'stage0/phash_dups.json')):
        edges[e['removed']].add(e['kept']); edges[e['kept']].add(e['removed'])
    QUAL = collections.defaultdict(list)
    for p in sorted(P.values(), key=lambda p: p['id']):
        if p['qualified']:
            QUAL[p['cell']].append(p)
    n_qual = sum(len(v) for v in QUAL.values())
    allp = sorted(P.values(), key=lambda p: p['id'])
    report = {'n_qualified_total': n_qual, 'dropped': [], 'relaxed': [], 'combos': [], 'combos_rejected': [], 'n_questions': collections.Counter(),
              'F_size': collections.defaultdict(collections.Counter), 'n_d': collections.defaultdict(collections.Counter), 'query_relaxed': []}

    def dup(a, b):
        return a['parent_asin'] == b['parent_asin'] or b['parent_asin'] in edges[a['parent_asin']]

    def clash(x, chosen):
        return any(dup(x, c) for c in chosen)

    def take(rng, pool, n, chosen, spread=None):
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

    def finish(q, qid, scen, tr, X, C, allowed, groups, extra, notes):
        """groups = [(bucket, [items])]；做硬性檢查、打亂、算 oracle，回傳 (rec, err)。"""
        cands = [(x, b) for b, g in groups for x in g]
        ids = [x['id'] for x, b in cands]
        if len(set(ids)) != len(ids):
            return None, '候選重複'
        for x, b in cands:
            at = x['attrs']
            if b == 'valid':
                continue
            if b == 'random' and X in x['styles']:
                return None, '隨機含 X'
            if M.is_valid(dict(style=at['style'], category=at['category'], color=at['color'], material=at['material'], shape=at['shape']), allowed):
                return None, '干擾項是合格'
        random.Random(f'0-stage4-order-{qid}-{tr}').shuffle(cands)
        pool = [dict(id=x['id'], style=x['attrs']['style'], category=x['attrs']['category'], color=x['attrs']['color'],
                     material=x['attrs']['material'], shape=x['attrs']['shape']) for x, b in cands]
        F = M.free_dims(pool, allowed)
        if len(F) < 2:
            return None, '|F|<2'
        o, sel = M.oracle(pool, allowed, K)
        if o['EffCov'] < 1.0 - 1e-9:
            return None, f'Oracle EffCov={o["EffCov"]:.3f}'
        vv = [p for p in pool if M.is_valid(p, allowed)]
        pairs = sum(1 for a, b in itertools.combinations(vv, 2) if all(a[d] == b[d] for d in ('color', 'material', 'shape')))
        rec = {'qid': qid, 'scenario': scen, 'query_id': q['id'], 'cell': q['cell'], 'style': X, 'category': C,
               'query': {'id': q['id'], 'parent_asin': q['parent_asin'], 'title': q['title'], 'title_clean': q['title_clean'], 'color': q['attrs']['color'],
                         'material': q['attrs']['material'], 'shape': q['attrs']['shape']},
               'allowed': {k: sorted(v) for k, v in allowed.items()}, 'free_dims': F, 'dup_pairs_valid': pairs, 'try': tr, 'notes': notes,
               'oracle_selection': [x['id'] for x in sel], 'n_same_cat_valid': sum(1 for p in vv if p['category'] == C), 'seed': f'0-stage4-{qid}-{tr}',
               'candidates': [dict(pos=i + 1, id=x['id'], parent_asin=x['parent_asin'], title=x['title'], title_clean=x['title_clean'], bucket=b,
                                   valid=M.is_valid(pool[i], allowed), cell=x['cell'], style=pool[i]['style'], category=pool[i]['category'], color=pool[i]['color'],
                                   material=pool[i]['material'], shape=pool[i]['shape']) for i, (x, b) in enumerate(cands)]} | extra
        return rec, None

    # ---------------- T4 Negation：query = 階段 3 的 108 個 ----------------
    T3q = json.load(open(T / 'questions.json'))
    qids = sorted({r['query_id'] for r in T3q})

    def build_t4(q, tr):
        qid = f'{q["id"]}-T4'; rng = random.Random(f'0-stage4-T4-{q["id"]}-{tr}')
        qs, qc = q['cs'], q['ci']; X = CELL_STYLE[qs]; C = CELL_ITEM[qc]; chosen = [q]; notes = []
        allowed = {'style': {X}, 'category': ALL_CATS - {C}}
        others = [x for c in CELLS if c.split('|')[0] == qs and c.split('|')[1] != qc for x in QUAL[c]]
        valid = take(rng, others, 12, chosen, spread=lambda x: x['ci'])
        if len(valid) != 12:
            return None, '合格不足 12'
        chosen += valid
        trap = take(rng, [x for x in QUAL[q['cell']] if x['id'] != q['id']], 12, chosen)
        if len(trap) != 12:
            return None, '陷阱不足 12'
        chosen += trap
        hard = take(rng, [x for c in CELLS if c.split('|')[0] != qs and c.split('|')[1] != qc for x in QUAL[c]], 8, chosen, spread=lambda x: x['cs'])
        if len(hard) != 8:
            return None, '困難干擾不足'
        chosen += hard
        rnd = take(rng, [x for x in allp if X not in x['styles'] and x['id'] != q['id']], 8, chosen)
        if len(rnd) != 8:
            return None, '隨機不足'
        extra = {'excluded_category': C, 'n_valid_categories': len({x['attrs']['category'] for x in valid})}
        return finish(q, qid, 'T4', tr, X, C, allowed, [('valid', valid), ('trap', trap), ('hard', hard), ('random', rnd)], extra, notes)

    out = []
    for qid_ in qids:
        q = P[qid_]; why = collections.Counter(); rec = None
        for tr in range(200):
            rec, err = build_t4(q, tr)
            if rec:
                break
            why[err] += 1
        if rec is None:
            report['dropped'].append({'qid': f'{qid_}-T4', 'reasons': dict(why)}); continue
        if rec['try']:
            rec['retry_reasons'] = dict(why)
        out.append(rec); report['n_questions']['T4'] += 1; report['F_size']['T4'][len(rec['free_dims'])] += 1
        for d, n in rec['free_dims'].items():
            report['n_d'][f'T4|{d}'][n] += 1

    # ---------------- T3 多重限制 ----------------
    combos = []
    for cell in CELLS:
        if cell.endswith('|wall_art'):
            continue
        qual = QUAL[cell]; tot = len(qual)
        for a in ('material', 'color'):
            for v in sorted({p['attrs'][a] for p in qual}):
                m = [p for p in qual if p['attrs'][a] == v]; n = len(m)
                info = {'cell': cell, 'attr': a, 'value': v, 'n': n, 'total': tot, 'excluded': round(1 - n / tot, 3)}
                other = [d for d in ('color', 'material', 'shape') if d != a]
                info['other_nd'] = {d: len({p['attrs'][d] for p in m}) for d in other}
                why = []
                if n < 12: why.append('n<12')
                if 1 - n / tot < 0.30: why.append('排除比例<30%')
                if any(x < 2 for x in info['other_nd'].values()): why.append('另兩屬性值數<2')
                if why:
                    if n >= 8:
                        info['why'] = why; report['combos_rejected'].append(info)
                else:
                    combos.append(info)
    report['combos'] = combos
    report['n_combos'] = len(combos); report['n_cells_with_combo'] = len({c['cell'] for c in combos})

    def q_level(cell, strict):
        cs = CELL_STYLE[cell.split('|')[0]]
        return [p for p in QUAL[cell] if p['single'] and p['single']['single_item'] == 'yes' and p['single']['single_item_conf'] >= 2
                and (not strict or (all(x['style'] == cs for x in p['allthree']) and p['claude']['style_conf'] == 3))]

    def build_t3(q, combo, ci_, tr):
        a, v, cell = combo['attr'], combo['value'], combo['cell']
        qid = f'{q["id"]}-T3-c{ci_:02d}'; rng = random.Random(f'0-stage4-T3-{qid}-{tr}')
        qs, qc = q['cs'], q['ci']; X = CELL_STYLE[qs]; C = CELL_ITEM[qc]; chosen = [q]; notes = []
        allowed = {'style': {X}, 'category': {C}, a: {v}}
        valid = take(rng, [x for x in QUAL[cell] if x['attrs'][a] == v and x['id'] != q['id']], 12, chosen)
        if len(valid) != 12:
            return None, '合格不足 12'
        chosen += valid
        pool = [x for x in QUAL[cell] if x['attrs'][a] != v and x['id'] != q['id']]
        atrap = take(rng, pool, 12, chosen); fill = []
        if len(atrap) < 12:
            fp = [x for c in CELLS if c.split('|')[0] == qs and c != cell for x in QUAL[c] if x['attrs'][a] == v]
            fill = take(rng, fp, 12 - len(atrap), chosen + atrap)
            notes.append(f'屬性陷阱只有 {len(atrap)} 件，用風格 X 其他品項且 {a}={v} 的合格商品補 {len(fill)} 件')
        if len(atrap) + len(fill) != 12:
            return None, '屬性陷阱不足'
        chosen += atrap + fill
        sp = [x for c in CELLS if c.split('|')[1] == qc and c.split('|')[0] != qs for x in QUAL[c]]
        strap = take(rng, [x for x in sp if x['attrs'][a] == v], 8, chosen, spread=lambda x: x['cs']); sfill = []
        if len(strap) < 8:
            sfill = take(rng, [x for x in sp if x['attrs'][a] != v], 8 - len(strap), chosen + strap, spread=lambda x: x['cs'])
            notes.append(f'風格陷阱只有 {len(strap)} 件 {a}={v}，放寬為 {a} 任意補 {len(sfill)} 件')
        if len(strap) + len(sfill) != 8:
            return None, '風格陷阱不足'
        chosen += strap + sfill
        rnd = take(rng, [x for x in allp if X not in x['styles'] and x['id'] != q['id']], 8, chosen)
        if len(rnd) != 8:
            return None, '隨機不足'
        extra = {'attr': a, 'value': v, 'combo_id': f'c{ci_:02d}', 'combo_n': combo['n'], 'combo_excluded': combo['excluded'],
                 'query_attr_equals_v': q['attrs'][a] == v, 'n_attr_trap_fill': len(fill), 'n_style_trap_fill': len(sfill)}
        groups = [('valid', valid), ('attr_trap', atrap), ('attr_trap_fill', fill), ('style_trap', strap), ('style_trap_loose', sfill), ('random', rnd)]
        return finish(q, qid, 'T3', tr, X, C, allowed, [g for g in groups if g[1]], extra, notes)

    for ci_, combo in enumerate(combos):
        want = 2 if combo['n'] == 12 else 3
        strict = q_level(combo['cell'], True); loose = [p for p in q_level(combo['cell'], False) if p not in strict]
        rng = random.Random(f'0-stage4-T3-query-{combo["cell"]}-{combo["attr"]}-{combo["value"]}')
        order = strict[:]; rng.shuffle(order); lo = loose[:]; rng.shuffle(lo)
        got = []; used_loose = 0
        for q in order + lo:
            if len(got) == want:
                break
            why = collections.Counter(); rec = None
            for tr in range(200):
                rec, err = build_t3(q, combo, ci_, tr)
                if rec:
                    break
                why[err] += 1
            if rec is None:
                report['dropped'].append({'qid': f'{q["id"]}-T3-c{ci_:02d}', 'reasons': dict(why)}); continue
            if q in lo:
                used_loose += 1; rec['notes'].append('query 放寬：合格 + single_item yes conf>=2（不要求三位風格一致、Claude 信心 3）')
            if rec['try']:
                rec['retry_reasons'] = dict(why)
            got.append(rec)
        combo['n_strict_queries'] = len(strict); combo['n_questions'] = len(got); combo['used_loose_queries'] = used_loose
        if len(got) < want:
            report['relaxed'].append({'combo': f'c{ci_:02d}', 'cell': combo['cell'], 'want': want, 'got': len(got)})
        for rec in got:
            out.append(rec); report['n_questions']['T3'] += 1; report['n_questions'][f'T3|{combo["cell"]}'] += 1
            report['F_size']['T3'][len(rec['free_dims'])] += 1
            for d, n in rec['free_dims'].items():
                report['n_d'][f'T3|{d}'][n] += 1
            if rec['notes']:
                report['relaxed'].append({'qid': rec['qid'], 'notes': rec['notes']})

    # S1/S2 原樣沿用
    for r in T3q:
        out.append(dict(r, source='stage3'))
    report['n_questions_total'] = len(out)
    report['n_t3_queries_unique'] = len({r['query_id'] for r in out if r['scenario'] == 'T3'})
    json.dump(out, open(U / 'questions4.json', 'w'), ensure_ascii=False, indent=1)
    json.dump(report, open(U / 'build_report4.json', 'w'), ensure_ascii=False, indent=1, default=lambda x: dict(x))
    print(json.dumps({'n_combos': len(combos), 'cells': report['n_cells_with_combo'], 'T4': report['n_questions']['T4'], 'T3': report['n_questions']['T3'],
                      'dropped': len(report['dropped']), 'qualified': n_qual}))


if __name__ == '__main__':
    main()
