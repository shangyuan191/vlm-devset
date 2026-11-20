"""合成 query（syn_en）：本地 Qwen3.8-27B（-devset4，temperature 0.7，每題每次嘗試固定 seed），不給圖。
用法： python3 -I gen_syn.py --model qwen38-27b-devset4 --url http://127.0.0.1:8101/v1/chat/completions
輸出 query_texts.json（qid → {tmpl_zh, tmpl_en, syn_en, syn_source, prompt, attempts[]}）；可續跑。"""
import argparse, json, sys, time, urllib.request, zlib
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from texts4 import *   # noqa

U = Path(__file__).resolve().parent
EXAMPLES = ['wood bed rails for queen bed with hooks', 'tall folding stool', 'adjustable wall mount shop light', 'grey back pillow',
            'small led battery clock', '11x14 fancy picture frame', 'alexa clock wall', 'camera poster']


def rule_for(q):
    sc, c = q['scenario'], ck(q)
    if sc == 'S1':
        return 'Do not name any specific type of furniture (no "chair", "lamp", "table", etc.); the shopper is open to any kind of item that matches the look.'
    if sc == 'S2':
        return f'Mention the item type ({CAT_EN_SHORT[c]}).'
    if sc == 'T4':
        return (f'Say clearly that the shopper does NOT want {CAT_EN_SHORT[c]} (use a word such as "not", "no", "except", "other than" or "anything but"), '
                'and do not name any other specific furniture type.')
    return f'Mention the item type ({CAT_EN_SHORT[c]}) and that it should be {VAL_EN[q["value"]]} ({DIM_EN[q["attr"]]}).'


def make_prompt(q):
    tmpl = req_parts(q)[2]
    ex = '\n'.join(f'- {e}' for e in EXAMPLES)
    return ('You help write realistic shopping-site search requests. A shopper has uploaded a photo of a furniture or home-decor product and types a short request '
            'next to the photo. Below is a plain template describing what the shopper wants. Rewrite it as ONE sentence a real person would type '
            '(casual wording is fine; it can be a short phrase or a short conversational sentence).\n\n'
            f'Real example searches from a shopping site (for tone only; do not copy them):\n{ex}\n\n'
            'Rules:\n- Refer to the uploaded photo (for example "this", "like the one in the picture", "like this").\n'
            '- Do not name any decor style or era (no mid-century, rustic, farmhouse, boho, industrial, coastal, modern, vintage, traditional, etc.).\n'
            f'- {rule_for(q)}\n- Use 4 to 30 words.\n- Output only the sentence, with no quotation marks and no explanation.\n\n'
            f'Template: {tmpl}\nSentence:')


def call(url, model, prompt, seed):
    payload = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 120, 'temperature': 0.7, 'seed': seed,
               'chat_template_kwargs': {'enable_thinking': False}}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())['choices'][0]['message'].get('content') or ''


def norm(t):
    t = t.strip().split('\n')[0].strip()
    return t.strip('"\'“”‘’ ').strip()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--url', required=True)
    a = ap.parse_args()
    qs = json.load(open(U / 'questions4.json'))
    path = U / 'query_texts.json'; out = json.load(open(path)) if path.exists() else {}
    for i, q in enumerate(qs):
        if q['qid'] in out and out[q['qid']].get('syn_en'):
            continue
        prompt = make_prompt(q); attempts = []; syn = None
        for k in range(5):
            seed = zlib.crc32(f'stage4-syn|{q["qid"]}|{k}'.encode())
            for retry in range(3):
                try:
                    raw = call(a.url, a.model, prompt, seed); break
                except Exception as ex:
                    if 'refused' in str(ex).lower() or 'unreachable' in str(ex).lower():
                        raise SystemExit(f'server unreachable: {ex}')
                    time.sleep(3); raw = ''
            t = norm(raw); ok, why = check_syn(q, t)
            attempts.append({'attempt': k + 1, 'seed': seed, 'raw': raw, 'text': t, 'ok': ok, 'fail_reasons': why})
            if ok:
                syn = t; break
        src = 'llm'
        if syn is None:
            syn = req_parts(q)[2]; src = 'tmpl_en_fallback'
        out[q['qid']] = {'scenario': q['scenario'], 'tmpl_zh': task_text(q, 'tmpl_zh', 40), 'tmpl_en': task_text(q, 'tmpl_en', 40), 'template_sentence_en': req_parts(q)[2],
                         'syn_en': syn, 'syn_source': src, 'prompt': prompt, 'attempts': attempts}
        if i % 10 == 0:
            path.write_text(json.dumps(out, ensure_ascii=False, indent=1)); print(i, q['qid'], src, syn, flush=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print('DONE gen_syn; fallback:', sum(1 for v in out.values() if v['syn_source'] != 'llm'), flush=True)


if __name__ == '__main__':
    main()
