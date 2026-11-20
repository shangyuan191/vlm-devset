"""由 results/scores5.json 產生 REPORT_白話版.md（數字全部來自 JSON）。python3 -I make_report5.py"""
import json, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
V = Path(__file__).resolve().parent
o = json.load(open(V / 'results/scores5.json')); C = o['cells']; MODELS = o['meta']['models']; ANN = set(o['meta']['annotators'])
md = (V / 'results/scores5.md').read_text()
nm = lambda m: m + ('‡' if m in ANN else '')
CAPS = ['cap_g0', 'cap_g1', 'cap_g2', 'cap_g3', 'cap_g4', 'cap_g5', 'cap_g5_nostyle']
def done(m): return all(f'{m}|{c}|{sc}' in C and len(C[f'{m}|{c}|{sc}']['orders']) == 3 and all(v['n'] == v['n_expected'] for v in C[f'{m}|{c}|{sc}']['orders'].values()) for c in CAPS + ['img_goldstyle'] for sc in ('S1', 'S2'))
full = [m for m in MODELS if done(m)]; missing = [m for m in MODELS if m not in full]

def avg(c, sc, key='EffCov'):
    v = [C[f'{m}|{c}|{sc}'][key] for m in full if f'{m}|{c}|{sc}' in C]
    return sum(v) / len(v) if v else float('nan')
def sec(title):
    m = re.search(r'^## ' + re.escape(title) + r'.*?(?=^## |\Z)', md, re.S | re.M); return m.group(0).strip() if m else ''
def pd(m, sc, lab, key='EffCov'):
    p = o['paired'].get(f'{m}|{sc}|{lab}|{key}'); return p['mean'] if p else float('nan')
def pavg(sc, lab, key='EffCov'):
    v = [pd(m, sc, lab, key) for m in full]; return sum(v) / len(v) if v else float('nan')
L = ['# 階段 5 白話報告：給「正確 caption」後，模型到底有沒有用上？\n', f'（數字全部由 `make_report5.py` 從 `results/scores5.json` 產生。完成的模型：{", ".join(nm(m) for m in full) or "無"}；' + (f'**未完成：{", ".join(nm(m) for m in missing)}（等不到空閒 GPU，見「限制」），表中以 – 表示，平均只算完成的模型。**）' if missing else '全部 7 個模型完成。）'), '']
L += ['## 0. 先講結論\n',
      f'- 只告訴模型「風格」（沒有圖）就有很大幫助：EffCov@5 從 g0（什麼都沒給）到 g1（只給風格），S1 平均 {avg("cap_g0","S1"):.3f} → {avg("cap_g1","S1"):.3f}（配對差平均 {pavg("S1","g1−g0"):+.3f}），S2 {avg("cap_g0","S2"):.3f} → {avg("cap_g1","S2"):.3f}（{pavg("S2","g1−g0"):+.3f}）。',
      f'- 之後再加品項、材質、顏色、形狀：S1 的 g1→g2 平均 {pavg("S1","g2−g1"):+.3f}（變差；可能原因是多了品項資訊後模型傾向挑同品項而不夠多樣——這是推測，需對照 SameCat 才能確認）；g3→g4→g5 的平均差分別是 {pavg("S1","g3−g2"):+.3f}（g2→g3）、{pavg("S1","g4−g3"):+.3f}、{pavg("S1","g5−g4"):+.3f}，接近 0。S2 因為任務句本來就有品項，g1→g2 平均 {pavg("S2","g2−g1"):+.3f}，接近 0。',
      f'- 拿掉風格、只留品項＋材質＋顏色＋形狀（g5−style），比有風格的 g5 差很多：S1 平均 {pavg("S1","g5−g5_nostyle"):+.3f}、S2 {pavg("S2","g5−g5_nostyle"):+.3f}（g5 − g5_nostyle）。風格是最關鍵的那一條資訊。',
      f'- 「圖 + 正確風格」比「只給正確風格文字（g1）」： g1 − img 平均 S1 {pavg("S1","g1−img"):+.3f}、S2 {pavg("S2","g1−img"):+.3f}（正值 = 光給正確風格文字就贏過只看圖）。',
      '- 和 SigLIP2 文字檢索比（見階梯表）：看 VLM 的 g5 是否明顯高於 `siglip2txt-top5`。若差不多，表示 VLM 只是在做簡單的文字比對。',
      '- 風格寫錯的代價：見第 5 節「caption 寫錯的損失」。\n',
      '## 1. 名詞小字典\n',
      '- **gold caption（正確 caption）**：用參考圖的「正確屬性」寫成的文字描述（風格＝題目風格、品項＝題目品項、材質/顏色/形狀＝三方多數決），不是模型自己看圖寫的。',
      '- **階梯 g0…g5**：一階一階加維度（g0 無、g1 風格、g2 +品項、g3 +材質、g4 +顏色、g5 +形狀）；**g5−style** = 品項＋材質＋顏色＋形狀（不含風格）。這些條件**都沒有參考圖**。',
      '- **img**：只給參考圖（階段 3）；**img+self**：圖＋模型自己寫的風格（階段 3 的 style_given）；**img+gold**：圖＋正確風格（本階段）。',
      '- **Align@5**：選的 5 件中符合限制（同風格［、同品項］）的比例。**EffCov@5**：符合限制且「多樣」的綜合分數（headline）。**CopyQ@5**：選中的合格商品裡，顏色（材質）和參考圖相同的比例；高 = 傾向找「相似」而不是「多樣」。',
      '- **CI**：題目層級 bootstrap 95% 信賴區間；`*` = 不含 0（差異可信）。‡ = 該模型也是標註者。\n',
      '## 2. 為什麼做\n',
      'pilot（11-16）的 caption 是模型自己寫的，分數低時分不出是「寫錯」還是「寫對但沒用上」。這次改用正確 caption、而且不給圖，分數只反映「拿到正確描述後，能不能在 40 件候選中認出符合的商品」。另加「圖 + 正確風格」和階段 3 的「圖 + 自己寫的風格」比，量出風格寫錯的損失。\n',
      '## 3. 怎麼做\n',
      '- 216 題（S1、S2 各 108）原樣沿用階段 3（候選、順序、標題都不變）；7 個模型 × 8 條件 × 3 個候選順序。prompt 只改開頭與「參考圖片→參考商品」（完整範例見附錄 A）。',
      '- SigLIP2 文字基準線：把 gold caption 組成英文句（模板見 `siglip_text.py`），用 SigLIP2 文字編碼器對候選圖向量，選 top-5 或標準 MMR（λ=0.7）。',
      '- 計分同階段 3（import 自 `stage3/score.py`）。\n']
