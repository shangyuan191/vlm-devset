> **Opus 審查後修改（2026-11-18，審查階段 3 後加的；只補充做法，不改題型、規模或 Skyler 的決定）**
> 1. **解析度沿用階段 3 的偏離**（階段 3 DECISIONS 11、12）：Qwen 系列 `max_pixels` = 307200、LLaVA-OV2 `IMG_MAX=560`，其餘 900。直接複製 T 的 `serve_devset3.sh` / `tasks_run.sh` 再改名即可。理由：409600 / 900 會超過 16384 tokens；和階段 3 一致才能把 S1/S2 tmpl_zh 結果拿來比。
> 2. **smoke 標準加嚴**：prompt tokens 最大值 **+ 512 ≤ 16384**（階段 3 只檢查 < 16384）。LLaVA-OV2 在階段 3 最大已到 15855，很接近上限。
> 3. **去風格字要反覆刪到不再變**：`clean()` 對 `STYLE_PAT` 重複 sub 直到字串不變（階段 3 的 item_0773 "Mid Modern Century" 刪一次後變成 "Mid Century"）。只用在 T3 / T4 新題；S1 / S2 沿用 `T/questions.json` 原標題，不重建，保持和階段 3 可配對比較。在 DECISIONS 記錄。
> 4. **siglip2-mmr-free 要標 †**：它會讀候選的標註屬性（特權資訊），表格與報告都要註明「非公平基準線」；公平的純圖片對照是 siglip2-top5、siglip2-mmr-std。
> 5. **標出標註者模型**：gemma4-12b、qwen38-27b 也是出題用的標註者，所有主表在它們名稱後加 ‡ 並在限制寫明。qwen38-27b 同時是 syn_en 的改寫者，報告要特別提醒它的 syn_en 分數可能偏高（自己改寫、自己作答）。
> 6. 其他照本文件；詳見 `T/OPUS_REVIEW.md`「階段 4 要注意」。

# 開發集 v0：階段 4（Negation、多重限制、合成 query）守則（2026-11-18 起，無人值守）

你是無人值守的 agent。使用者 Skyler（博一新生）**不會回答問題**，不要呼叫 AskUserQuestion。自己判斷，判斷寫進 `U/DECISIONS.md`（每條附理由）。
R = `/mnt/raid0/home/skyler/vlm-diverse-retrieval/`，D = `R/devset_v0/`，S = `D/stage2/`，T = `D/stage3/`，**U = `D/stage4/`（本階段工作目錄）**。
進度寫 `U/PROGRESS.md`（每步一行：`[UTC 時間] 步驟 — 結果`）。被中斷重啟時先讀 U 的 PROGRESS.md、DECISIONS.md，從中斷處繼續；所有腳本都要能續跑。
**設計已由 Skyler 和主控（Opus）決定，寫在本文件。照做，不要自己改設計。** 做不到時選最接近的做法，寫進 DECISIONS 與報告「需要 Skyler 決定的事」。

## 0. 先讀這些
- `T/RUNBOOK.md`、`T/REPORT_白話版.md`、`T/OPUS_REVIEW.md`（主控對階段 3 的審查；**其中「階段 4 要注意」的指示優先於本文件**）、`T/DECISIONS.md`
- `T/` 的腳本：`common3.py`、`build_questions.py`、`run_select.py`、`run_style.py`、`score.py`、`baselines.py`、`serve_devset3.sh`、`job3.sh`、`tasks_run.sh`（**複製到 U 再改，不改 T 的檔案**）
- `D/USER_DECISIONS.md`；`R/overnight_2026-11-14/C4_query/C4_design.md`（T3、T4 模板與 query 文字規則）；`R/agent_prompt_研究進度更新.md` 的 B-3 節
- `R/overnight_2026-11-14/C2_esci_abo/results/b1_example_queries.tsv`（ESCI 真實家具 query，當措辭範例）

