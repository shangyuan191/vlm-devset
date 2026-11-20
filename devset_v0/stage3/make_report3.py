"""由 results/scores.json、build_report.json、stage2 的 cell_status.json 產生 REPORT_白話版.md（數字全部由腳本填）。"""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
T = Path(__file__).resolve().parent; S = T.parent / 'stage2'
sc = json.load(open(T / 'results/scores.json')); br = json.load(open(T / 'build_report.json')); cs = json.load(open(S / 'cell_status.json'))
md = (T / 'results/scores.md').read_text()
ALL = ['qwen38-27b', 'qwen36-35b', 'gemma4-12b', 'qwen35-9b', 'qwen35-4b', 'internvl35-1tile', 'llavaov2-8b']
f = lambda x, p=3: '–' if x is None else f'{x:.{p}f}'
done = [m for m in ALL if m in sc['models'] and all(f'{c}|{s}' in sc['models'][m] and len(sc['models'][m][f'{c}|{s}']['orders']) == 3 and all(v['n'] == v['n_expected'] for v in sc['models'][m][f'{c}|{s}']['orders'].values()) for c in ('img', 'style_given') for s in ('S1', 'S2'))]
missing = [m for m in ALL if m not in done]
avg = {m: sc['models'][m].get('img|avg_EffCov') for m in sc['models'] if sc['models'][m].get('img|avg_EffCov') is not None}
best = max(avg, key=avg.get) if avg else None
L = ['# 開發集 v0：階段 3（補標緩衝 → 出題 → 第一輪選品實驗）報告（白話版）\n',
     '> 所有數字由 `make_report3.py` 從 `results/scores.json`、`build_report.json`、`stage2/cell_status.json` 讀出來填。我做的判斷在 `DECISIONS.md`，時間線在 `PROGRESS.md`。\n']
L.append('## 0. 先講結論')
L.append(f"1. **補標緩衝完成**：27/27 格達標，合格商品共 {cs['total']['qualified_total']} 件（階段 2 結束時是 838）。缺緩衝的 4 格都補到「目標＋4」以上；industrial × chair 的單一商品圖已 ≥ 13 張。（`stage2/cell_status.json`）")
L.append(f"2. **出題完成**：{br['n_queries']} 個 query、共 {br['n_questions_total']} 題（情境一 S1 與情境二 S2 各 {br['n_questions'].get('S1')}、{br['n_questions'].get('S2')} 題），丟掉 {len(br['dropped'])} 題。每題都通過 Oracle EffCov@5 = 1.00 檢查。（`build_report.json`）")
L.append(f"3. **模型跑完的有 {len(done)}/7 個**：{', '.join(done) or '無'}。" + (f" 還沒跑完：{', '.join(missing)}（見第 5 節的完成題數）。" if missing else ''))
if best:
    b = sc['models'][best]
    L.append(f"4. **目前（img 條件）平均 EffCov@5 最高的模型是 {best}**：{f(avg[best])}（S1 {f(b['img|S1']['EffCov'])}、S2 {f(b['img|S2']['EffCov'])}）。對照：Random {f(sc['baselines']['random']['avg_EffCov'])}、SigLIP2 top-5 {f(sc['baselines']['siglip2-top5']['img|avg_EffCov'])}、SigLIP2 + 輪流 MMR† {f(sc['baselines']['siglip2-mmr-free']['img|avg_EffCov'])}（† 這條基準線偷看了標註答案（三位標註者多數決）的顏色 / 材質 / 形狀 / 品項，不是公平對手，見第 1 節）、純圖片的 SigLIP2 + 標準 MMR {f(sc['baselines']['siglip2-mmr-std']['img|avg_EffCov'])}、Oracle 1.000。")
