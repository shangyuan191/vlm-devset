"""C2-1 風格判斷：每個 query 一次，只給 query 圖 + 11 個風格（附一句話定義），單選。輸出 out/<model>/style.jsonl（可續跑）。
用法： python3 -I run_style.py --model NAME --url URL [--no-think] [--limit N]"""
import argparse, json
from datetime import datetime, timezone
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from common3 import *   # noqa


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--url', required=True)
    ap.add_argument('--no-think', action='store_true'); ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    short = a.model.replace('-devset3', ''); out = T / 'out' / short; out.mkdir(parents=True, exist_ok=True)
    qs = json.load(open(T / 'questions.json')); seen = {}
    for q in qs:
        seen.setdefault(q['query_id'], q)
    todo = sorted(seen.values(), key=lambda q: q['query_id'])
    path = out / 'style.jsonl'; have = done_keys(path, 'query_id')
    todo = [q for q in todo if q['query_id'] not in have]
    if a.limit:
        todo = todo[:a.limit]
    opts = '\n'.join(f'- {o}：{STYLE_DEF[o]}' for o in OPTIONS['style'])
    with open(path, 'a') as fh:
        for q in todo:
            content = [{'type': 'text', 'text': '請看這張家具 / 家飾商品圖片：'},
                       {'type': 'image_url', 'image_url': {'url': img_url(q['query']['parent_asin'])}},
                       {'type': 'text', 'text': '請判斷這件商品屬於下列哪一種風格，只能單選一個：\n' + opts +
                        '\n\n請只回傳 JSON，不要 Markdown。格式如下（尖括號是要你填入的內容，不是答案）：{"style":"<上面選項中的一個，照抄英文>"}'}]
            def val(o):
                s = str(o['style']).strip().lower()
                if s not in OPTIONS['style']:
                    raise ValueError(f'bad style {s}')
                return s
            st, ans, att = request_with_retry(a.url, a.model, content, a.no_think, val, 'style')
            rec = {'query_id': q['query_id'], 'cell': q['cell'], 'gold': CELL_STYLE[q['cell'].split('|')[0]], 'status': st, 'answer': ans,
                   'attempt': att, 'raw_output': LAST.get('raw'), 'usage': LAST.get('usage'), 'latency_s': LAST.get('latency'),
                   'finish_reason': LAST.get('finish'), 'finished_at': datetime.now(timezone.utc).isoformat()}
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); fh.flush()
            print(q['query_id'], ans, rec['gold'], flush=True)
    print('DONE style', flush=True)


if __name__ == '__main__':
    main()
