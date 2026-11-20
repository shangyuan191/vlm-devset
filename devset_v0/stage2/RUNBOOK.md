# 開發集 v0：階段 2（補標到每格湊滿合格商品）守則（2026-11-17 起，無人值守）

你是無人值守的 agent。使用者 Skyler（博一新生）**不會回答問題**，不要呼叫 AskUserQuestion。自己判斷，判斷寫進 `S/DECISIONS.md`（每條附理由）。
R = `/mnt/raid0/home/skyler/vlm-diverse-retrieval/`，D = `R/devset_v0/`，S = `D/stage2/`。
進度寫 `S/PROGRESS.md`（每步一行：`[UTC 時間] 步驟 — 結果`）。被中斷重啟時先讀 S 的 PROGRESS.md、DECISIONS.md，從中斷處繼續；所有腳本都要能續跑（做過的跳過）。

## 0. 背景：先讀這些
- `D/RUNBOOK.md`（階段 0、1 的守則；**標註方式、指令、限制完全沿用**，本文件只寫不同的地方）
- `D/REPORT_白話版.md`、`D/DECISIONS.md`（階段 0、1 的結果與判斷）
- **`D/USER_DECISIONS.md`（Skyler 的決定，優先於其他文件）**
- `D/stage1/` 的腳本：`common.py`（選項、system prompt、解析）、`annotate_claude.py`、`annotate_local.py`、`serve_devset.sh`、`job_local.sh`、`make_sample.py`、`analyze.py`
- `D/stage1/human_review_labels.json`（Skyler 人工抽查 60 件的結果；`style` 是人工答案）

## 1. 這次要做什麼（一句話）
在 27 格裡繼續標商品，直到**每格的「合格商品」湊滿目標數**；格子商品全部標完仍不夠就停並記錄。另外替合格商品標「主圖是否只有單一商品」。**不出題、不跑選品實驗。**

## 2. 固定設定（Skyler 已決定，不要改）
- **格子**：30 格刪掉 `boho|table`、`coastal|chandelier_pendant`、`traditional|wall_art` → 27 格。這 3 格不再標。
- **目標合格數**：wall_art 的 5 格（mid_century、industrial、farmhouse_rustic、boho、coastal × wall_art；traditional × wall_art 已刪）各 **13** 件（wall art 只用於情境一，USER_DECISIONS ③）；其他 22 格各 **26** 件。
- **合格條件（USER_DECISIONS ⑨）**：一件商品對它所在格子「合格」⇔
  1. Claude 的 style = 格子風格（`common.CELL_STYLE`），且 Claude 的 style_conf ≥ 2；
  2. 三位中**至少兩位**的 style = 格子風格（Claude 必須是其中一位）；
  3. 三位中至少兩位的 category = 格子品項（`common.CELL_ITEM`）。
  標註失敗的標註者算「不同意」。
- **標註設定完全沿用階段 1**：同一份 `guideline_v1.md` / `common.SYSTEM_PROMPT`（**一個字都不要改**，才和階段 1 的 900 件一致）、768 px JPEG 品質 90 縮圖、Claude Opus 5.5 精簡呼叫（`D/RUNBOOK.md` 3.3 第 1 點的指令，預設思考不關）、每批 20 張跨格子混合、Qwen3.8-27B 與 gemma-4-12b 一次 1 張、temperature 0、同一個解析器 `common.parse_lines`。
- 階段 1 已標的 900 件（扣掉 3 個刪除格子是 810 件）**直接沿用，不重標**，算進每格的合格數。

## 3. 怎麼做

### 3.1 準備（不花額度）
- 建 `S/queue.jsonl`：27 格中每格**還沒標過**的商品（商品池 `D/stage0/pool.jsonl` 的格子部分，扣掉 `D/stage1/sample.jsonl` 已有的 parent_asin），每格依 `random.Random('0-stage2-<cell>').shuffle(依 parent_asin 排序的清單)` 排好順序。
- id 接續階段 1：`item_0901` 起；縮圖放 `S/img768/`（做法同 `make_sample.py`）。只在需要時才做縮圖也可以，但 id 一旦發出就固定，記在 `S/items.jsonl`（欄位同 `sample.jsonl`，另加 `round`）。

### 3.2 一輪一輪標，Claude 先標（Claude 是守門員，也是花錢的地方）
因為合格條件要求 Claude 同意，所以 **Claude 先標**；本地模型之後再一次標完。

每一輪：
1. 對每個還沒達標的格子，算出 **Claude 目標數** = ceil(該格目標合格數 ÷ 0.9) + 2（0.9 是階段 1 實測「Claude 說合格時，本地模型至少一位同意」的比例；26 → 31，13 → 17）。
   **Claude 正票** = Claude style = 格子風格、style_conf ≥ 2、category = 格子品項（含階段 1 已標的件數）。
2. 正票還不夠的格子：估計還差幾件 → 依該格目前的「正票率」（階段 1 + 已標部分）算要再拿幾件，**至少 20 件、最多拿到該格 queue 用完**；從 queue 依序取。正票率為 0 的格子一次取 40 件。
3. 把這一輪要標的商品全部打亂（固定 seed：`random.Random('0-stage2-round<k>')`），每 20 件一批送 Claude（沿用 `annotate_claude.py` 的做法；可以複製到 S 改成讀 `S/items.jsonl`、寫 `S/ann_claude.jsonl`，**不要改 D/stage1 的檔案**）。
4. 重複到所有格子的 Claude 正票都達標，或 queue 用完。

