"""階段 2 Claude 主標註：一輪一輪發商品 → 每 20 張一批送 Claude（沿用階段 1 的精簡呼叫）。可續跑。
用法： python3 -I annotate_claude2.py --mode main            # 3.2：重複到所有格子 Claude 正票達標或 queue 用完
       python3 -I annotate_claude2.py --mode topup            # 3.4：只對合格數不足的格子補一輪（需要 cell_status.json）
輸出： items.jsonl（發出的商品，id 從 item_0901 起，含 round）、img768/、ann_claude.jsonl、claude_calls.jsonl
預算：累計花費 + 0.30 > $40 就不再呼叫（exit 76）。碰到用量上限 exit 75（看守程式會等重置後讓 agent 重跑）。
"""
import argparse, base64, collections, json, math, os, random, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common2 import *  # noqa: F401,F403
from PIL import Image

MODEL = 'claude-opus-5-5'
WORK = S / 'claude_work'; WORK.mkdir(exist_ok=True)
(S / 'img768').mkdir(exist_ok=True)
CALLS = S / 'claude_calls.jsonl'
LONG = 768


class Limit(Exception):
    pass


class Budget(Exception):
    pass


def call(items, tag):
    if spent_usd() + CALL_MARGIN_USD > BUDGET_USD:
        raise Budget(f'spent {spent_usd():.2f}')
    content = []
    for s in items:
        b64 = base64.b64encode((S / s['ann_image']).read_bytes()).decode()
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
           'is_error': (res or {}).get('is_error'), 'num_turns': (res or {}).get('num_turns'), 'raw_output': text, 'stderr': p.stderr[-500:]}
    low = (text + p.stderr + (p.stdout[-2000:] if res is None else '')).lower()
    limited = ('hit your' in low and 'limit' in low) or 'usage limit' in low or ('rate_limit' in low and res is None)
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


def annotate(items, tag):
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
    with open(ANN2['claude'], 'a', encoding='utf-8') as f:
        for s in items:
            r = results.get(s['id'])
            f.write(json.dumps({'id': s['id'], 'model': MODEL, 'ok': r is not None, 'ann': r[0] if r else None,
                                'call_time': r[1] if r else None, 'batch_size': r[2] if r else None, 'tag': tag}, ensure_ascii=False) + '\n')


def thumb(src, dst):
    im = Image.open(R / src)
    if im.mode != 'RGB':
        bg = Image.new('RGB', im.size, 'white'); im = im.convert('RGBA'); bg.paste(im, mask=im.split()[3]); im = bg
    if max(im.size) > LONG:
        s = LONG / max(im.size); im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    im.save(dst, 'JPEG', quality=90)
    return list(im.size)


def cell_state():
    """每格：已標件數、Claude 正票、已發 queue 位置。"""
    c1 = load_ann(ANN1['claude']); c2 = load_ann(ANN2['claude'])
    st = {c: {'labeled': 0, 'pos': 0, 'issued': 0} for c in CELLS}
    for it in stage1_items():
        s = st[it['cell']]; s['labeled'] += 1; s['pos'] += claude_positive(it['cell'], c1.get(it['id']))
    for it in stage2_items():
        s = st[it['cell']]; s['issued'] += 1
        if it['id'] in c2:
            s['labeled'] += 1; s['pos'] += claude_positive(it['cell'], c2[it['id']])
    return st


def plan_main(st, qleft):
    """3.2 第 1–2 步：回傳 {cell: 取幾件}。"""
    take = {}
    for c in CELLS:
        need = claude_target0(c) - st[c]['pos']
        if need <= 0 or qleft[c] <= 0:
            continue
        rate = st[c]['pos'] / st[c]['labeled'] if st[c]['labeled'] else 0
        k = 40 if rate == 0 else max(20, math.ceil(need / rate))
        take[c] = min(k, qleft[c])
    return take


def plan_topup(qleft):
    """3.4：Claude 目標 = 還差的合格數 ÷ 該格實測確認率 + 2；至少 20 件的規則不適用，直接依正票率換算。"""
    cs = json.load(open(S / 'cell_status.json'))['cells']
    st = cell_state(); take = {}
    for c in CELLS:
        v = cs[c]
        deficit = v['target'] - v['qualified']
        if deficit <= 0 or qleft[c] <= 0:
            continue
        conf = v['confirm_rate'] if v.get('confirm_rate') else CONFIRM_RATE
        need_pos = math.ceil(deficit / max(conf, 0.3)) + 2
        rate = st[c]['pos'] / st[c]['labeled'] if st[c]['labeled'] else 0
        k = 40 if rate == 0 else max(10, math.ceil(need_pos / rate))
        take[c] = min(k, qleft[c])
    return take


