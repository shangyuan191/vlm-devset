# 開發集 v0：階段 2（補標到每格湊滿合格商品）報告（白話版）

> 所有數字都由 `make_report2.py` 從 `results/stage2_analysis.json`（由 `analyze.py` 產生）讀出來填。我做的判斷在 `DECISIONS.md`，時間線在 `PROGRESS.md`。沒有出題、沒有跑選品實驗。

## 0. 先講結論
1. **27 / 27 格都湊滿了合格商品**，合計 **891 件**（目標合計 637）。沒有任何格子不足。（`results/stage2_analysis.json`、`cell_status.json`）
2. 一共多標了 **1864 件**新商品（階段 1 沿用 810 件）。其中補標只需要 1 輪（只有 2 格差一點點）。
3. **Claude 總花費 $22.67**（上限 $40）：主標註 $17.27（每件 $0.0093）、單一商品欄位 $5.40（每件 $0.0061）。
4. 單一商品欄位：合格商品裡 **706 件**「主圖只有一件、信心 ≥ 2」，可當 query 圖候選。每格都至少有 13 件。
5. 階段 2 新標的三方一致性和階段 1 差不多，但風格 κ 略低（0.61 vs 0.67）。

## 1. 名詞小字典
| 名詞 | 白話意思 |
|---|---|
| 格子 | 一個「風格 × 品項」組合，例如 boho × chair。這次剩 27 格 |
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
- **結果**：1864 件新商品；3 格的 queue 已經全部用完（boho × lamp、coastal × chair、farmhouse/rustic × chair）。
- **代表什麼**：正票率低的格子（例如 farmhouse × chair）要多標很多件才湊得滿，這是成本的主要來源。

### 2.2 本地模型一次標完 + 算合格
- **怎麼做**：Qwen3.8-27B 與 gemma-4-12b 各自啟動 vLLM，把 Claude 標過的全部新商品一次標完（一次一張、溫度 0）。之後 `compute_qualified.py` 合併階段 1（27 格 810 件）與階段 2 的標註，算出合格。
- **結果**：第一次算完有 25 格達標、2 格差 3 件（farmhouse × 吊燈、boho × lamp），照規則補標第 1 輪（43 件）後全部達標。
- **耗時**：Qwen 每件約 8.67 秒（共 4.5 小時），gemma 每件約 3.77 秒（共 2.0 小時）。（這是純標註時間；另外 Qwen 還花了約 2 小時等別人佔用的 GPU 釋放才能啟動。）

### 2.3 單一商品欄位
- **怎麼做**：只對 891 件合格商品，Claude 另外一次呼叫（用 `single_item_prompt.md` 的短 prompt，不動主標註），回答 `single_item`（yes/no + 信心）與 `scene`（white / room / other）。
- **結果**：見第 3 節表格最右邊的「單一商品候選」欄。

## 3. 每格結果
| 格子 | 已標件數 | 合格 / 目標 | 狀態 | 階段 1 合格率 | 階段 2 合格率 | 單一商品候選（yes 且信心 ≥ 2） | queue 還剩 |
|---|---|---|---|---|---|---|---|
| boho × chair | 59 | 33 / 26 | 達標 | 53%（16/30） | 59%（17/29） | 29 | 29 |
| boho × 吊燈 | 50 | 34 / 26 | 達標 | 70%（21/30） | 65%（13/20） | 28 | 121 |
| boho × lamp | 146 | 29 / 26 | 達標 | 20%（6/30） | 20%（23/116） | 25 | 0 |
| boho × wall art | 30 | 19 / 13 | 達標 | 63%（19/30） | -（0/0） | 16 | 270 |
| coastal × chair | 153 | 30 / 26 | 達標 | 27%（8/30） | 18%（22/123） | 26 | 0 |
| coastal × lamp | 75 | 31 / 26 | 達標 | 47%（14/30） | 38%（17/45） | 22 | 225 |
| coastal × table | 162 | 32 / 26 | 達標 | 20%（6/30） | 20%（26/132） | 30 | 11 |
| coastal × wall art | 30 | 23 / 13 | 達標 | 77%（23/30） | -（0/0） | 19 | 270 |
| farmhouse/rustic × chair | 300 | 51 / 26 | 達標 | 10%（3/30） | 18%（48/270） | 30 | 0 |
| farmhouse/rustic × 吊燈 | 131 | 33 / 26 | 達標 | 30%（9/30） | 24%（24/101） | 31 | 169 |
| farmhouse/rustic × lamp | 186 | 38 / 26 | 達標 | 10%（3/30） | 22%（35/156） | 21 | 114 |
| farmhouse/rustic × table | 105 | 30 / 26 | 達標 | 33%（10/30） | 27%（20/75） | 28 | 195 |
| farmhouse/rustic × wall art | 30 | 16 / 13 | 達標 | 53%（16/30） | -（0/0） | 14 | 270 |
| industrial × chair | 135 | 67 / 26 | 達標 | 53%（16/30） | 49%（51/105） | 16 | 41 |
| industrial × 吊燈 | 62 | 37 / 26 | 達標 | 50%（15/30） | 69%（22/32） | 33 | 238 |
| industrial × lamp | 50 | 31 / 26 | 達標 | 60%（18/30） | 65%（13/20） | 27 | 250 |
| industrial × table | 55 | 32 / 26 | 達標 | 53%（16/30） | 64%（16/25） | 31 | 245 |
| industrial × wall art | 93 | 18 / 13 | 達標 | 23%（7/30） | 17%（11/63） | 14 | 68 |
| mid-century × chair | 79 | 41 / 26 | 達標 | 53%（16/30） | 51%（25/49） | 26 | 221 |
| mid-century × 吊燈 | 59 | 42 / 26 | 達標 | 70%（21/30） | 72%（21/29） | 42 | 241 |
| mid-century × lamp | 125 | 30 / 26 | 達標 | 43%（13/30） | 18%（17/95） | 25 | 175 |
| mid-century × table | 87 | 39 / 26 | 達標 | 50%（15/30） | 42%（24/57） | 36 | 213 |
| mid-century × wall art | 117 | 20 / 13 | 達標 | 17%（5/30） | 17%（15/87） | 16 | 183 |
| traditional × chair | 85 | 31 / 26 | 達標 | 33%（10/30） | 38%（21/55） | 27 | 215 |
| traditional × 吊燈 | 87 | 34 / 26 | 達標 | 43%（13/30） | 37%（21/57） | 34 | 213 |
| traditional × lamp | 98 | 37 / 26 | 達標 | 40%（12/30） | 37%（25/68） | 29 | 202 |
| traditional × table | 85 | 33 / 26 | 達標 | 37%（11/30） | 40%（22/55） | 31 | 215 |