## 1. 這次要做什麼
1. 出兩種新題型：**T4 Negation**、**T3 多重限制**。
2. 為所有題目（S1、S2、T3、T4）產生**合成 query 文字**（英文自然口語）。
3. 用 7 個本地模型跑，計分、寫報告。

## 2. 出題（`U/build_questions4.py` → `U/questions4.json`、`U/build_report4.json`）
沿用階段 3 的商品屬性定義（B1）、排除規則（同 parent_asin、phash 重複、query 本身）、固定 seed 抽樣、硬性檢查（合格 = 12、|F| ≥ 2、Oracle EffCov@5 = 1.00，用 `metrics.py`）、最多重抽 200 次。用**最新的** `S/qualified.jsonl`（891 件合格）。

### 2.1 T4 Negation（限制：style = X，category ≠ C；C = query 的品項）
- query：沿用階段 3 的 **108 個 query**（`T/questions.json`），每個一題 → 約 108 題。
| 組成 | 件數 | 來源 |
|---|---|---|
| 合格 | 12 | 風格 X、品項 ≠ C 的合格商品（含 wall art），依品項輪流取，盡量涵蓋全部其他品項 |
| 陷阱（同風格同品項） | 12 | 格子 (X, C) 的其他合格商品——風格對但品項是「不要」的那種 |
| 困難干擾 | 8 | 其他風格、品項 ≠ C 的合格商品 |
| 隨機 | 8 | 三方都標過、「確定不是 X」的商品 |
- 自由維度可含 category（C 以外的品項）。

### 2.2 T3 多重限制（限制：style = X，category = C，另一個屬性 a = v）
- **可出題的組合**：格子 (X, C)（非 wall art）× 屬性 a ∈ {material, color} × 值 v，同時滿足：
  1. 該格合格商品中 a = v（多數決）的件數 n ≥ 12；
  2. **排除比例**：1 − n / 該格合格數 ≥ 30%（否則限制等於沒加）；
  3. 符合的商品中，另外兩個屬性（{color, material, shape} 扣掉 a）都有 ≥ 2 種值。
  （主控 11/17 用 891 件試算：25 個組合、17 格通過。若你算出的數字不同，以實際計算為準並記錄。）
- 每個組合出 **3 題**（n = 12 的組合出 2 題），query 從該格「query 等級」商品抽（同階段 3 B2 條件；不夠時放寬成：合格 + single_item yes conf ≥ 2，記錄）。不同題用不同 query。記錄每題 query 本身的 a 是否等於 v。預計約 68 題。
| 組成 | 件數 | 來源 |
|---|---|---|
| 合格 | 12 | 格子 (X, C) 中 a = v 的合格商品 |
| 屬性陷阱 | 12 | 格子 (X, C) 中 a ≠ v 的合格商品（不夠 12 時，用風格 X 其他品項、a = v 的合格商品補，記錄） |
| 風格陷阱 | 8 | 品項 C、其他風格、a = v 的合格商品（不夠時放寬成 a 任意，記錄） |
| 隨機 | 8 | 三方都標過、「確定不是 X」的商品 |
- 自由維度 = 合格候選中 n_d ≥ 2 的維度（不含 style、category、a）。

