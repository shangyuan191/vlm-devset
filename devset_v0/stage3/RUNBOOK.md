# 開發集 v0：階段 3（補標緩衝 → 出題 → 第一輪選品實驗）守則（2026-11-17 起，無人值守）

你是無人值守的 agent。使用者 Skyler（博一新生）**不會回答問題**，不要呼叫 AskUserQuestion。自己判斷，判斷寫進 `T/DECISIONS.md`（每條附理由）。
R = `/mnt/raid0/home/skyler/vlm-diverse-retrieval/`，D = `R/devset_v0/`，S = `D/stage2/`，**T = `D/stage3/`（本階段的工作目錄）**。
進度寫 `T/PROGRESS.md`（每步一行：`[UTC 時間] 步驟 — 結果`）。被中斷重啟時先讀 T 的 PROGRESS.md、DECISIONS.md，從中斷處繼續；所有腳本都要能續跑（做過的跳過）。
**設計已經由 Skyler 和主控（Opus）決定好了，寫在本文件。你負責照做；不要自己改設計。** 規則真的做不到時，選最接近的做法、寫進 DECISIONS.md 和報告的「需要 Skyler 決定的事」。

## 0. 先讀這些
- `D/USER_DECISIONS.md`（Skyler 的決定，優先於其他文件。**③ 從本階段起照「n_d ≥ 2」執行**：教授還沒確認，Skyler 決定先用這個規則做 dev set）
- `S/RUNBOOK.md`、`S/REPORT_白話版.md`、`S/common2.py`、`S/compute_qualified.py`、`S/annotate_claude2.py`、`S/annotate_single_item.py`
- `R/overnight_2026-11-14/D_main_table/main_table_draft.md`（第 3、4 節：metric 定義與候選組成）、`metrics.py`
- `R/overnight_2026-11-16/RUNBOOK.md`、`REPORT_白話版.md`（模型怎麼啟動、哪些要特別參數）；`serve_model.sh`、`job.sh`、`chain/run_chain.py`（prompt 結構、容錯解析器）、`siglip/siglip_baseline.py`
- `D/stage0/s0_build_pool.py`（`STYLE_REGEX`：去掉標題中的風格字詞）、`D/stage0/phash_dups.json`（近似重複圖）

## A. 補標緩衝（先做；花一點 Claude 額度）
目的：有幾格「剛好湊滿」，出題時沒有餘裕；industrial × chair 可當 query 的單一商品圖只有 6 張。
- **A1 緩衝目標**：合格數 < 目標 + 4 且 queue 還有商品的格子，補到 **目標 + 4**（26 → 30；wall art 13 → 17）。依 `S/cell_status.json` 目前是：mid_century|lamp（26）、coastal|table（27）、farmhouse_rustic|chandelier_pendant（29）、mid_century|wall_art（15）。queue 用完的格子（boho|lamp 等）不動。
- **A2 industrial|chair**：繼續補標，直到該格合格商品中 `single_item = yes 且 conf ≥ 2` 的件數 ≥ 13，或 queue 用完，或這一格本階段新標滿 100 件（三者先到為止）。
- 做法：**沿用階段 2 的腳本與流程**（Claude 先標 → 本地兩位標 → compute_qualified → 新合格商品標 single_item），可以在 S 裡加參數或新增小腳本，但**不要改變既有結果**；新 id 接續 S/items.jsonl（`round` 記 5 以後）。標註設定一個字都不改（同準則、同縮圖、同 prompt、同模型）。最多 2 輪。
- 這部分**允許寫入 S**（append 標註檔、更新 items / qualified / cell_status / analysis / 報告），並在 `S/PROGRESS.md` 也記一行。完成後重跑 `S/analyze.py`、`S/make_report2.py`、`S/verify2.py`，報告要反映新數字。`D/stage1/*.jsonl` 的 sha256 仍不可變。
- 本地模型的 vLLM served name 用 **`-devset3`** 結尾、port 8091–8099（見 C 節規則）。
- **預算**：本階段 Claude 花費上限 **$5**（`claude_calls.jsonl` + `single_item_calls.jsonl` 在本階段新增的部分）；超過就停止 Claude，用現有資料繼續。

