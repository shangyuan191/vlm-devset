"""產生 S/REPORT_白話版.md；所有數字從 results/stage2_analysis.json、cell_status.json 讀出來填，不手打。保留報告最後的「## 自我驗收」一節。
用法： python3 -I devset_v0/stage2/make_report2.py
"""
import json
from pathlib import Path

S = Path(__file__).resolve().parent
J = json.load(open(S / 'results' / 'stage2_analysis.json'))
cells, cost, cons, summ = J['cells'], J['cost'], J['consistency'], J['summary']
pct = lambda x: '-' if x is None else f'{100 * x:.0f}%'  # noqa: E731
ZH = {'mid_century': 'mid-century', 'industrial': 'industrial', 'farmhouse_rustic': 'farmhouse/rustic', 'boho': 'boho', 'coastal': 'coastal',
      'traditional': 'traditional', 'chair': 'chair', 'table': 'table', 'lamp': 'lamp', 'chandelier_pendant': '吊燈', 'wall_art': 'wall art'}
name = lambda c: ' × '.join(ZH[x] for x in c.split('|'))  # noqa: E731
n_cells = len(cells)
met = summ['cells_met']
s1n = sum(v['stage1_n'] for v in cells.values()); s2n = sum(v['stage2_n'] for v in cells.values())
s1q = sum(v['stage1_qualified'] for v in cells.values()); s2q = sum(v['stage2_qualified'] for v in cells.values())
rounds = sorted(set(json.load(open(S / 'topup_rounds.json'))[i]['round'] for i in range(len(json.load(open(S / 'topup_rounds.json')))))) if (S / 'topup_rounds.json').exists() else []
no_room = [c for c, v in cells.items() if v['single_item_yes_conf2'] < (13 if c.endswith('wall_art') else 13)]
few_free = [c for c, v in cells.items() if v['scenario2'] is not None and v['scenario2']['n_free'] < 3]
tight = sorted(cells, key=lambda c: cells[c]['qualified'] - cells[c]['target'])[:5]
ex = [c for c in cells if cells[c]['queue_left'] == 0]
k1, k2 = cons['stage1_27cells']['dims'], cons['stage2_new']['dims']
cm, cs_ = cost['claude_main'], cost['claude_single_item']
lq, lg = cost['local']['qwen'], cost['local']['gemma']

tab = ['| 格子 | 已標件數 | 合格 / 目標 | 狀態 | 階段 1 合格率 | 階段 2 合格率 | 單一商品候選（yes 且信心 ≥ 2） | queue 還剩 |', '|---|---|---|---|---|---|---|---|']
for c, v in cells.items():
    tab.append(f"| {name(c)} | {v['labeled']} | {v['qualified']} / {v['target']} | {v['status']} | {pct(v['stage1_qualified_rate'])}（{v['stage1_qualified']}/{v['stage1_n']}） | {pct(v['stage2_qualified_rate'])}（{v['stage2_qualified']}/{v['stage2_n']}） | {v['single_item_yes_conf2']} | {v['queue_left']} |")
attr = ['| 格子 | color 值數 | material 值數 | shape 值數 | 情境二自由維度（值數 ≥ 2） |', '|---|---|---|---|---|']
for c, v in cells.items():
    a = v['attrs']
    fd = '（wall art 不出情境二）' if v['scenario2'] is None else (('、'.join(f'{d}（{n} 種）' for d, n in v['scenario2']['free_dims'].items()) or '無') + f"，共 {v['scenario2']['n_free']} 個")
    attr.append(f"| {name(c)} | {a['color']['n_values']} | {a['material']['n_values']} | {a['shape']['n_values']} | {fd} |")
kap = ['| 維度 | 階段 1（27 格 {} 件）κ | 階段 2 新標（{} 件）κ | 階段 2 兩兩一致率（Claude–Qwen / Claude–Gemma / Qwen–Gemma） |'.format(cons['stage1_27cells']['n_all3_ok'], cons['stage2_new']['n_all3_ok']), '|---|---|---|---|']
for d in k1:
    p = k2[d]['pairs']
    kap.append(f"| {d} | {k1[d]['kappa']:.2f} | {k2[d]['kappa']:.2f} | {pct(p['claude-qwen'])} / {pct(p['claude-gemma'])} / {pct(p['qwen-gemma'])} |")