def issue_round(take, rnd):
    """把這一輪的商品打亂、編 id、做縮圖、寫 items.jsonl。回傳這一輪的 items（依批次順序）。"""
    q = queue_by_cell()
    issued = {it['parent_asin'] for it in stage2_items()}
    pick = []
    for c, k in take.items():
        rows = [r for r in q[c] if r['parent_asin'] not in issued]
        pick += rows[:k]
    pick.sort(key=lambda r: (r['cell'], r['qpos']))
    random.Random(f'0-stage2-round{rnd}').shuffle(pick)
    nxt = 901 + len(stage2_items())
    new = []
    with open(S / 'items.jsonl', 'a', encoding='utf-8') as f:
        for k, p in enumerate(pick):
            iid = f'item_{nxt + k:04d}'
            wh = thumb(p['image_path'], S / 'img768' / f'{iid}.jpg')
            rec = {'id': iid, 'ann_image': f'img768/{iid}.jpg', 'ann_wh': wh, 'batch': None, 'round': rnd,
                   **{x: p[x] for x in ('parent_asin', 'cell', 'item', 'kw_style', 'title', 'store', 'source', 'categories', 'image_path', 'sha256')}}
            f.write(json.dumps(rec, ensure_ascii=False) + '\n'); new.append(rec)
    return new


def run_round(rnd):
    """標這一輪尚未標的商品（每 20 件一批，批次 = 該輪 id 連續 20 個）。"""
    done = set(load_ann(ANN2['claude']))
    items = [it for it in stage2_items() if it['round'] == rnd]
    for k in range(0, len(items), 20):
        g = items[k:k + 20]
        if all(s['id'] in done for s in g):
            continue
        g = [s for s in g if s['id'] not in done]
        print(f'round {rnd} batch {k // 20 + 1}/{math.ceil(len(items) / 20)}: {len(g)} items, spent ${spent_usd():.2f}', flush=True)
        annotate(g, f'main20-r{rnd}')
        checkpoint1()


def checkpoint1():
    flag = S / 'checkpoint1.json'
    if flag.exists():
        return
    calls = [r for r in read_jsonl(CALLS) if r.get('total_cost_usd') is not None and not r.get('limited') and r['tag'].startswith('main20')]
    n = len(load_ann(ANN2['claude']))
    if n < 200:
        return
    cost = sum(r['total_cost_usd'] for r in calls)
    per = cost / n
    est_items = 1300
    est_single = 0.5 * per * 700   # 單一商品欄位：約 700 件合格商品，每件成本以主標註的一半粗估（保守）
    proj = per * est_items + est_single
    json.dump({'n': n, 'cost': round(cost, 4), 'per_item': round(per, 5), 'projected_total_usd': round(proj, 2),
               'assumption': '主標註 1300 件 + 單一商品欄位 700 件 × 0.5 × 每件成本'}, open(flag, 'w'), indent=1)
    progress(f'階段2/Claude 檢查點 1 — 前 {n} 件共 ${cost:.2f}，每件 ${per:.4f}；推估總額 ${proj:.1f}（{"≤" if proj <= BUDGET_USD else ">"} $40）')
    if proj > BUDGET_USD:
        raise Budget('checkpoint1 projection > budget')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--mode', required=True, choices=['main', 'topup'])
    a = ap.parse_args()
    try:
        # 先把已發未標的輪補完（續跑）
        rounds = sorted({it['round'] for it in stage2_items()})
        for r in rounds:
            run_round(r)
        for _ in range(8):
            st = cell_state(); q = queue_by_cell()
            qleft = {c: len(q[c]) - st[c]['issued'] for c in CELLS}
            take = plan_main(st, qleft) if a.mode == 'main' else plan_topup(qleft)
            if a.mode == 'topup':
                tag_round = max(rounds + [0]) + 1
                if any(it['round'] >= 100 for it in stage2_items() if False):
                    pass
            if not take:
                print('no more cells to take', flush=True); break
            rnd = max([it['round'] for it in stage2_items()] + [0]) + 1
            progress(f'階段2/Claude 第 {rnd} 輪 — 發出 {sum(take.values())} 件（{len(take)} 格）')
            issue_round(take, rnd)
            run_round(rnd)
            if a.mode == 'topup':
                break
    except Limit as e:
        print('USAGE LIMIT:', e, flush=True); sys.exit(75)
    except Budget as e:
        progress(f'階段2/Claude 停止 — 預算或檢查點：{e}（累計 ${spent_usd():.2f}）')
        print('BUDGET STOP:', e, flush=True); sys.exit(76)
    print('finished', flush=True)


if __name__ == '__main__':
    main()