### 3.3 本地模型
- Claude 階段完成後，Qwen3.8-27B 和 gemma-4-12b 各啟動一次 vLLM，標 `S/items.jsonl` 的**全部**商品（不只 Claude 正票，干擾項之後也需要三方標註）。
- 腳本複製 `serve_devset.sh`、`job_local.sh`、`annotate_local.py` 到 S 改用；served name 結尾改成 **`-devset2`**（port 8081–8089，規則同前：只用 5090 的 0 1 3 4、只用空閒記憶體、一張卡最多一個自己的 server、等卡上限 4 小時）。
- 也可以在 Claude 還在標的時候先讓本地模型標已經發出 id 的商品，只要不重複標、可續跑。

### 3.4 算合格、補標
- `S/compute_qualified.py`：合併階段 1（810 件）與階段 2 的三方標註 → `S/annotations_all.jsonl`（每件：id、cell、parent_asin、三位標註、是否合格），`S/qualified.jsonl`（只有合格的），`S/cell_status.json`（每格：已標件數、Claude 正票、合格數、目標、queue 剩幾件、狀態 = 達標 / 不足但已標完 / 進行中）。
- 有格子**合格數 < 目標**、queue 還有商品 → 再做一輪 3.2 + 3.3（只對這些格子；Claude 目標改成「還差的合格數 ÷ 該格實測的確認率 + 2」）。**最多補 2 輪**；之後還不夠就記為「不足」，在報告裡寫清楚。

### 3.5 單一商品欄位（USER_DECISIONS ⑧）
- 只對**合格商品**（含階段 1 的）標一個新欄位，由 Claude 單獨一次呼叫（不改主標註的 system prompt）：
  - `single_item`：`yes` = 主圖中只有這一件商品（可以有背景或情境擺設，但主角明確只有一件）；`no` = 一張圖裡有多件同類商品並列（例如一組 2 張椅子、多色並排）、或是拼貼多張小圖、或看不出主角是哪一件。另附 `single_item_conf` 1–3。
  - 另一個欄位 `scene`：`white` = 白底或純色去背；`room` = 房間情境照；`other`。
- 自訂一份很短的 system prompt（寫在 `S/single_item_prompt.md`，固定不變）；每批 20 張；結果寫 `S/ann_single_item.jsonl`。

### 3.6 預算與檢查點
- **Claude 總預算上限 $40**（主標註 + 單一商品欄位 + 重送都算）。依階段 1 實測每件 $0.0092，點估計約 1,300 件、$12。
- **檢查點 1**：Claude 標完前 200 件後，算每件平均成本與「推估總額」寫進 PROGRESS.md。推估 > $40 → 停止 Claude（本地模型照做），寫報告等 Skyler 決定。
- 任何時候累計花費達 $40 → 立刻停止 Claude 呼叫。
- 碰到 5 小時用量上限：不用處理，看守程式會等到重置後讓你繼續。

## 4. 分析與報告
- `S/analyze.py` → `S/results/stage2_analysis.json`、`.md`：
  - 每格：已標件數、合格數 / 目標、狀態、合格率（階段 1 與階段 2 分開列，看兩者是否差很多）。
  - 合格商品的屬性分布：每格的 color、material、shape 各有幾種不同值（多數決；給 USER_DECISIONS ③ 用）。依 ③ 的新規則（自由維度 = 合格商品中 ≥ 2 種值；wall_art 只用於情境一），列出每格情境二的自由維度與值數。
  - 單一商品欄位：每格合格商品中 `single_item = yes` 且 conf ≥ 2 的件數（= 可當 query 圖的候選數）。
  - 三方一致性：沿用階段 1 的 Fleiss κ 與兩兩一致率（只算階段 2 新標的），和階段 1 比較。
  - 成本：Claude 實際花費（主標註、單一商品欄位分開）、每件成本、本地模型每件秒數與總時數。
- `S/REPORT_白話版.md`：寫法同 `D/REPORT_白話版.md`（先講結論、名詞小字典、每段「為什麼 / 怎麼做 / 結果 / 代表什麼」、數字附來源檔、限制、需要 Skyler 決定的事）。**Skyler 是初學者，請用白話、避免術語；必要的術語先解釋。**數字由腳本從 JSON 產生，不要手打。
- 自我驗收（寫進報告最後一節）：重跑分析結果相同；報告數字和 JSON 一致；沒有殘留的自己的 vLLM；沒有寫入受保護的資料夾；階段 1 的檔案沒被改（`D/stage1/*.jsonl` 的 sha256 要和 `S/stage1_sha256_before.txt` 相同）。

## 5. 限制
- 沿用 `D/RUNBOOK.md` 第 4 節全部限制，另外：
  - **新檔只寫在 S**（和 `R/data/derived/devset_images/`，但這次應該不需要下載新圖）。**不要修改 `D/` 底下 S 以外的任何檔案**（包括 D/stage0、D/stage1、D 的報告與 USER_DECISIONS.md）。
  - 只 kill 自己的、served name 結尾是 `-devset2` 的 vLLM。**不要用沒限定範圍的 `pkill -f`**（階段 1 犯過這個錯，見 `D/DECISIONS.md` 第 26 條）：要停自己的程序時，記下 PID 並只 kill 那個 PID。
  - 除了 3.2、3.5 規定的 `claude -p` 標註呼叫，不要使用 subagent。不發布 artifact、不 git push、不呼叫其他付費 API。
  - 不改準則、不改合格條件、不改格子、不出題。覺得規則有問題 → 寫在報告「需要 Skyler 決定的事」。
- 全部完成後在 `S/PROGRESS.md` 最後一行寫 `ALL DONE`。
