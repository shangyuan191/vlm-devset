"""產生 REPORT_白話版.md。python3 -I make_report4.py（數字全由 results/scores4.json、build_report4.json、query_texts.json 產生，不手打）。"""
import collections, json, random, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
U = Path(__file__).resolve().parent
sc = json.load(open(U / 'results/scores4.json')); br = json.load(open(U / 'build_report4.json')); qt = json.load(open(U / 'query_texts.json')) if (U / 'query_texts.json').exists() else {}
QS = json.load(open(U / 'questions4.json')); QD = {q['qid']: q for q in QS}
MODELS = ['qwen38-27b', 'qwen36-35b', 'gemma4-12b', 'qwen35-9b', 'qwen35-4b', 'internvl35-1tile', 'llavaov2-8b']
LAB = {'qwen38-27b': 'qwen38-27b‡', 'gemma4-12b': 'gemma4-12b‡'}
lab = lambda m: LAB.get(m, m)
f = lambda x, p=3: '–' if x is None else f'{x:.{p}f}'
M = sc['models']; B = sc['baselines']
have = [m for m in MODELS if m in M]


def get(m, key, k):
    return M.get(m, {}).get(key, {}).get(k)


def rank(key, k, rev=True):
    v = [(get(m, key, k), m) for m in have if get(m, key, k) is not None]
    return sorted(v, reverse=rev)


def span(key, k, rev=True, p=3):
    r = rank(key, k, rev)
    return f"{lab(r[0][1])} {f(r[0][0], p)}（最{'高' if rev else '低'}）、{lab(r[-1][1])} {f(r[-1][0], p)}（最{'低' if rev else '高'}）" if r else '（資料不足）'


L = []
w = L.append
tmpl_done = [m for m in have if get(m, 'tmpl_zh|T4', 'EffCov') is not None]
w('# 開發集 v0：階段 4 報告（Negation、多重限制、合成 query）\n')
def complete(m):
    r = M.get(m, {})
    ok = all(r.get(f'tmpl_zh|{s}', {}).get('orders', {}).get(o, {}).get('n') == r.get(f'tmpl_zh|{s}', {}).get('orders', {}).get(o, {}).get('n_expected') and o in r.get(f'tmpl_zh|{s}', {}).get('orders', {}) for s in ('T3', 'T4') for o in ('o0', 'o1', 'o2'))
    n = sc['meta']['n_questions']
    ok = ok and all(r.get(f'wording|{s}', {}).get('by_wording', {}).get(wd, {}).get('n') == n[s] for s in ('S1', 'S2', 'T3', 'T4') for wd in ('tmpl_en', 'syn_en'))
    return ok
done = [m for m in MODELS if complete(m)]
w(f"> 本報告所有數字由腳本從 `results/scores4.json`、`build_report4.json`、`query_texts.json` 產生。已全部跑完的模型：{len(done)}/7（{', '.join(lab(m) for m in done) or '無'}）；有部分資料的：{', '.join(lab(m) for m in have if m not in done) or '無'}。\n")
w('## 先講結論\n')
t4 = B.get('siglip2-top5', {}).get('tmpl_zh|T4', {}); t3 = B.get('siglip2-top5', {}).get('tmpl_zh|T3', {})
w(f"1. **T4「同風格但不是這個品項」**：7 個模型的 Align@5（5 件裡真正符合的比例）{span('tmpl_zh|T4', 'Align')}；純圖片相似度（SigLIP2 top-5）只有 {f(t4.get('Align'))}，隨機 {f(B['random']['T4']['Align'])}。"
  f"純看「長得像」會被陷阱（同風格同品項、但題目說不要）騙：SigLIP2 的 Trap@5 = {f(t4.get('trap'))}（隨機 {f(sc['random_trap']['T4'])}）。模型的 Trap@5：{span('tmpl_zh|T4', 'trap', rev=False)}。")
w(f"2. **T3「同風格 + 同品項 + 指定顏色 / 材質」**：模型的 Align@5 {span('tmpl_zh|T3', 'Align')}；SigLIP2 top-5 {f(t3.get('Align'))}。"
  f"屬性陷阱（風格對、品項對、但顏色 / 材質不是指定值）被選中的比例 {span('tmpl_zh|T3', 'attr_trap', rev=False)}；SigLIP2 top-5 {f(t3.get('attr_trap'))}。")