## B. 出題（不用 GPU；`T/build_questions.py` → `T/questions.json`、`T/build_report.json`）

### B1 每件商品的屬性（計分用）
- 只用**三方都標過**的商品（階段 1 的 810 件 + 階段 2 全部）。
- `style`、`category`：合格商品 = 它所在格子的風格 / 品項（`CELL_STYLE` / `CELL_ITEM`）。
- `color`、`material`、`shape`：三位多數決；三位都不同時用 Claude 的值（寫進 DECISIONS）。
- 一件商品對 query 風格 X「**確定不是 X**」⇔ 三位中**沒有任何一位**標 style = X。

### B2 query 圖（每題一張；兩個情境用**同一批** query，才能配對比較 H2）
- 來自 **22 個非 wall art 格子**的合格商品，且：三位 style 都 = 格子風格、Claude style_conf = 3、`single_item = yes` 且 conf ≥ 2。
- 每格最多 **5 個** query（依 `random.Random('0-stage3-query-<cell>')` 從符合的商品中抽）；不足 5 就用全部，記錄。預計約 110 個 query → 約 220 題。

### B3 候選 40 件（兩個情境分開，`main_table_draft.md` 4.2 修改 5）
所有候選都要排除：query 本身、和 query 或其他候選同 parent_asin、`phash_dups.json` 中和它們互為重複的商品。抽樣都用固定 seed（`random.Random('0-stage3-<scenario>-<query id>-<try>')`）。

**情境二 S2（限風格 X + 品項 C = query 的格子）**
| 組成 | 件數 | 從哪裡抽 |
|---|---|---|
| 合格 | 12 | 同格子（X, C）的其他合格商品 |
| 困難干擾 1 | 12 | 品項 C、其他風格格子的合格商品（盡量平均分到其他風格） |
| 困難干擾 2 | 8 | 風格 X、其他品項格子的合格商品（含 wall art） |
| 隨機 | 8 | 三方都標過、「確定不是 X」的商品 |

**情境一 S1（只限風格 X）**
| 組成 | 件數 | 從哪裡抽 |
|---|---|---|
| 合格 | 12 | 風格 X 所有格子（含 wall art）的合格商品；**至少涵蓋 4 個品項**（該風格只剩 4 格時就是全部 4 格），其中 2–3 件和 query 同品項 |
| 困難干擾 1 | 12 | 品項 = query 品項、其他風格格子的合格商品 |
| 困難干擾 2 | 8 | 其他風格、其他品項格子的合格商品，且多數決 color 或 material 和 query 相同（不夠時放寬到其他風格其他品項，記錄） |
| 隨機 | 8 | 三方都標過、「確定不是 X」的商品 |

### B4 每題的硬性檢查（不過就換 seed 重抽，最多 200 次；仍不過就丟掉這題並記錄）
1. 合格 = 12 件；干擾項全部「確定不是 X」（困難干擾來自其他風格格子的合格商品，自動成立；隨機桶要檢查）。在 S2，干擾項的品項不是 C 或風格不是 X 至少一項成立（不可以是合格的）。
2. 自由維度 F = 合格候選中值數 n_d ≥ 2 的維度（USER_DECISIONS ③ 新規則）；**|F| ≥ 2**。S2 的 F ⊆ {color, material, shape}；S1 的 F 可包含 category。
3. **Oracle EffCov@5 = 1.00**（用 `metrics.py` 的 `oracle()`；請 import，不要複製改寫；import 時關掉 `__pycache__` 寫入）。
- 記錄每題：每個自由維度的 n_d、合格候選中「三個自由屬性都相同」的配對數（近似重複，給 Dup@5 用）、S1 合格候選中和 query 同品項的件數。
- 標題：候選與 query 都用**去掉風格字詞的標題**（`STYLE_REGEX`，做法同 pilot 的 `title_clean`；寫進 DECISIONS 你用的是哪個 regex）。
- `T/build_report.json`：題數（每格、每情境）、被丟掉的題與原因、n_d 分布、|F| 分布。