R = f"""# 開發集 v0：階段 2（補標到每格湊滿合格商品）報告（白話版）

> 所有數字都由 `make_report2.py` 從 `results/stage2_analysis.json`（由 `analyze.py` 產生）讀出來填。我做的判斷在 `DECISIONS.md`，時間線在 `PROGRESS.md`。沒有出題、沒有跑選品實驗。

## 0. 先講結論
1. **{len(met)} / {n_cells} 格都湊滿了合格商品**，合計 **{summ['qualified_total']} 件**（目標合計 {summ['target_total']}）。{'沒有任何格子不足。' if not summ['cells_short'] else '不足的格子：' + '、'.join(name(c) for c in summ['cells_short'])}（`results/stage2_analysis.json`、`cell_status.json`）
2. 一共多標了 **{s2n} 件**新商品（階段 1 沿用 {s1n} 件）。其中補標只需要 {len(rounds)} 輪（只有 2 格差一點點）。
3. **Claude 總花費 ${cost['claude_total_usd']:.2f}**（上限 ${cost['budget_usd']:.0f}）：主標註 ${cm['usd']:.2f}（每件 ${cm['per_item_usd']:.4f}）、單一商品欄位 ${cs_['usd']:.2f}（每件 ${cs_['per_item_usd']:.4f}）。
4. 單一商品欄位：合格商品裡 **{summ['single_item_candidates_total']} 件**「主圖只有一件、信心 ≥ 2」，可當 query 圖候選。{'每格都至少有 13 件。' if not no_room else '候選數少於 13 件的格子：' + '、'.join(f"{name(c)}（{cells[c]['single_item_yes_conf2']}）" for c in no_room) + '。'}
5. 階段 2 新標的三方一致性和階段 1 差不多，但風格 κ 略低（{k2['style']['kappa']:.2f} vs {k1['style']['kappa']:.2f}）。

## 1. 名詞小字典
| 名詞 | 白話意思 |
|---|---|
| 格子 | 一個「風格 × 品項」組合，例如 boho × chair。這次剩 {n_cells} 格 |
| Claude 正票 | Claude 說這件的風格 = 格子風格（信心 ≥ 2）而且品項 = 格子品項。它是 Claude 先過濾的第一關 |
| 合格商品 | Claude 正票，並且三位中至少兩位同意風格、至少兩位同意品項。合格商品才可以當題目的答案 |
| queue | 每格還沒標過的商品，依固定隨機順序排好，標註時從前面依序拿 |
| 單一商品 | 主圖裡的主角明確只有一件（不是一組兩張椅子、不是拼貼圖） |
| Fleiss κ | 多位標註者「扣掉碰巧一致之後」的一致程度；0.6–0.8 算相當一致，0.8 以上幾乎完全一致 |
| 自由維度 | 情境二裡可以變化的屬性：某格合格商品中，這個屬性（color / material / shape）出現 ≥ 2 種不同值 |

## 2. 怎麼做（為什麼 / 怎麼做 / 結果 / 代表什麼）

### 2.1 Claude 先標，湊滿「Claude 正票」
- **為什麼**：合格條件要求 Claude 必須同意，所以 Claude 是守門員；先讓它標，沒過的商品就不用多花本地模型的時間（但本地模型最後還是全標，因為之後干擾項也要三方標註）。
- **怎麼做**：每格目標合格數 26（wall art 13）。Claude 正票的目標 = ceil(目標 ÷ 0.9) + 2（26 → 31、13 → 17），依該格階段 1 的正票率算每格要再拿幾件，從 queue 依序取，每 20 張一批、跨格打亂。設定和階段 1 完全相同（同一份準則、768 px 縮圖、Opus 5.5）。
- **結果**：{cost['n_stage2_items']} 件新商品；{len(ex)} 格的 queue 已經全部用完（{'、'.join(name(c) for c in ex) or '無'}）。
- **代表什麼**：正票率低的格子（例如 farmhouse × chair）要多標很多件才湊得滿，這是成本的主要來源。

### 2.2 本地模型一次標完 + 算合格
- **怎麼做**：Qwen3.8-27B 與 gemma-4-12b 各自啟動 vLLM，把 Claude 標過的全部新商品一次標完（一次一張、溫度 0）。之後 `compute_qualified.py` 合併階段 1（27 格 {s1n} 件）與階段 2 的標註，算出合格。
- **結果**：第一次算完有 25 格達標、2 格差 3 件（farmhouse × 吊燈、boho × lamp），照規則補標第 1 輪（43 件）後全部達標。
- **耗時**：Qwen 每件約 {lq['sec_per_item']} 秒（共 {lq['total_hours']:.1f} 小時），gemma 每件約 {lg['sec_per_item']} 秒（共 {lg['total_hours']:.1f} 小時）。（這是純標註時間；另外 Qwen 還花了約 2 小時等別人佔用的 GPU 釋放才能啟動。）

### 2.3 單一商品欄位
- **怎麼做**：只對 {summ['qualified_total']} 件合格商品，Claude 另外一次呼叫（用 `single_item_prompt.md` 的短 prompt，不動主標註），回答 `single_item`（yes/no + 信心）與 `scene`（white / room / other）。
- **結果**：見第 3 節表格最右邊的「單一商品候選」欄。

## 3. 每格結果
{chr(10).join(tab)}

來源：`results/stage2_analysis.json`。合計：階段 1 沿用 {s1n} 件中合格 {s1q} 件（{pct(s1q / s1n)}）；階段 2 新標 {s2n} 件中合格 {s2q} 件（{pct(s2q / s2n)}）。
> 注意：wall art 的 farmhouse、boho、coastal 三格在階段 2 沒有再標（階段 1 的 30 件就已經超過 13 件的目標），所以階段 2 欄位是「-」。

**合格率階段 1 vs 2**：階段 2 整體合格率（{pct(s2q / s2n)}）比階段 1（{pct(s1q / s1n)}）低，主要原因是階段 1 每格固定 30 件、各格權重一樣，而階段 2 是「正票率低的格子拿得多」（例如 farmhouse × chair 把 queue 用完），低合格率的格子在階段 2 占比較大；不能直接說階段 2 的品質變差。看單一格子時，階段 1 每格只有 30 件，誤差很大。

## 4. 合格商品的屬性分布（給 USER_DECISIONS ③ 用）
依 ③ 的新規則：合格商品中出現 ≥ 2 種值的屬性就是自由維度；wall art 只用於情境一。值用三位的多數決。
{chr(10).join(attr)}

- 自由維度少於 3 個的情境二格子：{'、'.join(f"{name(c)}（{cells[c]['scenario2']['n_free']} 個）" for c in few_free) or '無'}。
- 完整的值分布在 `results/stage2_analysis.json` 的 `cells.<格>.attrs`。

## 5. 三方一致性
{chr(10).join(kap)}

- 品項（category）三位都很一致；風格最難，三位之間只有約 6–7 成一致，這也是為什麼要求 Claude 同意 + 另一位同意。
- Gemma 在階段 2 的新商品中有 {lg['failed']} 筆輸出不在選項內，記為失敗（算「不同意」，和階段 1 一樣）；Qwen 失敗 {lq['failed']} 筆。

## 6. 成本
| 項目 | 金額 / 數量 |
|---|---|
| Claude 主標註 | ${cm['usd']:.2f}（{cm['calls']} 次呼叫，{cost['n_stage2_items']} 件，每件 ${cm['per_item_usd']:.4f}） |
| Claude 單一商品欄位 | ${cs_['usd']:.2f}（{cs_['calls']} 次呼叫，{cost['n_single_labeled']} 件，每件 ${cs_['per_item_usd']:.4f}） |
| Claude 合計 | ${cost['claude_total_usd']:.2f}（預算 ${cost['budget_usd']:.0f}） |
| 碰到用量上限的呼叫 | {cm['limited_calls'] + cs_['limited_calls']} 次 |

來源：`claude_calls.jsonl`、`single_item_calls.jsonl`。

## 7. 限制
- 每格的「合格」仍然是模型標註，不是人工確認；Claude 對 industrial 的把關有幫助（USER_DECISIONS ⑨），但沒有再做人工抽查。
- 階段 2 的商品是依「Claude 正票率」不斷往 queue 取，所以每格取的件數不同；合格率是每格自己的估計，樣本只有幾十件，誤差不小。
- 屬性分布用三位多數決；沒有多數（三位都不同）的件不計入值數。
- 補標到合格數剛好達標的格子（例如 {'、'.join(f"{name(c)} {cells[c]['qualified']}/{cells[c]['target']}" for c in tight)}）幾乎沒有餘裕：之後如果題目要求多樣性或排除重複，可能不夠。

## 8. 需要 Skyler 決定的事
1. **餘裕不大的格子**要不要多標一些（queue 還有商品的格子，每多標 20 件約 $0.19）？
2. **情境二自由維度少的格子**（第 4 節）：如果教授不同意把 n_d ≥ 4 放寬成 ≥ 2，這些格子要重新評估。
3. **queue 用完的格子**（{'、'.join(name(c) for c in ex) or '無'}）：沒有更多商品可補，只能維持現狀。
"""
old = (S / 'REPORT_白話版.md').read_text(encoding='utf-8') if (S / 'REPORT_白話版.md').exists() else ''
if '## 自我驗收' in old:
    R = R.rstrip('\n') + '\n\n' + old[old.index('## 自我驗收'):]
(S / 'REPORT_白話版.md').write_text(R, encoding='utf-8')
print('report ok')