eqs = [(get(m, 'tmpl_zh|T3|query_eq_v', 'Align'), get(m, 'tmpl_zh|T3|query_neq_v', 'Align')) for m in have]
eqs = [(a, b) for a, b in eqs if a is not None and b is not None]
if eqs:
    w(f"3. **query 圖本身的屬性等不等於指定值**會影響 T3：query 屬性 = 指定值（例如參考圖就是木頭、要求木頭）時，模型平均 Align@5 = {f(sum(a for a, b in eqs) / len(eqs))}；不等於（參考圖是金屬、卻要木頭）時 = {f(sum(b for a, b in eqs) / len(eqs))}。")
# 措辭
cnt = collections.Counter(); tot = 0; diffs = []
for m in have:
    for s in ('S1', 'S2', 'T3', 'T4'):
        p = M[m].get(f'wording|{s}', {}).get('paired', {}).get('EffCov|syn_en-tmpl_en')
        if p:
            tot += 1; diffs.append(p['mean'])
            cnt['sig_pos' if p['lo'] > 0 else 'sig_neg' if p['hi'] < 0 else 'ns'] += 1
if tot:
    w(f"4. **措辭（合成 query vs 英文模板句）**：{tot} 個「模型 × 題型」格子中，syn_en − tmpl_en 的 EffCov@5 差：顯著變好 {cnt['sig_pos']}、顯著變差 {cnt['sig_neg']}、看不出差別 {cnt['ns']}（95% CI 是否含 0）；平均差 {sum(diffs) / len(diffs):+.3f}。"
      "（syn_en 由 Claude Sonnet 5.5 改寫，不是受測模型，沒有「自己改寫自己作答」的問題。）")
w('5. **注意**：gemma4-12b‡、qwen38-27b‡ 同時是出題用的標註者；siglip2-mmr-free† 會讀候選的標註屬性，不是公平基準線（公平的純圖片對照是 siglip2-top5、siglip2-mmr-std）。\n')

w('## 名詞小字典\n')
for k, v in [('T3 多重限制', '同風格 + 同品項，再加一個屬性限制（顏色或材質等於某個值），例如「這個風格的椅子，要布面的」。'),
             ('T4 Negation', '同風格，但**不要**某個品項（query 圖的品項），例如「我已經有這張椅子，要同風格但不是椅子的東西」。'),
             ('S1 / S2', '階段 3 的兩種題：S1 只限風格；S2 限風格 + 同品項。本階段只補跑新的措辭，沿用階段 3 的題目。'),
             ('Align@5', '模型挑的 5 件中「真的符合所有限制」的比例。'), ('Div@5', '符合限制的那幾件，在「可以不同的維度」（顏色、材質、形狀、T4 還有品項）上有多分散；只算符合件數 ≥ 2 的題。'),
             ('EffCov@5', '主指標：同樣看分散度，但分母固定用 5 件，所以選到不符合的件會被扣分；1.00 = 滿分。'),
             ('Trap@5（陷阱）', 'T4：5 件中選到「同風格、同品項」（題目說不要的那種）的比例。T3 分兩種：屬性陷阱 = 風格 / 品項對、但顏色或材質不是指定值（或補位商品）；風格陷阱 = 品項 / 屬性對、但風格不對。越低越好；隨機的期望值就是該桶佔 40 件的比例。'),
             ('tmpl_zh / tmpl_en / syn_en', '三種 query 寫法：中文模板句、英文直譯模板句、由 Claude Sonnet 5.5 改寫成真人購物語氣的英文需求句（RUNBOOK 原訂本地 Qwen3.8-27B，因等不到 2 張 GPU 改用，見 DECISIONS）。'),
             ('SigLIP2 三種基準線', 'siglip2-top5 = 只挑和 query 圖最像的 5 件；siglip2-mmr-std = 標準 MMR（相似又不重複，只用圖片）；**siglip2-mmr-free† = 依標註屬性輪流挑，偷看了答案相關資訊，不是公平基準線**。'),
             ('‡ / †', '‡ = 該模型同時是出題標註者（分數可能偏高）；† = 非公平基準線。'),
             ('95% CI', '題目層級 bootstrap（重抽 10,000 次）的 95% 信賴區間；區間不含 0 才表示差距比較可信。'),
             ('o0 / o1 / o2', '候選順序：o0 = 原順序，o1、o2 = 兩種打亂；±是三種順序的標準差。')]:
    w(f'- **{k}**：{v}')