## C. 跑模型（GPU）

### C1 模型（7 個新模型；啟動參數完全照 `R/overnight_2026-11-16/RUNBOOK.md` 第 1 節與它的 job.sh）
qwen38-27b（TP=2）、qwen36-35b（TP=2）、gemma4-12b（TP=2）、qwen35-9b、qwen35-4b、internvl35-1tile、llavaov2-8b。
- 舊模型（Qwen3-VL、InternVL3）**不跑**。不呼叫任何付費 API（Claude、Gemini 都不當受測模型）。
- served name `<前綴>-devset3`，port 8091–8099；只用 5090 的 GPU 0 1 3 4、只用空閒記憶體、**一張卡上同時最多一個自己的 server**、可以多個模型在不同卡上平行；等卡超過 4 小時就先跳過、最後再試一次。
- `--max-model-len 16384`、`--limit-mm-per-prompt '{"image": 41}'`；Qwen3.5/3.6/3.8 加 `enable_thinking=false` 與 max_pixels 409600（同 11-16）。
- vLLM 用 `~/miniforge3/envs/adl_hw3_py311`（不可修改這個環境）。腳本複製 `R/overnight_2026-11-16/serve_model.sh`、`job.sh` 到 T 再改（不改原檔）。

### C2 每個模型要跑的請求（`T/run_select.py`、`T/run_style.py`；輸出 `T/out/<model>/...jsonl`，可續跑）
1. **風格判斷（Style Acc）**：每個 query 一次，只給 query 圖 + 風格清單（`common.OPTIONS['style']` 的 11 個選項，各附 `guideline_v1.md` 裡的一句話定義），要它單選一個，輸出 JSON `{"style": "..."}`。標準答案 = query 的格子風格。
2. **選品 `img`（主條件）**：每題（S1、S2）× 3 個候選順序（題目原順序 + 兩個 seed 打亂）。
3. **選品 `style_given`（H5：認得出但沒用上）**：同 2，但在參考圖後面多一行文字：「參考商品的風格是：<該模型自己在第 1 步的答案>」。也是 3 個順序。
- prompt：中文，結構照 `run_chain.py` 的 one_step（參考圖 → 任務說明 → 每個候選 `POSITION i; title=<去風格字標題>` + 圖 → JSON 格式說明），K = 5，max_tokens 512，temperature 0。
  - S1 任務句：「請從候選中挑 5 件和參考圖片**同風格**的商品，並且讓這 5 件盡量多樣：品項、顏色、材質、形狀盡量不同。」
  - S2 任務句：「請從候選中挑 5 件和參考圖片**同風格、而且同樣是<品項中文名>**的商品，並且讓這 5 件盡量多樣：顏色、材質、形狀盡量不同。」
  - **不可以在 prompt 中寫出風格名稱**（style_given 條件除外，那一行就是實驗操作）。
  - 品項中文名：chair 椅子、table 桌子、lamp 檯燈 / 落地燈、chandelier/pendant 吊燈、wall art 壁面裝飾畫。
- 圖片前處理同 `run_chain.py` 的 `img_url()`（縮到 900、JPEG 85），圖片來源 `R/data/derived/devset_images/<parent_asin>.jpg`。
- 解析：容錯解析器（同 run_chain.py）；selected_positions 必須剛好 5 個、不重複、在 1..40；失敗重試 3 次，仍失敗記 failed（計分 0 分）。每筆存 raw_output、latency、usage、finish_reason。
- **先 smoke test**：第一個啟動的模型先跑 5 題 × 2 情境 × 1 順序，確認 prompt tokens < 16384、解析成功，再跑全部；把 smoke 的 prompt tokens 寫進 PROGRESS。
- 預估量：每個模型約 110 + 220 × 3 × 2 ≈ 1,430 個請求。

