"""§4.5 SigLIP2 文字檢索基準線（CPU）。用 R/.venv/bin/python -I siglip_text.py。
固定英文模板（gold caption → 一句話）：
  g1: a {style} style item
  g2: a {style} style {category}
  g3: a {style} style {category}, made of {material}
  g4: ... , made of {material}, {color} color
  g5: ... , {shape} shape
  g5_nostyle: a {category}, made of {material}, {color} color, {shape} shape
（category 'chandelier/pendant' 寫成 'chandelier pendant light'、'lamp' 照寫；material 的 'plastic/acrylic' 等斜線保留原文。）
SigLIP2 文字編碼器：padding='max_length'、max_length=64（SigLIP 官方用法）；候選圖向量用 stage3/siglip_emb.json。
選法：top5 = 文字–候選相似度前 5；mmr-std = λ0.7 * 文字相似 − 0.3 * 與已選的最大圖–圖相似（同 T/baselines.py）。"""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
V = Path(__file__).resolve().parent; T = V.parent / 'stage3'; R = V.parent.parent
QS = json.load(open(T / 'questions.json')); K = 5
CAT = {'chandelier/pendant': 'chandelier pendant light'}


def caption(q, cond):
    s, c, m, col, sh = q['style'], CAT.get(q['category'], q['category']), q['query']['material'], q['query']['color'], q['query']['shape']
    return {'cap_g1': f'a {s} style item', 'cap_g2': f'a {s} style {c}', 'cap_g3': f'a {s} style {c}, made of {m}',
            'cap_g4': f'a {s} style {c}, made of {m}, {col} color', 'cap_g5': f'a {s} style {c}, made of {m}, {col} color, {sh} shape',
            'cap_g5_nostyle': f'a {c}, made of {m}, {col} color, {sh} shape'}[cond]


def main():
    import torch
    from transformers import AutoModel, AutoProcessor
    emb = json.load(open(T / 'siglip_emb.json'))
    mp = R / 'models/siglip2-so400m-patch14-384'; model = AutoModel.from_pretrained(mp).eval(); proc = AutoProcessor.from_pretrained(mp)
    conds = ['cap_g1', 'cap_g2', 'cap_g3', 'cap_g4', 'cap_g5', 'cap_g5_nostyle']
    texts = sorted({caption(q, c) for q in QS for c in conds}); tv = {}
    for i in range(0, len(texts), 32):
        b = texts[i:i + 32]
        with torch.no_grad():
            e = model.get_text_features(**proc(text=b, padding='max_length', max_length=64, return_tensors='pt'))
        e = getattr(e, 'pooler_output', e); e = e / e.norm(dim=-1, keepdim=True)
        for t, v in zip(b, e.tolist()): tv[t] = v
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    for cond in conds:
        outs = {'siglip2txt-top5': [], 'siglip2txt-mmr-std': []}
        for q in QS:
            t = tv[caption(q, cond)]; cs = q['candidates']; sim = {c['pos']: dot(t, emb[c['parent_asin']]) for c in cs}; byp = {c['pos']: c for c in cs}
            outs['siglip2txt-top5'].append((q, sorted(sim, key=lambda p: -sim[p])[:K]))
            sel = []; rest = [c['pos'] for c in cs]
            while len(sel) < K:
                sc = lambda p: 0.7 * sim[p] - 0.3 * max((dot(emb[byp[p]['parent_asin']], emb[byp[s]['parent_asin']]) for s in sel), default=0)
                b = max(rest, key=sc); sel.append(b); rest.remove(b)
            outs['siglip2txt-mmr-std'].append((q, sel))
        for n, rows in outs.items():
            d = V / 'out' / n; d.mkdir(parents=True, exist_ok=True)
            with open(d / f'select_{cond}_o0.jsonl', 'w') as f:
                for q, sel in rows:
                    f.write(json.dumps({'qid': q['qid'], 'query_id': q['query_id'], 'scenario': q['scenario'], 'condition': cond, 'order': 'o0', 'status': 'ok',
                                        'selected_positions': sel, 'shown_positions': sel, 'caption_text': caption(q, cond)}) + '\n')
    print('done', len(texts), 'texts')


if __name__ == '__main__':
    main()