w('')
w('## 1. 出題結果（`build_questions4.py` → `questions4.json`、`build_report4.json`）\n')
nq = br['n_questions']
w(f"- 可用合格商品 {br['n_qualified_total']} 件（沿用階段 3「三方都標過」規則；`stage2/qualified.jsonl` 的 891 件中有 10 件缺一位標註者，排除）。")
w(f"- **T4 Negation：{nq.get('T4', 0)} 題**（用階段 3 的 108 個 query；全部 |自由維度| = {dict(br['F_size']['T4'])}，Oracle EffCov@5 = 1.00）。")
w(f"- **T3 多重限制：{nq.get('T3', 0)} 題**，來自 {br['n_combos']} 個可出題組合 / {br['n_cells_with_combo']} 個格子（規則：該格 a = v 件數 ≥ 12、排除比例 ≥ 30%、另兩個屬性各 ≥ 2 種值）；同一組合內 query 不重複，共 {br['n_t3_queries_unique']} 個不同 query。主控 11/17 用 891 件試算是 25 組合 / 17 格，我用 881 件實算是 {br['n_combos']} / {br['n_cells_with_combo']}。")
w(f"- T3 補位與放寬（記在 `build_report4.json` → `relaxed`）：{sum(1 for r in br['relaxed'] if 'notes' in r)} 題有補位 / 放寬（屬性陷阱不足改用「風格 X 其他品項、a = v」補；風格陷阱不足改為 a 任意）；被換掉的 query（該 query 自己在該組合建不出題）{len(br['dropped'])} 次。")
w(f"- 沿用階段 3 的 S1、S2 各 {sc['meta']['n_questions']['S1']}、{sc['meta']['n_questions']['S2']} 題；T3、T4 的標題去風格字改為**反覆刪到不再變**（修掉 \"Mid Modern Century\" 這類拼接）；S1 / S2 沿用原標題以保持可配對。\n")
w('### T3 可出題組合\n\n| 格子 | 屬性 | 值 | 該格符合件數 / 合格數 | 排除比例 | query 屬性 = 值的題數 |\n|---|---|---|---|---|---|')
for c in br['combos']:
    qq = [q for q in QS if q['scenario'] == 'T3' and q['cell'] == c['cell'] and q['attr'] == c['attr'] and q['value'] == c['value']]
    w(f"| {c['cell']} | {c['attr']} | {c['value']} | {c['n']} / {c['total']} | {c['excluded']:.2f} | {sum(1 for q in qq if q['query_attr_equals_v'])} / {len(qq)} |")
w('')
body = (U / 'results/scores4.md').read_text().split('\n## T4 Negation 主表', 1)
w('## 2. 結果（由 `score4.py` 產生；完整檔案 `results/scores4.md`）\n')
w('## T4 Negation 主表' + body[1] if len(body) > 1 else '（尚無資料）')
w('')
# 合成 query 品質
w('## 3. 合成 query（syn_en）品質\n')
if qt:
    srcs = collections.Counter(v['syn_source'] for v in qt.values()); att = collections.Counter(len(v['attempts']) for v in qt.values() if v['syn_source'] == 'llm')
    why = collections.Counter(r for v in qt.values() for a in v['attempts'] for r in a['fail_reasons'])
    w(f"- 共 {len(qt)} 題；LLM 通過自動檢查 {srcs['llm']} 題、用 tmpl_en 後備 {srcs['tmpl_en_fallback']} 題。通過者的嘗試次數分布：{dict(sorted(att.items()))}。")
    w(f"- 被檢查擋下的原因（所有嘗試合計）：{dict(why.most_common())}。")
    bys = collections.defaultdict(list)
    for q, v in qt.items():
        bys[v['scenario']].append(len(v['syn_en'].split()))
    w('- 平均字數：' + '、'.join(f"{s} {sum(x) / len(x):.1f}" for s, x in sorted(bys.items())) + '。')
    rng = random.Random(0); pick = sorted(rng.sample(sorted(qt), min(30, len(qt))))
    w('\n### 附錄：隨機抽 30 題的改寫（給 Skyler 看品質）\n\n| qid | 題型 | 模板句（改寫輸入） | syn_en | 來源 |\n|---|---|---|---|---|')
    for qid in pick:
        v = qt[qid]; w(f"| {qid} | {v['scenario']} | {v['template_sentence_en']} | {v['syn_en']} | {v['syn_source']} |")