### C3 不用 GPU 的基準線（等卡時做；`T/baselines.py`）
- **Random**：每題蒙地卡羅 1,000 次的期望值（`metrics.random_expect`，seed 固定）。
- **Oracle**：每題都應是 1.00（建題時已檢查）。
- **SigLIP2 top-5**、**SigLIP2 + MMR**：沿用 `R/overnight_2026-11-16/siglip/siglip_baseline.py` 的模型與 `R/.venv`（CPU；不要裝套件）。MMR 用「相似度前 10 名內，依該情境的自由維度輪流挑不同值」的簡化版（和 11-16 的品項輪流同一精神；寫清楚做法），另外也報告標準 MMR（λ = 0.7，圖片 embedding cosine）。

## D. 計分與報告
- `T/score.py` → `T/results/scores.json`、`scores.md`：
  - **主表**：每個模型 × 條件（img / style_given）× 情境（S1 / S2）：Align@5、Div@5（條件分數，只算 |V| ≥ 2 的題）、**EffCov@5（headline）**、失敗率；3 個順序的平均 ± 標準差；加 Random、Oracle、SigLIP2、SigLIP2+MMR 列。另一欄「平均 EffCov@5」= S1、S2 平均。
  - **Style Acc**：每個模型；另外列每個風格的正確率、最常見的錯誤風格。
  - **H5 2×2**：依「該模型 Style Acc 答對 / 答錯」把題目分兩組，各自的 img Align@5；以及 style_given − img 的配對差（題目層級 bootstrap 95% CI，10,000 次、seed 固定）。
  - **H2**：同一 query 的 S1 vs S2，只比共同的自由維度（color、material、shape）的逐維度 Div，配對差 + CI。
  - **H3 SameCat@5**（只 S1）：5 件中和 query 同品項的比例 vs 合格候選中同品項的比例 vs Oracle 解的比例。
  - **H6 Dup@5**、**位置偏誤**（選到第 1 個位置的比例、選剛好 [1..5] 的比例）。
  - 每格 / 每風格的 EffCov 分解（附錄表）。
- `T/REPORT_白話版.md`：寫法同 `S/REPORT_白話版.md`（先講結論、名詞小字典、每段「為什麼 / 怎麼做 / 結果 / 代表什麼」、數字附來源檔、限制、需要 Skyler 決定的事）。**數字由腳本從 JSON 產生，不要手打。** Skyler 是初學者，用白話。
  - 限制一定要寫：query 圖的風格沒有人工確認（只靠三方一致 + Claude 高信心）；題數小；③ 的規則教授尚未確認。
- 每完成一個模型就更新一次 scores 與報告草稿。
- **自我驗收**（報告最後一節）：重跑 score.py 結果相同；報告數字與 JSON 一致；每個模型每個條件的完成題數；沒有殘留的 `-devset3` vLLM；沒有寫入受保護的資料夾；`D/stage1/*.jsonl` sha256 不變。
- 全部完成後在 `T/PROGRESS.md` 最後一行寫 `ALL DONE`。

## E. 限制
- 沿用 `D/RUNBOOK.md` 第 4 節與 `S/RUNBOOK.md` 第 5 節全部限制，另外：
  - 新檔只寫在 T（A 節允許寫 S）。不修改 `D/stage0`、`D/stage1`、`D/USER_DECISIONS.md`、D 的報告，以及 `R/pilot1/`、`R/pilot2/`、`R/overnight_*`、`R/smoke_*`、`R/models/`、既有的 `R/data/`。
  - 只 kill 自己的、served name 結尾是 `-devset3` 的 vLLM，**記下 PID 只 kill 那個 PID**；不要用沒限定範圍的 `pkill -f`。
  - 除了 A 節規定的 `claude -p` 標註呼叫，不使用 subagent；不發布 artifact；不 git push；不呼叫 Gemini 或其他付費 API；不讀 `~/.config/gemini_api_key`。
  - 不下載模型或資料、不安裝套件、不建新環境。
  - 規模就是本文件寫的：不要自己加模型、加條件、加題型（多重限制、negation、caption 階梯、規模實驗都**不做**）。
- 碰到 5 小時用量上限：不用處理，看守程式會等到重置後讓你繼續。
