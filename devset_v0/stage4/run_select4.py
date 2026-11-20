"""階段 4 選品。python3 -I run_select4.py --model NAME --url URL --wording tmpl_zh|tmpl_en|syn_en --scenarios T3,T4 [--orders o0,o1,o2] [--no-think] [--limit-queries N] [--tag _x]
輸出 out/<model>/select_<wording>_<order>.jsonl（可續跑）。prompt 結構同階段 3 run_select.py，文字由 texts4.py 產生。"""
import argparse, json, random
from datetime import datetime, timezone
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from common3 import *   # noqa
from texts4 import intro, task_text, json_text   # noqa

U = T   # common3 的 T = 本檔所在資料夾 = stage4


def build(q, cands, wording, syn):
    n = len(cands)
    content = [{'type': 'text', 'text': intro(wording)}, {'type': 'image_url', 'image_url': {'url': img_url(q['query']['parent_asin'])}},
               {'type': 'text', 'text': task_text(q, wording, n, syn)}]
    for c in cands:
        content.append({'type': 'text', 'text': f'POSITION {c["pos"]}; title={c["title_clean"]}'})
        content.append({'type': 'image_url', 'image_url': {'url': img_url(c['parent_asin'])}})
    content.append({'type': 'text', 'text': json_text(wording, n)})
    return content


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--url', required=True)
    ap.add_argument('--wording', required=True, choices=['tmpl_zh', 'tmpl_en', 'syn_en']); ap.add_argument('--scenarios', default='S1,S2,T3,T4')
    ap.add_argument('--no-think', action='store_true'); ap.add_argument('--orders', default='o0'); ap.add_argument('--limit-queries', type=int, default=0)
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    short = a.model.replace('-devset4', ''); out = U / 'out' / short; out.mkdir(parents=True, exist_ok=True)
    sc = set(a.scenarios.split(','))
    qs = [q for q in json.load(open(U / 'questions4.json')) if q['scenario'] in sc]
    if a.limit_queries:
        # smoke：每種題型各取前 N 個 query
        keep = set()
        for s in sorted(sc):
            keep |= {q['qid'] for q in [x for x in qs if x['scenario'] == s][:a.limit_queries]}
        qs = [q for q in qs if q['qid'] in keep]
    texts = json.load(open(U / 'query_texts.json')) if a.wording == 'syn_en' else {}
    for order in a.orders.split(','):
        path = out / f'select{a.tag}_{a.wording}_{order}.jsonl'; have = done_keys(path, 'qid')
        with open(path, 'a') as fh:
            for q in qs:
                if q['qid'] in have:
                    continue
                cands = list(q['candidates']); n = len(cands); orig = None
                if order != 'o0':
                    random.Random(f'stage4-{order}-{q["qid"]}').shuffle(cands)
                    orig = [c['pos'] for c in cands]
                    cands = [dict(c, pos=i) for i, c in enumerate(cands, 1)]
                syn = texts[q['qid']]['syn_en'] if a.wording == 'syn_en' else None
                content = build(q, cands, a.wording, syn)
                def val(o):
                    sel = o.get('selected_positions')
                    if not (isinstance(sel, list) and len(sel) == K and len(set(sel)) == K and all(isinstance(x, int) and not isinstance(x, bool) and 1 <= x <= n for x in sel)):
                        raise ValueError(f'invalid selection {sel}')
                    return sel
                st, sel, att = request_with_retry(a.url, a.model, content, a.no_think, val, 'selected_positions')
                m = (lambda xs: [orig[x - 1] for x in xs]) if orig else (lambda xs: list(xs))
                rec = {'qid': q['qid'], 'query_id': q['query_id'], 'scenario': q['scenario'], 'wording': a.wording, 'order': order, 'status': st,
                       'selected_positions': m(sel) if sel else None, 'shown_positions': sel, 'attempt': att, 'syn_text': syn,
                       'raw_output': LAST.get('raw'), 'usage': LAST.get('usage'), 'latency_s': LAST.get('latency'), 'finish_reason': LAST.get('finish'),
                       'finished_at': datetime.now(timezone.utc).isoformat()}
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); fh.flush()
                print(a.wording, order, q['qid'], rec['selected_positions'], st, (rec['usage'] or {}).get('prompt_tokens'), flush=True)
    print('DONE select', a.wording, flush=True)


if __name__ == '__main__':
    main()