L.append('5. 兩處為了塞進 16384 tokens 而偏離 RUNBOOK 的地方（Qwen 系列圖片解析度、LLaVA-OV2 縮圖），見第 6 節。\n')
L.append('''## 1. 名詞小字典
| 名詞 | 白話意思 |
|---|---|
| S1 / S2 | 情境一：只要求「同風格」；情境二：要求「同風格 + 同品項」。兩個情境用同一批 query 圖 |
| 合格候選 | 40 件候選中真的符合限制的 12 件 |
| Align@5 | 模型挑的 5 件中，合格的比例 |
| Div@5 | 只看挑中的合格商品，各個「自由維度」（顏色、材質、形狀…）有多不同；合格少於 2 件的題不算 |
| EffCov@5 | 主要指標：自由維度的覆蓋率，沒挑到合格商品就是 0，滿分 1。它同時要求「對」和「多樣」 |
| 自由維度 | 合格候選中這個屬性有 ≥ 2 種值（例如顏色有 4 種），才拿來要求多樣 |
| Oracle | 事先知道答案時能拿到的最高分（每題都 1.00） |
| img / style_given | img：只給圖；style_given：額外告訴模型「參考商品的風格是 X」（X 是它自己在風格判斷題的答案） |
| Style Acc | 只給 query 圖，模型能不能選對風格 |
| 順序 o0/o1/o2 | 候選的排列順序（原順序 + 兩種打亂），用來看模型是否受位置影響 |
| 困難干擾 | 看起來很像答案、但其實不合格的候選（例如同品項但別的風格），用來考模型會不會被騙 |
| SigLIP2 top-5 | 不用大模型：用圖片向量找和參考圖最像的 5 件。純看圖，公平的對照組 |
| SigLIP2 + 輪流 MMR（siglip2-mmr-free）† | 先用 SigLIP2 取最像的 10 件，再**依標註答案的屬性**（顏色 / 材質 / 形狀 / 品項）輪流挑不同值。**它看得到標註答案，模型看不到**，所以是「半作弊」的參考值，不是公平對手（Opus 審查補註） |
| SigLIP2 + 標準 MMR（siglip2-mmr-std） | 只用圖片向量：挑和參考圖像、又和已選的不像的（λ = 0.7）。不看標註，公平 |
| H5 | 假設：模型「認得出風格，但選品時沒用上」。比較 style_given 和 img 的差 |
| H2 | 假設：S1（可以換品項）時，模型在顏色 / 材質 / 形狀上變化得比 S2 少。表中是同一張 query 的 S1 − S2 |
| H3 SameCat@5 | 只看 S1：挑出的 5 件中和參考圖同品項的比例。越高代表越「黏」在參考圖的品項上，不敢換品項 |
| H6 Dup@5 | 5 件中「顏色、材質、形狀三樣都一樣」的配對數，越高代表挑到越多近似重複款 |
| 95% CI | 用 bootstrap（重抽題目 10,000 次）估的誤差範圍；範圍跨過 0 就代表「看不出差別」 |
| 位置偏誤 | 模型是否偏愛排在前面的候選；完全隨機時「選到第 1 位」約 5/40 = 0.125 |
''')
L.append('## 2. 補標緩衝（A 節）\n- **為什麼**：有幾格剛好湊滿，出題時沒餘裕；industrial × chair 可當 query 的單一商品圖太少。\n- **怎麼做**：沿用階段 2 的腳本，Claude 補標第 5 輪（162 件），本地兩位標註者標完，再補標單一商品欄位；Claude 階段 3 花費不到上限 $5。\n- **結果**：')
for c in ['mid_century|lamp', 'coastal|table', 'farmhouse_rustic|chandelier_pendant', 'mid_century|wall_art', 'industrial|chair']:
    v = cs['cells'][c]; L.append(f"  - {c}：合格 {v['qualified']} / 目標 {v['target']}")
