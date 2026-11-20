"""階段 5：正確 caption 階梯。用法：python3 -I run_caption.py --model NAME --url URL --conditions c1,c2 [--orders o0,o1,o2] [--limit-queries N] [--tag _x] [--no-think]
輸出 out/<model>/select<tag>_<cond>_<order>.jsonl（可續跑）。prompt 除開頭與任務句的「參考圖片→參考商品」外，其餘同 stage3/run_select.py 的 build()。"""
import argparse, json, random
from datetime import datetime, timezone
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from common3 import *   # noqa
V = Path(__file__).resolve().parent; T = V.parent / 'stage3'
QFILE = T / 'questions.json'
CONDS = {'cap_g0': [], 'cap_g1': ['style'], 'cap_g2': ['style', 'category'], 'cap_g3': ['style', 'category', 'material'],
         'cap_g4': ['style', 'category', 'material', 'color'], 'cap_g5': ['style', 'category', 'material', 'color', 'shape'],
         'cap_g5_nostyle': ['category', 'material', 'color', 'shape'], 'img_goldstyle': None}
DIM_ZH = {'style': '風格', 'category': '品項', 'material': '材質', 'color': '顏色', 'shape': '形狀'}
ORDER_CONDS = ['cap_g1', 'img_goldstyle', 'cap_g0', 'cap_g2', 'cap_g3', 'cap_g4', 'cap_g5', 'cap_g5_nostyle']


def gold(q):
    return {'style': q['style'], 'category': q['category'], 'material': q['query']['material'], 'color': q['query']['color'], 'shape': q['query']['shape']}


def build(q, cands, cond):
    n = len(cands); g = gold(q); dims = CONDS[cond]; cap_lines = []
    if cond == 'img_goldstyle':
        content = [{'type': 'text', 'text': '使用者附上一張參考商品圖片，想找和它風格一樣的商品。參考圖片如下：'},
                   {'type': 'image_url', 'image_url': {'url': img_url(q['query']['parent_asin'])}},
                   {'type': 'text', 'text': f'參考商品的風格是：{g["style"]}'}]
        cap_lines = [f'參考商品的風格是：{g["style"]}']
    elif cond == 'cap_g0':
        content = [{'type': 'text', 'text': '使用者想找和某件參考商品風格一樣的商品，但這次沒有提供參考商品的圖片或描述。'}]
    else:
        cap_lines = [f'- {DIM_ZH[d]}：{g[d]}' for d in dims]
        content = [{'type': 'text', 'text': '使用者想找和某件參考商品風格一樣的商品。這次沒有參考商品的圖片，只有它的描述：\n' + '\n'.join(cap_lines)}]
    ref = '參考圖片' if cond == 'img_goldstyle' else '參考商品'   # img_goldstyle 與 style_given 完全相同（DECISIONS 2）
    if q['scenario'] == 'S1':
        task = f'以下是 {n} 件候選商品。請從候選中挑 {K} 件和{ref}**同風格**的商品，並且讓這 {K} 件盡量多樣：品項、顏色、材質、形狀盡量不同。'
    else:
        task = (f'以下是 {n} 件候選商品。請從候選中挑 {K} 件和{ref}**同風格、而且同樣是{CAT_ZH[q["category"].replace("/", "_").replace(" ", "_")]}**的商品，'
                f'並且讓這 {K} 件盡量多樣：顏色、材質、形狀盡量不同。')
    content.append({'type': 'text', 'text': task})
    for c in cands:
        content.append({'type': 'text', 'text': f'POSITION {c["pos"]}; title={c["title_clean"]}'})
        content.append({'type': 'image_url', 'image_url': {'url': img_url(c['parent_asin'])}})
    content.append({'type': 'text', 'text': '請只回傳 JSON，不要 Markdown。格式如下（尖括號是要你填入的內容，不是答案）：{"selected_positions":[<position>, ...]}'
                    f'。position 使用 1-based position；selected_positions 剛好 {K} 個且不得重複；請根據圖片和標題實際判斷後再選。'})
    return content, cap_lines


def render(content):
    return '\n'.join(c['text'] if c['type'] == 'text' else '[IMAGE]' for c in content)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--url', required=True)
    ap.add_argument('--conditions', default=','.join(ORDER_CONDS)); ap.add_argument('--no-think', action='store_true')
    ap.add_argument('--orders', default='o0,o1,o2'); ap.add_argument('--limit-queries', type=int, default=0); ap.add_argument('--tag', default='')
    ap.add_argument('--dump-prompts', action='store_true')
    a = ap.parse_args()
    short = a.model.replace('-devset5', ''); out = V / 'out' / short; out.mkdir(parents=True, exist_ok=True)
    qs = json.load(open(QFILE))
    if a.limit_queries:
        keep = sorted({q['query_id'] for q in qs})[:a.limit_queries]; qs = [q for q in qs if q['query_id'] in keep]
    if a.dump_prompts:
        (V / 'logs').mkdir(exist_ok=True)
        for cond in CONDS:
            q = next(x for x in qs if x['scenario'] == 'S2') if False else qs[0]
            content, _ = build(q, list(q['candidates']), cond)
            (V / 'logs' / f'prompt_example_{cond}.txt').write_text(f'# {q["qid"]}（完整文字；[IMAGE] = 一張圖）\n' + render(content) + '\n')
        return
    for cond in a.conditions.split(','):
        for order in a.orders.split(','):
            path = out / f'select{a.tag}_{cond}_{order}.jsonl'; have = done_keys(path, 'qid')
            with open(path, 'a') as fh:
                for q in qs:
                    if q['qid'] in have:
                        continue
                    cands = list(q['candidates']); n = len(cands); orig = None
                    if order != 'o0':
                        random.Random(f'stage3-{order}-{q["qid"]}').shuffle(cands)
                        orig = [c['pos'] for c in cands]
                        cands = [dict(c, pos=i) for i, c in enumerate(cands, 1)]
                    content, cap_lines = build(q, cands, cond)
                    def val(o):
                        sel = o.get('selected_positions')
                        if not (isinstance(sel, list) and len(sel) == K and len(set(sel)) == K and all(isinstance(x, int) and not isinstance(x, bool) and 1 <= x <= n for x in sel)):
                            raise ValueError(f'invalid selection {sel}')
                        return sel
                    st, sel, att = request_with_retry(a.url, a.model, content, a.no_think, val, 'selected_positions')
                    m = (lambda xs: [orig[x - 1] for x in xs]) if orig else (lambda xs: list(xs))
                    rec = {'qid': q['qid'], 'query_id': q['query_id'], 'scenario': q['scenario'], 'condition': cond, 'order': order, 'status': st,
                           'selected_positions': m(sel) if sel else None, 'shown_positions': sel, 'attempt': att, 'caption_lines': cap_lines,
                           'has_image': sum(c['type'] == 'image_url' for c in content) - n, 'raw_output': LAST.get('raw'), 'usage': LAST.get('usage'),
                           'latency_s': LAST.get('latency'), 'finish_reason': LAST.get('finish'), 'finished_at': datetime.now(timezone.utc).isoformat()}
                    fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); fh.flush()
                    print(cond, order, q['qid'], rec['selected_positions'], st, (rec['usage'] or {}).get('prompt_tokens'), flush=True)
    print('DONE caption', flush=True)


if __name__ == '__main__':
    main()