來源：`results/stage2_analysis.json`。合計：階段 1 沿用 810 件中合格 342 件（42%）；階段 2 新標 1864 件中合格 549 件（29%）。
> 注意：wall art 的 farmhouse、boho、coastal 三格在階段 2 沒有再標（階段 1 的 30 件就已經超過 13 件的目標），所以階段 2 欄位是「-」。

**合格率階段 1 vs 2**：階段 2 整體合格率（29%）比階段 1（42%）低，主要原因是階段 1 每格固定 30 件、各格權重一樣，而階段 2 是「正票率低的格子拿得多」（例如 farmhouse × chair 把 queue 用完），低合格率的格子在階段 2 占比較大；不能直接說階段 2 的品質變差。看單一格子時，階段 1 每格只有 30 件，誤差很大。

## 4. 合格商品的屬性分布（給 USER_DECISIONS ③ 用）
依 ③ 的新規則：合格商品中出現 ≥ 2 種值的屬性就是自由維度；wall art 只用於情境一。值用三位的多數決。
| 格子 | color 值數 | material 值數 | shape 值數 | 情境二自由維度（值數 ≥ 2） |
|---|---|---|---|---|
| boho × chair | 7 | 2 | 3 | color（7 種）、material（2 種）、shape（3 種），共 3 個 |
| boho × 吊燈 | 6 | 1 | 4 | color（6 種）、shape（4 種），共 2 個 |
| boho × lamp | 8 | 4 | 4 | color（8 種）、material（4 種）、shape（4 種），共 3 個 |
| boho × wall art | 2 | 2 | 2 | （wall art 不出情境二） |
| coastal × chair | 5 | 5 | 2 | color（5 種）、material（5 種）、shape（2 種），共 3 個 |
| coastal × lamp | 7 | 6 | 4 | color（7 種）、material（6 種）、shape（4 種），共 3 個 |
| coastal × table | 7 | 4 | 2 | color（7 種）、material（4 種）、shape（2 種），共 3 個 |
| coastal × wall art | 7 | 5 | 3 | （wall art 不出情境二） |
| farmhouse/rustic × chair | 8 | 2 | 2 | color（8 種）、material（2 種）、shape（2 種），共 3 個 |
| farmhouse/rustic × 吊燈 | 5 | 3 | 5 | color（5 種）、material（3 種）、shape（5 種），共 3 個 |
| farmhouse/rustic × lamp | 9 | 4 | 4 | color（9 種）、material（4 種）、shape（4 種），共 3 個 |
| farmhouse/rustic × table | 5 | 1 | 3 | color（5 種）、shape（3 種），共 2 個 |
| farmhouse/rustic × wall art | 5 | 3 | 2 | （wall art 不出情境二） |
| industrial × chair | 8 | 3 | 2 | color（8 種）、material（3 種）、shape（2 種），共 3 個 |
| industrial × 吊燈 | 2 | 2 | 5 | color（2 種）、material（2 種）、shape（5 種），共 3 個 |
| industrial × lamp | 5 | 2 | 5 | color（5 種）、material（2 種）、shape（5 種），共 3 個 |
| industrial × table | 4 | 3 | 2 | color（4 種）、material（3 種）、shape（2 種），共 3 個 |
| industrial × wall art | 6 | 4 | 2 | （wall art 不出情境二） |
| mid-century × chair | 9 | 4 | 2 | color（9 種）、material（4 種）、shape（2 種），共 3 個 |
| mid-century × 吊燈 | 2 | 2 | 4 | color（2 種）、material（2 種）、shape（4 種），共 3 個 |
| mid-century × lamp | 4 | 3 | 4 | color（4 種）、material（3 種）、shape（4 種），共 3 個 |
| mid-century × table | 7 | 4 | 3 | color（7 種）、material（4 種）、shape（3 種），共 3 個 |
| mid-century × wall art | 4 | 2 | 2 | （wall art 不出情境二） |
| traditional × chair | 8 | 4 | 2 | color（8 種）、material（4 種）、shape（2 種），共 3 個 |
| traditional × 吊燈 | 5 | 2 | 3 | color（5 種）、material（2 種）、shape（3 種），共 3 個 |
| traditional × lamp | 5 | 4 | 3 | color（5 種）、material（4 種）、shape（3 種），共 3 個 |
| traditional × table | 7 | 3 | 3 | color（7 種）、material（3 種）、shape（3 種），共 3 個 |

