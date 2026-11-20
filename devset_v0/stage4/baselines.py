"""C3 不用 GPU 的基準線。用法： R/.venv/bin/python -I baselines.py
- Random：每題蒙地卡羅 1000 次期望值（seed 固定）→ results/random_expect.json
- Oracle：題目建好時已檢查 = 1.00；這裡用題目內存的 oracle_selection 重算 → results/oracle.json
- SigLIP2 top-5 / SigLIP2+MMR（自由維度輪流版）/ SigLIP2+標準 MMR(λ=0.7) → out/<name>/select_tmpl_zh_o0.jsonl（格式同模型輸出）
自由維度輪流版 MMR：取 cosine 前 10；從 query 最像的一件開始，依該題自由維度（依 color、material、shape、category 固定順序）輪流，
  每輪在前 10 名中挑「該維度值還沒被選過、cosine 最高」的一件；挑不到就挑剩下 cosine 最高的；直到 5 件。不看風格 / 合格資訊。"""
import json, random, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
T = Path(__file__).resolve().parent; R = T.parent.parent
sys.path.insert(0, str(R / 'overnight_2026-11-14' / 'D_main_table'))
import metrics as M

QS = json.load(open(T / 'questions4.json')); K = 5
(T / 'results').mkdir(exist_ok=True)


def pools(q):
    pool = [dict(id=c['id'], style=c['style'], category=c['category'], color=c['color'], material=c['material'], shape=c['shape']) for c in q['candidates']]
    return pool, {k: set(v) for k, v in q['allowed'].items()}


def random_part():
    out = {}
    for q in QS:
        pool, allowed = pools(q); rng = random.Random(f'0-stage4-random-{q["qid"]}'); a = e = 0; dv = []
        for _ in range(1000):
            s = M.score(rng.sample(pool, K), pool, allowed, K); a += s['Align']; e += s['EffCov']
            if s['Div'] is not None: dv.append(s['Div'])
        out[q['qid']] = {'Align': a / 1000, 'EffCov': e / 1000, 'Div': sum(dv) / len(dv) if dv else None, 'p_v2': len(dv) / 1000}
    json.dump(out, open(T / 'results/random_expect.json', 'w'))
    orc = {}
    for q in QS:
        pool, allowed = pools(q); by = {p['id']: p for p in pool}
        s = M.score([by[i] for i in q['oracle_selection']], pool, allowed, K); orc[q['qid']] = s
    json.dump(orc, open(T / 'results/oracle.json', 'w'))
    print('random/oracle done', sum(v['EffCov'] for v in orc.values()) / len(orc))


def embed():
    import torch
    from PIL import Image
    from transformers import AutoModel, AutoProcessor
    cache = T / 'siglip_emb.json'; emb = json.load(open(cache)) if cache.exists() else {}
    asins = sorted({q['query']['parent_asin'] for q in QS} | {c['parent_asin'] for q in QS for c in q['candidates']})
    todo = [a for a in asins if a not in emb]
    if todo:
        torch.set_num_threads(8)
        mp = R / 'models/siglip2-so400m-patch14-384'; model = AutoModel.from_pretrained(mp).eval(); proc = AutoProcessor.from_pretrained(mp); t = time.time()
        for i in range(0, len(todo), 16):
            ims = [Image.open(R / 'data/derived/devset_images' / f'{a}.jpg').convert('RGB') for a in todo[i:i + 16]]
            with torch.no_grad():
                e = model.get_image_features(**proc(images=ims, return_tensors='pt'))
            e = getattr(e, 'pooler_output', e); e = e / e.norm(dim=-1, keepdim=True)
            for a, v in zip(todo[i:i + 16], e.tolist()): emb[a] = v
            print(f'{i + len(ims)}/{len(todo)} {time.time() - t:.0f}s', flush=True)
            if (i // 16) % 20 == 0: cache.write_text(json.dumps(emb))
        cache.write_text(json.dumps(emb))
    return emb


def main():
    random_part()
    emb = embed()
    cos = lambda a, b: sum(x * y for x, y in zip(emb[a], emb[b]))
    outs = {n: [] for n in ('siglip2-top5', 'siglip2-mmr-free', 'siglip2-mmr-std')}
    for q in QS:
        qa = q['query']['parent_asin']; cs = q['candidates']
        sim = {c['pos']: cos(qa, c['parent_asin']) for c in cs}; byp = {c['pos']: c for c in cs}
        rank = sorted(cs, key=lambda c: -sim[c['pos']])
        outs['siglip2-top5'].append((q, [c['pos'] for c in rank[:K]]))
        F = [d for d in ('color', 'material', 'shape', 'category') if d in q['free_dims']]
        top = rank[:10]; pick = [top[0]]; i = 0
        while len(pick) < K:
            d = F[i % len(F)]; i += 1
            seen = {p[d] for p in pick}; left = [c for c in top if c not in pick]
            good = [c for c in left if c[d] not in seen]
            pick.append((good or left)[0])
        outs['siglip2-mmr-free'].append((q, [c['pos'] for c in pick]))
        sel = []; rest = [c['pos'] for c in cs]
        while len(sel) < K:
            def sc(p):
                red = max((cos(byp[p]['parent_asin'], byp[s]['parent_asin']) for s in sel), default=0)
                return 0.7 * sim[p] - 0.3 * red
            b = max(rest, key=sc); sel.append(b); rest.remove(b)
        outs['siglip2-mmr-std'].append((q, sel))
    for n, rows in outs.items():
        d = T / 'out' / n; d.mkdir(parents=True, exist_ok=True)
        with open(d / 'select_tmpl_zh_o0.jsonl', 'w') as f:
            for q, sel in rows:
                f.write(json.dumps({'qid': q['qid'], 'query_id': q['query_id'], 'scenario': q['scenario'], 'wording': 'tmpl_zh', 'order': 'o0', 'status': 'ok', 'selected_positions': sel}) + '\n')
    print('baselines done')


if __name__ == '__main__':
    main()