## 3. query 文字（三種寫法）
每題都有三種 query 文字（S1、S2 也要補）：
1. `tmpl_zh`：中文模板句（S1、S2 就是階段 3 的任務句；T3、T4 依同樣結構新寫，例如 T4「請挑 5 件和參考圖片同風格、但**不是**<品項>的商品…」、T3「…同風格、同樣是<品項>、而且是<值中文>的商品…」）。
2. `tmpl_en`：同一句的英文直譯（固定模板，人工寫好，不用 LLM）。
3. `syn_en`：**合成 query**。由 LLM 把英文模板句改寫成「真人在購物網站會打的英文需求句」，然後放進固定的英文任務框架裡（框架 = tmpl_en 去掉模板句後的其餘部分：「從候選中挑 5 件…輸出 JSON…」）。
- 改寫模型：本地 **Qwen3.8-27B**（vLLM，`-devset4`，temperature 0.7，每題固定 seed）。**不給它看圖**，只給模板句 + 8 個 ESCI 真實 query 當措辭範例 + 規則。
- 規則（自動檢查；不過就重新生成，最多 5 次；仍不過就用 tmpl_en 並記錄）：
  - 不可出現風格字詞（`STYLE_REGEX`，同階段 3）；
  - 必須提到參考圖（例如 "this", "the one in the picture", "like this"）；
  - S2、T3 必須提到品項字；T4 必須有否定（not / no / except / other than / anything but）且提到被排除的品項；T3 必須提到屬性值（color / material 的英文詞或明確同義詞，寫好同義詞表）；
  - S1、T4 不可以把品項限制成單一品項（不可只寫 "chairs"）。
  - 長度 4–30 個英文字。
- 存 `U/query_texts.json`（每題：三種文字、改寫 prompt、每次嘗試與檢查結果）。另外隨機抽 30 題寫進報告附錄，給 Skyler 看改寫品質。

## 4. 跑模型
- 7 個模型、啟動參數、GPU 規則同階段 3（served name 結尾 **`-devset4`**，port **8101–8109**，只用 5090 的 0 1 3 4、一張卡最多一個自己的 server、可平行、等卡上限 4 小時）。
- 要跑的請求（每個模型）：
| 題目 | 條件 | 順序 |
|---|---|---|
| T3、T4（約 176 題） | tmpl_zh | 3 個順序 |
| S1、S2、T3、T4（約 392 題） | tmpl_en、syn_en | 只跑題目原順序 |
- prompt 結構、圖片前處理、K = 5、max_tokens 512、容錯解析、重試、smoke test 都同階段 3。不給 style_given 條件。
- 預估每個模型約 1,300 個請求。

## 5. 計分與報告
- `U/score4.py` → `U/results/scores4.json`、`.md`（計分定義同階段 3 的 `score.py`，基準線 Random / Oracle / SigLIP2 / SigLIP2+MMR 也要對新題型算）：
  - **T4 主表**：Align@5、Div@5、EffCov@5、**Trap@5（5 件中選到「同風格同品項」陷阱的比例）**、失敗率；3 順序平均 ± 標準差。
  - **T3 主表**：同上，Trap 分成「屬性陷阱」與「風格陷阱」兩欄；顏色限制與材質限制分開列；另列「query 本身是否等於 v」兩組的差別。
  - **措辭比較**：每個模型、每種題型的 tmpl_zh（只取原順序）vs tmpl_en vs syn_en 的 Align@5、EffCov@5，配對差 + 題目層級 bootstrap 95% CI。
  - 和階段 3 的 S1、S2 合成一張總表（所有題型 × 模型，tmpl_zh 主條件）。
- `U/REPORT_白話版.md`：寫法同 `T/REPORT_白話版.md`（白話、先講結論、名詞小字典、數字由腳本產生、限制、需要 Skyler 決定的事）。
- 自我驗收同階段 3（重跑相同、數字一致、完成題數、無殘留 `-devset4` vLLM、沒寫受保護資料夾、`D/stage1/*.jsonl` sha256 不變）。
- 全部完成後在 `U/PROGRESS.md` 最後一行寫 `ALL DONE`。

## 6. 限制
- 同階段 3 第 E 節全部限制；新檔只寫在 U，不修改 T、S、D 的其他檔案。
- **本階段不呼叫 Claude 標註**（不需要），不使用 subagent，不呼叫付費 API。
- 只 kill 自己的 `-devset4` vLLM（記 PID）。
- 不自己加題型、條件或模型。
- 碰到 5 小時用量上限：不用處理，看守程式會等。
