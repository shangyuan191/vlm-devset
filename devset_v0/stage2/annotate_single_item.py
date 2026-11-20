"""3.5 單一商品欄位：只對合格商品（含階段 1）由 Claude 單獨呼叫一次（自訂短 system prompt = single_item_prompt.md），每批 20 張。
輸出 ann_single_item.jsonl（每件一行）、single_item_calls.jsonl（每次呼叫：cost、usage）。可續跑；缺漏的重送（每批 <= 5 張，最多 2 輪）。
用法： python3 -I annotate_single_item.py     （先跑 compute_qualified.py 產生 qualified.jsonl）
"""
import base64, json, os, re, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common2 import *  # noqa: F401,F403

MODEL = 'claude-opus-5-5'
PROMPT = (S / 'single_item_prompt.md').read_text(encoding='utf-8')
FINAL = 'Answer for every image above. Output JSON lines only.'
CALLS = S / 'single_item_calls.jsonl'; OUT = S / 'ann_single_item.jsonl'; WORK = S / 'claude_work'; WORK.mkdir(exist_ok=True)


class Limit(Exception):
    pass


class Budget(Exception):
    pass


def parse(text):
    good = []
    for m in re.finditer(r'\{[^{}]*"id"[^{}]*\}', text or ''):
        try:
            o = json.loads(m.group(0))
            r = {'id': str(o['id']).strip(), 'single_item': str(o['single_item']).strip().lower(), 'single_item_conf': int(o['single_item_conf']),
                 'scene': str(o['scene']).strip().lower()}
            if r['single_item'] in ('yes', 'no') and r['single_item_conf'] in (1, 2, 3) and r['scene'] in ('white', 'room', 'other'):
                good.append(r)
        except Exception:
            pass
    return good


def call(items, tag):
    if spent_usd() + CALL_MARGIN_USD > BUDGET_USD:
        raise Budget(f'spent {spent_usd():.2f}')
    content = []
    for s in items:
        b64 = base64.b64encode(s['path'].read_bytes()).decode()
        content += [{'type': 'text', 'text': f"item_id: {s['id']}"}, {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b64}}]
    content.append({'type': 'text', 'text': FINAL})
    line = json.dumps({'type': 'user', 'message': {'role': 'user', 'content': content}})
    env = {k: v for k, v in os.environ.items() if k.lower() not in ('all_proxy', 'https_proxy', 'http_proxy')}
    cmd = ['claude', '-p', '--model', MODEL, '--system-prompt', PROMPT, '--tools', '', '--strict-mcp-config', '--setting-sources', '',
           '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--no-session-persistence']
    t0 = time.time()
    p = subprocess.run(cmd, input=line + '\n', capture_output=True, text=True, env=env, cwd=WORK, timeout=1200)
    res = None
    for l in p.stdout.splitlines():
        try:
            o = json.loads(l)
        except Exception:
            continue
        if o.get('type') == 'result':
            res = o
    text = (res or {}).get('result') or ''
    low = (text + p.stderr + (p.stdout[-2000:] if res is None else '')).lower()
    limited = ('hit your' in low and 'limit' in low) or 'usage limit' in low or ('rate_limit' in low and res is None)
    good = [] if limited else parse(text)
    sent = {s['id'] for s in items}; by = {}
    for g in good:
        if g['id'] in sent and g['id'] not in by:
            by[g['id']] = g
    rec = {'time': time.strftime('%FT%TZ', time.gmtime()), 'tag': tag, 'n_sent': len(items), 'sent_ids': sorted(sent), 'wall_s': round(time.time() - t0, 1),
           'returncode': p.returncode, 'total_cost_usd': (res or {}).get('total_cost_usd'), 'usage': (res or {}).get('usage'),
           'is_error': (res or {}).get('is_error'), 'raw_output': text, 'returned_ok_ids': sorted(by), 'limited': bool(limited)}
    with open(CALLS, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    if limited:
        raise Limit(text[:300] or p.stderr[-300:])
    return by


def main():
    q = read_jsonl(S / 'qualified.jsonl')
    items = {it['id']: it for it in stage1_items() + stage2_items()}
    done = {r['id'] for r in read_jsonl(OUT)}
    todo = []
    for r in sorted(q, key=lambda r: r['id']):
        if r['id'] in done:
            continue
        it = items[r['id']]
        todo.append({'id': r['id'], 'path': (S1 if it['round'] == 0 else S) / it['ann_image']})
    print(len(q), 'qualified;', len(todo), 'to do', flush=True)
    try:
        for k in range(0, len(todo), 20):
            g = todo[k:k + 20]
            print(f'batch {k // 20 + 1}/{-(-len(todo) // 20)} spent ${spent_usd():.2f}', flush=True)
            res = {**call(g, 'single20')}
            for rnd in (1, 2):
                miss = [s for s in g if s['id'] not in res]
                for j in range(0, len(miss), 5):
                    res.update(call(miss[j:j + 5], f'single-resend{rnd}'))
            with open(OUT, 'a', encoding='utf-8') as f:
                for s in g:
                    r = res.get(s['id'])
                    f.write(json.dumps({'id': s['id'], 'ok': r is not None, **(r or {})}, ensure_ascii=False) + '\n')
    except Limit as e:
        print('USAGE LIMIT:', e); sys.exit(75)
    except Budget as e:
        progress(f'階段2/單一商品欄位 停止 — 預算：{e}'); print('BUDGET STOP', e); sys.exit(76)
    print('finished', flush=True)


if __name__ == '__main__':
    main()
