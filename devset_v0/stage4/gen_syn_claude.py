"""合成 query（syn_en）改用 Claude Sonnet 5.5 產生（主控 Opus 於 2026-11-18 決定，見 DECISIONS）。
沿用 gen_syn.py 的 make_prompt() 規則與 texts4.check_syn() 自動檢查；不給圖。每次呼叫一批題目，輸出 JSON lines {qid, sentence}。
未通過檢查的題目在下一輪重送（最多 5 輪），仍不過就用 tmpl_en 模板句（syn_source = tmpl_en_fallback）。
輸出格式與 gen_syn.py 相同（query_texts.json），另加 rewriter 欄位。"""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.dont_write_bytecode = True
U = Path(__file__).resolve().parent
sys.path.insert(0, str(U))
from texts4 import *  # noqa
from gen_syn import make_prompt  # noqa

MODEL = 'claude-sonnet-5-5'
SYS = ('You rewrite plain shopping templates into realistic shopper requests. For each item you get an id and a full instruction block. '
       'Follow each block\'s rules exactly. Output exactly one JSON object per line: {"qid": "<id>", "sentence": "<sentence>"}. '
       'No other text, no Markdown.')


def call(batch, rnd):
    body = '\n\n'.join(f'### id: {q["qid"]}\n{make_prompt(q)}' for q in batch)
    cmd = ['claude', '-p', '--model', MODEL, '--system-prompt', SYS, '--tools', '', '--strict-mcp-config', '--setting-sources', '',
           '--output-format', 'json', '--no-session-persistence']
    r = subprocess.run(cmd, input=body + '\n\nOutput the JSON lines now.', capture_output=True, text=True, timeout=900)
    try:
        res = json.loads(r.stdout)
    except Exception:
        return {}, {'round': rnd, 'error': (r.stdout + r.stderr)[-500:]}
    out = {}
    for line in (res.get('result') or '').splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            o = json.loads(line); out[o['qid']] = str(o['sentence'])
        except Exception:
            pass
    return out, {'round': rnd, 'n': len(batch), 'got': len(out), 'cost_usd': res.get('total_cost_usd')}


def norm(t):
    return t.strip().split('\n')[0].strip().strip('"\'“”‘’ ').strip()


def main():
    qs = {q['qid']: q for q in json.load(open(U / 'questions4.json'))}
    path = U / 'query_texts.json'
    out = json.load(open(path)) if path.exists() else {}
    attempts = {k: [] for k in qs}; calls = []
    todo = [k for k in qs if not (k in out and out[k].get('syn_en'))]
    for rnd in range(1, 6):
        if not todo:
            break
        batches = [[qs[k] for k in todo[i:i + 40]] for i in range(0, len(todo), 40)]
        with ThreadPoolExecutor(6) as ex:
            results = list(ex.map(lambda b: call(b, rnd), batches))
        ok_ids = set()
        for got, meta in results:
            calls.append(meta)
            for qid, s in got.items():
                if qid not in qs:
                    continue
                t = norm(s); ok, why = check_syn(qs[qid], t)
                attempts[qid].append({'attempt': rnd, 'text': t, 'ok': ok, 'fail_reasons': why})
                if ok and qid not in ok_ids:
                    ok_ids.add(qid); q = qs[qid]
                    out[qid] = {'scenario': q['scenario'], 'tmpl_zh': task_text(q, 'tmpl_zh', 40), 'tmpl_en': task_text(q, 'tmpl_en', 40),
                                'template_sentence_en': req_parts(q)[2], 'syn_en': t, 'syn_source': 'llm', 'rewriter': MODEL,
                                'prompt': make_prompt(q), 'attempts': attempts[qid]}
        todo = [k for k in todo if k not in ok_ids]
        print('round', rnd, 'ok', len(ok_ids), 'left', len(todo), flush=True)
    for k in todo:
        q = qs[k]
        out[k] = {'scenario': q['scenario'], 'tmpl_zh': task_text(q, 'tmpl_zh', 40), 'tmpl_en': task_text(q, 'tmpl_en', 40),
                  'template_sentence_en': req_parts(q)[2], 'syn_en': req_parts(q)[2], 'syn_source': 'tmpl_en_fallback', 'rewriter': MODEL,
                  'prompt': make_prompt(q), 'attempts': attempts[k]}
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (U / 'syn_claude_calls.jsonl').write_text(''.join(json.dumps(c) + '\n' for c in calls))
    print('DONE; fallback', len(todo), 'cost', sum((c.get('cost_usd') or 0) for c in calls), flush=True)


if __name__ == '__main__':
    main()