w('')
w('## 4. 限制\n')
for x in ['query 圖的風格沒有人工確認（只靠三方一致 + Claude 高信心）；題數小（T3 64 題、T4 108 題），T3 每個組合只有 2–3 題，格子層級的差異不可信。',
          '③「n_d ≥ 2 即自由維度」教授尚未確認；許多 T3 題的自由維度只剩 2 種值（見 build_report4.json 的 n_d 分布），EffCov 的鑑別力有限。',
          'gemma4-12b‡、qwen38-27b‡ 同時是標註者與受測者。',
          'siglip2-mmr-free† 使用標註屬性（特權資訊），不是公平基準線；結論以 siglip2-top5、siglip2-mmr-std 為對照。',
          '解析度沿用階段 3 的偏離：Qwen 系列 max_pixels = 307200、LLaVA-OV2 圖縮到 560，其他 900（否則 41 張圖會超過 16384 tokens）。',
          '標題中的風格線索字（beach、steampunk、cottage、barn、antique…）依規則未刪；T3 / T4 的標題已改為反覆刪到不再變，但 S1 / S2 仍是階段 3 的單次刪除標題（為了可配對），其中 item_0773 "Mid Modern Century" 殘留 "Mid Century"。',
          'T3 的「顏色 / 材質」限制值以三位標註者多數決為準，標註本身有雜訊；T4、T3 的合格集合來自標註，不是人工確認。',
          'syn_en 由 Claude Sonnet 5.5 改寫（偏離 RUNBOOK 的本地 Qwen3.8-27B），不同於真人；改寫只看模板句、不看圖，措辭風格偏單一（見附錄 30 題）。tmpl_zh 的 S1 / S2 用階段 3 的結果（同 prompt、同題）。']:
    w(f'- {x}')
w('\n## 5. 需要 Skyler 決定的事\n')
for i, x in enumerate(['T3 可出題組合集中在少數屬性值（例如 wood、natural wood、metallic）；要不要擴大標註讓 T3 組合更多元（需要更多合格商品）。',
                       'T3 / T4 的「陷阱」是否就是你要的難度？SigLIP2 純相似度在 T4 的 Trap 很高，代表 T4 主要測「讀懂不要」；若想測更細的否定，可再加陷阱種類。',
                       '合成 query 目前只有 Claude 一種改寫者（原訂 Qwen3.8-27B 因等不到 GPU 改用）；要不要再加人工改寫一小批或本地模型改寫作對照。',
                       '標註者 = 受測者（gemma4-12b‡、qwen38-27b‡）的問題，長期是否換掉其中一位標註者、或用人工確認的子集另算（延續階段 3 審查建議）。',
                       '教授對 ③ 的意見回來後是否重新出題（延續階段 3）。'], 1):
    w(f'{i}. {x}')
w('\n## 6. 自我驗收\n\n第 7 項列出的 `stage3/OPUS_REVIEW.md` 是主控 Opus 在階段 4 開始前後寫的審查報告（01:48，非本階段 agent 所改）。\n')
vp = U / 'results/verify4.txt'
w('```\n' + (vp.read_text().strip() if vp.exists() else '（尚未執行 verify4.py）') + '\n```')
(U / 'REPORT_白話版.md').write_text('\n'.join(L) + '\n')
print('report written', len(L))