- 自由維度少於 3 個的情境二格子：boho × 吊燈（2 個）、farmhouse/rustic × table（2 個）。
- 完整的值分布在 `results/stage2_analysis.json` 的 `cells.<格>.attrs`。

## 5. 三方一致性
| 維度 | 階段 1（27 格 796 件）κ | 階段 2 新標（1831 件）κ | 階段 2 兩兩一致率（Claude–Qwen / Claude–Gemma / Qwen–Gemma） |
|---|---|---|---|
| category | 0.93 | 0.93 | 95% / 94% / 96% |
| color | 0.71 | 0.70 | 73% / 68% / 79% |
| material | 0.79 | 0.75 | 78% / 77% / 86% |
| shape | 0.72 | 0.64 | 83% / 72% / 72% |
| style | 0.67 | 0.61 | 62% / 64% / 71% |

- 品項（category）三位都很一致；風格最難，三位之間只有約 6–7 成一致，這也是為什麼要求 Claude 同意 + 另一位同意。
- Gemma 在階段 2 的新商品中有 33 筆輸出不在選項內，記為失敗（算「不同意」，和階段 1 一樣）；Qwen 失敗 0 筆。

## 6. 成本
| 項目 | 金額 / 數量 |
|---|---|
| Claude 主標註 | $17.27（97 次呼叫，1864 件，每件 $0.0093） |
| Claude 單一商品欄位 | $5.40（46 次呼叫，891 件，每件 $0.0061） |
| Claude 合計 | $22.67（預算 $40） |
| 碰到用量上限的呼叫 | 0 次 |

來源：`claude_calls.jsonl`、`single_item_calls.jsonl`。

## 7. 限制
- 每格的「合格」仍然是模型標註，不是人工確認；Claude 對 industrial 的把關有幫助（USER_DECISIONS ⑨），但沒有再做人工抽查。
- 階段 2 的商品是依「Claude 正票率」不斷往 queue 取，所以每格取的件數不同；合格率是每格自己的估計，樣本只有幾十件，誤差不小。
- 屬性分布用三位多數決；沒有多數（三位都不同）的件不計入值數。
- 補標到合格數剛好達標的格子（例如 boho × lamp 29/26、farmhouse/rustic × wall art 16/13、coastal × chair 30/26、farmhouse/rustic × table 30/26、mid-century × lamp 30/26）幾乎沒有餘裕：之後如果題目要求多樣性或排除重複，可能不夠。

## 8. 需要 Skyler 決定的事
1. **餘裕不大的格子**要不要多標一些（queue 還有商品的格子，每多標 20 件約 $0.19）？
2. **情境二自由維度少的格子**（第 4 節）：如果教授不同意把 n_d ≥ 4 放寬成 ≥ 2，這些格子要重新評估。
3. **queue 用完的格子**（boho × lamp、coastal × chair、farmhouse/rustic × chair）：沒有更多商品可補，只能維持現狀。

## 自我驗收（`verify2.py` 的輸出，2026-11-17 UTC）
1. 重跑 compute_qualified → analyze → make_report2 後，3 個輸出檔（stage2_analysis.json / .md、本報告）的 md5 與重跑前相同：通過。
2. 報告 27 格表每一列的「合格 / 目標、狀態、單一商品候選、queue 剩餘」與 JSON 一致（不一致 0 格）；總合格數與總花費與 JSON 一致：通過。
3. `D/stage1/*.jsonl` 的 sha256 與 `stage1_sha256_before.txt` 相同：通過。
4. 沒有殘留的 `-devset2` vLLM，8081–8089 沒有被我佔用：通過。
5. D 底下 S 以外、本階段啟動後被修改的檔案：0 個。所有新檔都寫在 S；沒有用 subagent、沒有 git push、沒有呼叫其他付費 API。