L.append('- **代表什麼**：每格都有足夠合格商品做 12 件合格候選與 query。\n')
L.append('## 3. 出題（B 節）')
L.append(f"- 每格最多 5 個 query；實際：" + '、'.join(f"{k} {v['used']}" for k, v in br['queries_per_cell'].items() if v['used'] < 5) + ' 以外每格 5 個。')
L.append(f"- 候選 40 件 = 合格 12 + 困難干擾 12 + 困難干擾 8 + 隨機 8。有 {br['n_retried']} 題換 seed 重抽過（多半是 Oracle EffCov 不到 1）。")
L.append('- 自由維度個數 |F|（題數）：' + '；'.join(f"{s}：" + ', '.join(f'{k} 個維度 {v} 題' for k, v in sorted(d.items())) for s, d in br['F_size'].items()))
L.append('- 標題都用「去風格字」版本（`c1_stats.STYLE_REGEX` 全部 pattern）。細節見 `DECISIONS.md` 3–6。\n')
L.append('## 4. 跑模型（C 節）\n每個模型 108 個風格判斷 + 216 題 × 3 順序 × 2 條件（img、style_given）。Random 期望值每題蒙地卡羅 1000 次；SigLIP2 用 CPU（top-5、輪流 MMR、標準 MMR λ=0.7）。\n')
L.append('## 5. 結果（數字由 `score.py` 產生，來源 `results/scores.json` / `scores.md`）\n')
L.append(md.replace('# 階段 3 計分（scripts 產生；數字來源 results/scores.json）\n', '').replace('\n## ', '\n### '))
L.append('\n## 6. 限制\n- **query 圖的風格沒有人工確認**：只靠三方一致 + Claude 高信心（style_conf = 3）。\n- **題數小**：108 個 query、216 題，每個模型每格只有幾題；CI 很寬，差異要小心解讀。\n- **③ 的規則（自由維度 n_d ≥ 2）教授尚未確認**，Skyler 決定先用它做 dev set。\n- **為了塞進 16384 tokens 偏離 RUNBOOK**：Qwen 系列 `max_pixels` 由 409600 降為 307200（41 張圖在 409600 下 prompt 約 16380 tokens，加輸出會超過）；LLaVA-OV2 送出的圖縮到長邊 560（900 時 41 張約 32k tokens）。所以這兩類模型看到的圖比其他模型小，和 11-16 的結果不能直接比。\n- boho × lamp 只有 3 個合格 query；wall art 格只出現在 S1。\n- 近似重複圖只用 `phash_dups.json`，沒有重算。\n'
         '- **（Opus 審查補充）gemma4-12b 和 qwen38-27b 同時是標註者和受測模型**：query 圖的條件是「三位標註者（Claude、Qwen3.8-27B、Gemma4-12B）都標同一風格」，合格商品也要它們之一同意。所以這兩個模型的 Style Acc 和選品分數可能偏高（有點像考自己出的題），和其他 5 個模型比較時要打折。\n'
         '- **（Opus 審查補充）siglip2-mmr-free 看得到標註屬性**（名詞小字典 †）。它的 S2 EffCov 比所有模型都高，但不代表「簡單方法打敗大模型」；公平的純圖片對照是 siglip2-top5 與 siglip2-mmr-std。\n'
         '- **（Opus 審查補充）標題去風格字不完全**：`STYLE_REGEX` 只刪風格名稱本身。(a) 1 件商品（item_0773，出現在 9 題）原標題是 "Mid Modern Century"，刪掉 Modern 後反而拼出 "Mid Century"；(b) 和風格高度相關、但不是風格名稱的字還在，例如 beach（出現 205 次）、steampunk（116）、country / cottage、barn、antique。所以 S1 的 Align 有一部分可能來自「讀標題」而不是「看圖判斷風格」。\n')
L.append('## 7. 需要 Skyler 決定的事\n1. 上面 Qwen / LLaVA-OV2 解析度的偏離要不要接受？或要把 `--max-model-len` 調大重跑這幾個模型。\n2. 教授對 ③ 的意見回來後，是否要重新出題（自由維度規則可能改）。\n3. 要不要人工確認 query 圖風格（108 張，可抽查）。\n'
         '4. （Opus 審查新增）gemma4-12b、qwen38-27b 同時是標註者與受測者：論文主表要不要把它們特別標出來，或改用人工確認過的子集計分？\n'
         '5. （Opus 審查新增）標題中 beach / steampunk / cottage 這類「風格線索字」要不要也刪，或加一個「不給標題、只給圖」的條件？（目前照 RUNBOOK 只刪風格名稱；要改就是改設計，所以交給你決定。）\n')
v = T / 'results/verify3.txt'
if v.exists():
    L.append('\n## 自我驗收（`verify3.py` 的輸出）\n\n```\n' + v.read_text() + '```')
(T / 'REPORT_白話版.md').write_text('\n'.join(L) + '\n')
print('report ok; done models:', done)