L += ['## 4. 結果：階梯表（3 個順序平均）\n', *[sec(t) + '\n' for t in ('階梯表：EffCov@5（S1）', '階梯表：EffCov@5（S2）', '階梯表：Align@5（S1）', '階梯表：Align@5（S2）')],
      '![S1](results/ladder_S1.svg)  ![S2](results/ladder_S2.svg)\n',
      '**代表什麼**：折線在 g0→g1 大幅上升，之後大致持平；g5−style 掉回接近 g0。SigLIP2 文字檢索的對照見表中 `siglip2txt-*` 列。\n',
      '### 每一階的配對差（EffCov@5；Align@5 見 `results/scores5.md`）\n', *[sec(t) + '\n' for t in ('每一階的配對差：EffCov@5（S1）', '每一階的配對差：EffCov@5（S2）')],
      '## 5. caption 寫錯的損失（img+gold − img+self）\n', *[sec(t) + '\n' for t in ('caption 寫錯的損失：img+gold − img+self（EffCov@5，S1）', 'caption 寫錯的損失：img+gold − img+self（EffCov@5，S2）')],
      '預期：「模型風格答對」那組差距接近 0（也檢查 prompt 有沒有寫錯）；「答錯」那組差距大。\n',
      '## 6. 找相似的傾向（CopyQ@5 顏色/材質，括號 = EffCov@5）\n', *[sec(t) + '\n' for t in ('找相似的傾向：CopyQ@5 顏色 / 材質（選中的合格商品中，和參考圖相同的比例）與 EffCov@5（S1）', '找相似的傾向：CopyQ@5 顏色 / 材質（選中的合格商品中，和參考圖相同的比例）與 EffCov@5（S2）')],
      '## 7. 和 pilot 階梯對照\n',
      'pilot（`overnight_2026-11-16/results/ladder_compare.md`）條件不同：模型自己寫的 caption＋有圖、只有燈具、K=3、20 題。它的結論：只加風格就大幅進步（+0.4～+0.9 盞），只加材質幾乎沒用，再加更多維度沒有再進步，拿掉風格就掉回原點。本階段（正確 caption、無圖、216 題、K=5）的 g0→g1 大幅進步、g2 以後持平、拿掉風格大幅下降，**方向一致**；差別是本階段證明這不是「caption 寫錯」造成的——即使 caption 全對，加了風格以外的維度也沒有進一步幫助。\n',
      '## 8. 限制\n',
      '- 階梯順序固定（風格→品項→材質→顏色→形狀），某一階的效果可能和加入順序有關。',
      '- S2 的任務句本來就有品項，所以 S2 的 g1→g2 預期接近 0。',
      '- gold caption 的材質、顏色、形狀是三方多數決，不是人工標註。',
      '- qwen38-27b、gemma4-12b 也是標註者（‡）。',
      '- qwen35-4b 實際使用的卡見 `DECISIONS.md` / `PROGRESS.md`（5090 的 GPU 3；4080 被他人佔用放不下）；不同 GPU 數值可能有極小差異。',
      '- GPU 2（3070，8GB）不使用（權重放不下）。',
      '- 本階段 GPU 長時間被他人佔用，部分模型等卡很久' + (f'；**{", ".join(nm(m) for m in missing)} 沒有完成**，結論只涵蓋已完成的模型。' if missing else '。'), '',
      '## 9. 需要 Skyler 決定的事\n',
      '- 「只給正確風格」就拿到大部分增益，之後的維度沒有再幫助——這是否要改變 benchmark 的任務設計（例如不再把品項／材質／顏色當成 caption 提示）？',
      ('- 未完成的模型要不要等有空卡時補跑（`job5.sh` 可續跑）？' if missing else ''), '',
      '## 附錄 A：8 個條件的 prompt 範例（item_0024-S1，完整文字，[IMAGE] = 一張圖）\n']
for c in ['cap_g0', 'cap_g1', 'cap_g2', 'cap_g3', 'cap_g4', 'cap_g5', 'cap_g5_nostyle', 'img_goldstyle']:
    t = (V / f'logs/prompt_example_{c}.txt').read_text().splitlines(); L += [f'### {c}\n', '```', *(t[:9] + ['…（候選 3–40 同格式）…'] + t[-2:]), '```\n']
L += ['## 附錄 B：全部指標\n', '見 `results/scores5.md`（完成題數、失敗率、Align@5、配對差等）。\n']
(V / 'REPORT_白話版.md').write_text('\n'.join(L) + '\n')
print('ok', full, missing)
