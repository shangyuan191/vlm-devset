"""階段 2 本地 VLM 標註者（複製自 stage1/annotate_local.py：改讀 S/items.jsonl；沒有待標時若 Claude 還在發新輪就等）。一張圖一個請求，temperature 0，可續跑。

用法： python3 -I annotate_local.py --model SERVED_NAME --url http://127.0.0.1:PORT/v1/chat/completions --out ann_xxx.jsonl [--no-think]
解析失敗重試 1 次，仍失敗記 failed（不再重試）。server 連不上就直接停（不寫 failed）。
"""
import argparse, base64, json, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common2 import SYSTEM_PROMPT, FINAL_TEXT, S as HERE, parse_lines, read_jsonl  # noqa: E402
import os, signal

MAX_TOKENS = 300


def post(url, model, content, nothink):
    payload = {'model': model, 'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': content}], 'max_tokens': MAX_TOKENS, 'temperature': 0}
    if nothink:
        payload['chat_template_kwargs'] = {'enable_thinking': False}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True); ap.add_argument('--url', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--no-think', action='store_true'); ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    out = HERE / a.out
    while True:
        sample = read_jsonl(HERE / 'items.jsonl')
        done = {json.loads(l)['id'] for l in open(out)} if out.exists() else set()
        todo = [s for s in sample if s['id'] not in done]
        if a.limit:
            todo = todo[:a.limit]
        if not todo:
            if claude_running():
                time.sleep(60); continue
            break
        print(f'{len(sample)} items, {len(done)} done, {len(todo)} to do', flush=True)
        run(a, todo, out)
    print('finished', flush=True)


def claude_running():
    p = HERE / 'claude_main.pid'
    try:
        os.kill(int(p.read_text().strip()), 0); return True
    except Exception:
        return False


def run(a, todo, out):
    with open(out, 'a', encoding='utf-8') as f:
        for i, s in enumerate(todo):
            b64 = base64.b64encode((HERE / s['ann_image']).read_bytes()).decode()
            content = [{'type': 'text', 'text': f"item_id: {s['id']}"},
                       {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                       {'type': 'text', 'text': FINAL_TEXT}]
            rec = {'id': s['id'], 'model': a.model, 'tries': []}
            ann = None
            for attempt in (1, 2):
                t0 = time.time()
                resp = post(a.url, a.model, content, a.no_think)     # 連線錯誤直接丟例外停止
                text = resp['choices'][0]['message'].get('content') or ''
                good, bad = parse_lines(text)
                good = [g for g in good if g['id'] == s['id']] or ([dict(good[0], id=s['id'])] if len(good) == 1 else [])
                rec['tries'].append({'latency_s': round(time.time() - t0, 3), 'raw_output': text, 'usage': resp.get('usage'),
                                     'finish_reason': resp['choices'][0].get('finish_reason'), 'errors': bad})
                if good:
                    ann = good[0]; break
            rec['ok'] = ann is not None; rec['ann'] = ann
            f.write(json.dumps(rec, ensure_ascii=False) + '\n'); f.flush()
            if (i + 1) % 50 == 0:
                print(i + 1, flush=True)


if __name__ == '__main__':
    main()
