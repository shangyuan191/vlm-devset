"""C2-2/3 選品：每題（S1、S2）× 3 個順序（o0 原順序、o1、o2 打亂）。條件 img / style_given。輸出 out/<model>/select_<cond>_<order>.jsonl（可續跑）。
用法： python3 -I run_select.py --model NAME --url URL --condition img|style_given [--no-think] [--orders o0,o1,o2] [--limit-queries N]"""
import argparse, json, random
from datetime import datetime, timezone
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from common3 import *   # noqa


def build(q, cands, style_line):
    n = len(cands)
    content = [{'type': 'text', 'text': '使用者附上一張參考商品圖片，想找和它風格一樣的商品。參考圖片如下：'},
               {'type': 'image_url', 'image_url': {'url': img_url(q['query']['parent_asin'])}}]
    if style_line:
        content.append({'type': 'text', 'text': f'參考商品的風格是：{style_line}'})
    if q['scenario'] == 'S1':
        task = f'以下是 {n} 件候選商品。請從候選中挑 {K} 件和參考圖片**同風格**的商品，並且讓這 {K} 件盡量多樣：品項、顏色、材質、形狀盡量不同。'
    else:
        task = (f'以下是 {n} 件候選商品。請從候選中挑 {K} 件和參考圖片**同風格、而且同樣是{CAT_ZH[q["category"].replace("/", "_").replace(" ", "_")]}**的商品，'
                f'並且讓這 {K} 件盡量多樣：顏色、材質、形狀盡量不同。')
    content.append({'type': 'text', 'text': task})
    for c in cands:
        content.append({'type': 'text', 'text': f'POSITION {c["pos"]}; title={c["title_clean"]}'})
        content.append({'type': 'image_url', 'image_url': {'url': img_url(c['parent_asin'])}})
    content.append({'type': 'text', 'text': '請只回傳 JSON，不要 Markdown。格式如下（尖括號是要你填入的內容，不是答案）：{"selected_positions":[<position>, ...]}'
                    f'。position 使用 1-based position；selected_positions 剛好 {K} 個且不得重複；請根據圖片和標題實際判斷後再選。'})
    return content


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--url', required=True)
    ap.add_argument('--condition', required=True, choices=['img', 'style_given']); ap.add_argument('--no-think', action='store_true')
    ap.add_argument('--orders', default='o0,o1,o2'); ap.add_argument('--limit-queries', type=int, default=0)
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    short = a.model.replace('-devset3', ''); out = T / 'out' / short; out.mkdir(parents=True, exist_ok=True)
    qs = json.load(open(T / 'questions.json'))
    if a.limit_queries:
        keep = sorted({q['query_id'] for q in qs})[:a.limit_queries]; qs = [q for q in qs if q['query_id'] in keep]
    style_ans = {}
    sp = out / 'style.jsonl'
    if a.condition == 'style_given':
        if not sp.exists():
            raise SystemExit('style.jsonl missing')
        style_ans = {r['query_id']: r['answer'] for r in map(json.loads, open(sp)) if r['status'] == 'ok'}
    for order in a.orders.split(','):
        path = out / f'select{a.tag}_{a.condition}_{order}.jsonl'; have = done_keys(path, 'qid')
        with open(path, 'a') as fh:
            for q in qs:
                if q['qid'] in have:
                    continue
                cands = list(q['candidates']); n = len(cands)
                orig = None
                if order != 'o0':
                    random.Random(f'stage3-{order}-{q["qid"]}').shuffle(cands)
                    orig = [c['pos'] for c in cands]
                    cands = [dict(c, pos=i) for i, c in enumerate(cands, 1)]
                style_line = style_ans.get(q['query_id']) if a.condition == 'style_given' else None
                content = build(q, cands, style_line)
                def val(o):
                    sel = o.get('selected_positions')
                    if not (isinstance(sel, list) and len(sel) == K and len(set(sel)) == K and all(isinstance(x, int) and not isinstance(x, bool) and 1 <= x <= n for x in sel)):
                        raise ValueError(f'invalid selection {sel}')
                    return sel
                st, sel, att = request_with_retry(a.url, a.model, content, a.no_think, val, 'selected_positions')
                m = (lambda xs: [orig[x - 1] for x in xs]) if orig else (lambda xs: list(xs))
                rec = {'qid': q['qid'], 'query_id': q['query_id'], 'scenario': q['scenario'], 'condition': a.condition, 'order': order, 'status': st,
                       'selected_positions': m(sel) if sel else None, 'shown_positions': sel, 'attempt': att, 'style_given': style_line,
                       'style_given_missing': a.condition == 'style_given' and style_line is None,
                       'raw_output': LAST.get('raw'), 'usage': LAST.get('usage'), 'latency_s': LAST.get('latency'), 'finish_reason': LAST.get('finish'),
                       'finished_at': datetime.now(timezone.utc).isoformat()}
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); fh.flush()
                print(a.condition, order, q['qid'], rec['selected_positions'], st, (rec['usage'] or {}).get('prompt_tokens'), flush=True)
    print('DONE select', a.condition, flush=True)


if __name__ == '__main__':
    main()
