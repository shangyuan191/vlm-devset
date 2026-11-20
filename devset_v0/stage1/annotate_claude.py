"""Claude 標註者（固定 claude-opus-5-5，精簡呼叫：自訂 system prompt、不用工具、圖片 base64 直接放進訊息）。可續跑。

用法：
  python3 -I annotate_claude.py --batches 1-5                       # 主標註：sample.jsonl 的 batch 1–5（每批 20 張）
  python3 -I annotate_claude.py --recheck 40 --batch-size 5         # 品質小檢查：前 100 件中抽 40 件，每批 5 張重標 → ann_claude_recheck5.jsonl
輸出：ann_claude.jsonl（每件一行）、claude_calls.jsonl（每次呼叫一行：cost、usage、送出與回傳的 id）。
驗證：回傳 id 集合 = 送出 id 集合、每行可解析、值在選項內；缺漏或不合法的重送（每批 <= 5 張，最多 2 輪），仍失敗記 failed。
碰到用量上限：印出訊息、exit 75（不寫任何 failed）。
"""
import argparse, base64, json, os, random, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SYSTEM_PROMPT, FINAL_TEXT, HERE, parse_lines  # noqa: E402

MODEL = 'claude-opus-5-5'
WORK = HERE / 'claude_work'; WORK.mkdir(exist_ok=True)
CALLS = HERE / 'claude_calls.jsonl'


class Limit(Exception):
    pass


def call(items, tag):
    content = []
    for s in items:
        b64 = base64.b64encode((HERE / s['ann_image']).read_bytes()).decode()
        content += [{'type': 'text', 'text': f"item_id: {s['id']}"},
                    {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b64}}]
    content.append({'type': 'text', 'text': FINAL_TEXT})
    line = json.dumps({'type': 'user', 'message': {'role': 'user', 'content': content}})
    env = {k: v for k, v in os.environ.items() if k.lower() not in ('all_proxy', 'https_proxy', 'http_proxy')}
    cmd = ['claude', '-p', '--model', MODEL, '--system-prompt', SYSTEM_PROMPT, '--tools', '', '--strict-mcp-config',
           '--setting-sources', '', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose',
           '--no-session-persistence']
    t0 = time.time()
    p = subprocess.run(cmd, input=line + '\n', capture_output=True, text=True, env=env, cwd=WORK, timeout=1200)
    res, models = None, set()
    for l in p.stdout.splitlines():
        try:
            o = json.loads(l)
        except Exception:
            continue
        if o.get('type') == 'assistant':
            models.add(o.get('message', {}).get('model'))
        if o.get('type') == 'result':
            res = o
    text = (res or {}).get('result') or ''
    rec = {'time': time.strftime('%FT%TZ', time.gmtime()), 'tag': tag, 'n_sent': len(items), 'sent_ids': [s['id'] for s in items],
           'wall_s': round(time.time() - t0, 1), 'returncode': p.returncode, 'models_seen': sorted(m for m in models if m),
           'total_cost_usd': (res or {}).get('total_cost_usd'), 'usage': (res or {}).get('usage'),
           'modelUsage': (res or {}).get('modelUsage'), 'is_error': (res or {}).get('is_error'),
           'num_turns': (res or {}).get('num_turns'), 'raw_output': text, 'stderr': p.stderr[-500:]}
    low = (text + p.stderr + (p.stdout[-2000:] if res is None else '')).lower()
    limited = ('hit your' in low and 'limit' in low) or 'usage limit' in low or 'rate_limit' in low and res is None
    good, bad = ([], []) if limited else parse_lines(text)
    sent = {s['id'] for s in items}
    by = {}
    for g in good:
        if g['id'] in sent and g['id'] not in by:
            by[g['id']] = g
    rec['returned_ok_ids'] = sorted(by); rec['parse_errors'] = bad; rec['limited'] = bool(limited)
    with open(CALLS, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    if limited:
        raise Limit(text[:300] or p.stderr[-300:])
    if res is None or rec['is_error']:
        print('  call error:', p.returncode, text[:200], p.stderr[-200:], flush=True)
    return by, rec


def annotate(items, out, tag, bs):
    """標一組商品（一批）；缺的用 <=5 張小批重送，最多 2 輪。"""
    by, rec = call(items, tag)
    results = {i: (by[i], rec['time'], len(items)) for i in by}
    for rnd in (1, 2):
        missing = [s for s in items if s['id'] not in results]
        if not missing:
            break
        print(f'  resend round {rnd}: {len(missing)} items', flush=True)
        for k in range(0, len(missing), 5):
            sub = missing[k:k + 5]
            by, rec = call(sub, f'{tag}-resend{rnd}')
            for i in by:
                results[i] = (by[i], rec['time'], len(sub))
    with open(out, 'a', encoding='utf-8') as f:
        for s in items:
            r = results.get(s['id'])
            f.write(json.dumps({'id': s['id'], 'model': MODEL, 'ok': r is not None, 'ann': r[0] if r else None,
                                'call_time': r[1] if r else None, 'batch_size': r[2] if r else None, 'tag': tag}, ensure_ascii=False) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batches', default=''); ap.add_argument('--recheck', type=int, default=0)
    ap.add_argument('--batch-size', type=int, default=20)
    a = ap.parse_args()
    sample = [json.loads(l) for l in open(HERE / 'sample.jsonl')]
    try:
        if a.recheck:
            out = HERE / f'ann_claude_recheck{a.batch_size}.jsonl'
            first = [s for s in sample if s['batch'] <= 5]
            pick = sorted(random.Random('0-recheck').sample(first, a.recheck), key=lambda s: s['id'])
            random.Random('0-recheck-order').shuffle(pick)
            done = {json.loads(l)['id'] for l in open(out)} if out.exists() else set()
            groups = [pick[k:k + a.batch_size] for k in range(0, len(pick), a.batch_size)]
            for gi, g in enumerate(groups):
                if all(s['id'] in done for s in g):
                    continue
                print(f'recheck group {gi + 1}/{len(groups)}', flush=True)
                annotate(g, out, f'recheck{a.batch_size}', a.batch_size)
        else:
            out = HERE / 'ann_claude.jsonl'
            lo, hi = (int(x) for x in a.batches.split('-'))
            done = {json.loads(l)['id'] for l in open(out)} if out.exists() else set()
            for b in range(lo, hi + 1):
                items = [s for s in sample if s['batch'] == b and s['id'] not in done]
                if not items:
                    continue
                if a.batch_size != 20:
                    groups = [items[k:k + a.batch_size] for k in range(0, len(items), a.batch_size)]
                else:
                    groups = [items]
                for g in groups:
                    print(f'batch {b}: {len(g)} items', flush=True)
                    annotate(g, out, f'main{a.batch_size}', a.batch_size)
    except Limit as e:
        print('USAGE LIMIT:', e, flush=True); sys.exit(75)
    print('finished', flush=True)


if __name__ == '__main__':
    main()
