# 開發集 v0：階段 0（建商品池）＋ 階段 1（抽樣三方標註）守則（2026-11-17 凌晨，無人值守）

你是無人值守的 agent。使用者 Skyler（博一新生）在睡覺，**不會回答問題**，不要呼叫 AskUserQuestion。自己判斷，判斷寫進 `DECISIONS.md`（每條附理由）。
D = `/mnt/raid0/home/skyler/vlm-diverse-retrieval/devset_v0/`，R = `/mnt/raid0/home/skyler/vlm-diverse-retrieval/`。
進度寫 `D/PROGRESS.md`（每步一行：`[UTC 時間] 階段/工作 — 結果`）。被中斷重啟時先讀 PROGRESS.md、DECISIONS.md，從中斷處繼續；所有腳本都要能續跑（做過的跳過）。

## 0. 背景：先讀這些
- `R/agent_prompt_研究進度更新.md`（教授回饋；第 2 節固定設定：5 個維度 style、category、color、material、shape；第 4 節規則）
- `R/overnight_2026-11-14/C1_category/C1_report.md`、`c1_stats.py`（`ITEM_RULES` 在第 80 行附近、`STYLE_REGEX` 在第 41 行附近、本機資料位置）
- `R/overnight_2026-11-14/C3_annotation/C3_design.md`、`guideline_v0.md`（標註準則 v0 與試標發現的問題）
- `R/overnight_2026-11-14/C4_query/C4_design.md`（第 4 節去重複規則、第 6 節建議組合）
- `R/overnight_2026-11-14/D_main_table/main_table_draft.md`（題目怎麼用這些標註）
- `R/overnight_2026-11-16/REPORT_白話版.md` 第 5 節（串接小題組：借用標籤造成的問題，這次要避免）
- 啟動 vLLM 的做法：`R/overnight_2026-11-16/serve_model.sh`、`job.sh`（一張卡最多一個自己的 server、gpu_claims、等卡規則）

## 1. 範圍（Skyler 已確認）
- 6 種風格：mid-century（modern）、industrial、farmhouse/rustic、boho、coastal、traditional
- 5 種品項：chair、table、lamp（桌燈、落地燈）、chandelier/pendant（吊燈）、wall art
- 共 30 格「風格 × 品項」。

## 2. 階段 0：建商品池（不花 Claude 標註額度）
1. 從本機 Amazon Reviews 2023 子集（C1 報告「總量」那張表的來源）用 C1 的 `ITEM_RULES` 決定品項、`STYLE_REGEX` 決定「關鍵字風格」，撈出 30 格的候選。只用有主圖 URL 的商品。注意 C4 提到的誤抓（例如 sofa table / console table 不是沙發；有按摩功能的躺椅），必要時修品項規則，修了什麼寫進 DECISIONS.md。
2. 每格記下「關鍵字命中總數」（這是之後算可用量的分母），然後每格最多隨機保留 300 件（seed 0）進商品池。
3. 另外建「無風格關鍵字」的干擾池：5 個品項各隨機 300 件，標題與 details 都不含任何風格字詞（之後當隨機干擾項；階段 1 不標它）。
4. 去重複（C4 第 4 節）：同 store 且去掉顏色、尺寸字詞後標題 token Jaccard ≥ 0.8 視為同款只留一件；下載圖片後再用感知雜湊（pHash）去掉近似重複。
5. 下載主圖到 `R/data/derived/devset_images/<parent_asin>.jpg`（用 metadata 裡最大的主圖；平行 ≤ 8、失敗重試 3 次、記錄失敗）。總大小上限 5 GB；`/mnt/raid0` 可用空間低於 250 GB 就停止並記錄。
6. 輸出 `D/stage0/pool.jsonl`（每件：parent_asin、title、store、來源子集、類別路徑、品項、關鍵字風格、圖片路徑、sha256、phash、是否在干擾池）與 `D/stage0/cell_counts.json`（每格命中總數、去重後數量、入池數量、下載失敗數）。

## 3. 階段 1：每格抽 30 件做三方標註（= 階段 2 的第一批，標註之後直接沿用）
### 3.1 準則 v1
以 `guideline_v0.md` 為基礎寫 `D/stage1/guideline_v1.md`，補上 C3 第 1.3 節列的問題：燈具看燈座／燈身不看燈罩（或你判斷更好的明確規則）、多部件商品（多頭吊燈）的形狀、coastal vs boho、mid-century vs modern minimalist / scandinavian 的區分。
- style 選項：6 個目標風格 + modern minimalist、scandinavian、glam、other + mixed/none（不要只給 6 選 1）。
- 其他 4 維的選項沿用 v0（必要時微調並記錄）。每個維度附信心 1–3。
- 三位標註者用**完全相同的準則文字**。

### 3.2 抽樣
每格從商品池隨機抽 30 件（seed 0；不足 30 就全取並記錄）→ 最多 900 件，存 `D/stage1/sample.jsonl`。標註者**只看圖**（不給標題、ASIN、格子風格）。每件送一張圖。

### 3.3 三位標註者
1. **Claude（固定用 Opus 5.5）**：**用精簡呼叫，不要用預設的 Claude Code system prompt、不要用 Read 工具讀圖**（11/17 Skyler 要求省額度；主對話 Claude 已實測可行）。做法：
   - 指令：`claude -p --model claude-opus-5-5 --system-prompt "<準則 v1 全文 + 輸出格式>" --tools "" --strict-mcp-config --setting-sources "" --input-format stream-json --output-format stream-json --verbose --no-session-persistence < batch.jsonl`（先 `unset ALL_PROXY HTTPS_PROXY HTTP_PROXY all_proxy http_proxy https_proxy`）。**不要加 `--bare`**（會讀不到登入憑證，回 "Not logged in"）。
   - `batch.jsonl` 是一行 stream-json 使用者訊息：`{"type":"user","message":{"role":"user","content":[...]}}`；content 依序放「`{"type":"text","text":"item_id: <id>"}` + `{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":...}}`」，最後一個 text 說「依準則標註以上每一件，只輸出 JSON lines」。
   - system prompt = 準則 v1 全文 + 「每個 item_id 只輸出一行 JSON（id、style、style_conf、category、category_conf、color、color_conf、material、material_conf、shape、shape_conf），不要任何其他文字、不要解釋、不要 Markdown」。每批用**完全相同**的 system prompt 文字（才吃得到快取）。
   - **圖片先縮到長邊 768 px（JPEG 品質 90）再送**（11/17 主對話加入）：下載的主圖多是 1500 px，Claude 會把每張算成約 1,600 tokens；768 px 約 800 tokens，判斷風格、材質、顏色綽綽有餘。縮圖存 `D/stage1/img768/`（只給標註用，不改原圖）。**三位標註者都用同一份 768 px 縮圖**，保持一致；階段 2 也要沿用同一設定。
   - **每批 20 張**（主對話建議的 sweet spot：固定開銷攤平得夠，又不會因為圖太多而錯位或注意力分散）。每批的商品要**跨格子隨機混合**（不要同一批都是同風格，避免比較效應），用固定 seed 打亂。
   - 驗證：回傳的 id 集合必須等於送出的 id 集合、每行可解析、值在選項內；缺漏或不合法的件數重送（重送時每批 ≤ 5 張）。
   - 從 stream-json 最後一行 `type: result` 讀 `total_cost_usd`、`usage`，存 `D/stage1/claude_calls.jsonl`。
   - 主對話實測參考（3 張、極簡準則）：輸入約 1,354 tokens、輸出 101 tokens、$0.0129、沒有 thinking tokens。20 張 + 完整準則預估每件約 $0.003–0.006。
   - **批量品質小檢查**：前 100 件標完後，另外抽其中 40 件用「每批 5 張」重標一次，比較和「每批 20 張」的一致率（各維度）。一致率明顯偏低（例如 style < 85%）就改成每批 10 張並記錄。這個檢查的成本算進預算。
   - **成本檢查點**：先只標 100 件，算出每件平均 `total_cost_usd`，推估 900 件的總額寫進 PROGRESS.md 與 DECISIONS.md。**推估總額 ≤ 30 美元才繼續標剩下的 800 件**；超過就停止 Claude 標註（本地模型照做），在報告寫清楚，等 Skyler 決定。
   - 碰到 5 小時用量上限：不用處理，看守程式會等到重置後讓你繼續。
2. **Qwen3.8-27B-FP8**、3. **gemma-4-12b-it**（vLLM，`~/miniforge3/envs/adl_hw3_py311`，不可修改此環境；啟動參數照 `R/overnight_2026-11-16/` 與 `R/smoke_2026-11-15/REPORT_白話版.md`；Qwen 加 enable_thinking=false 與 max_pixels 409600；兩個都是 TP=2）。served name 以 `-devset_2026-11-17` 結尾，port 8081–8089；一張 GPU 最多一個自己的 server，只用 5090（0 1 3 4），只用空閒記憶體，不碰別人的程式。temperature 0，同一份準則文字，輸出同樣的 JSON 格式；解析失敗重試 1 次，仍失敗記為失敗。
   - 某個模型等卡超過 4 小時：先做別的，最後再試；仍排不到就在報告寫明，只用其他兩位的結果做分析。

### 3.4 分析（`D/stage1/analyze.py` → `D/results/stage1_analysis.json`、`.md`）
- **每格**：(a) 「多數決風格 = 格子風格」的比例（關鍵字準確率）；(b) 三位風格完全一致的比例；(c) 三位一致且 = 格子風格、且沒有人給信心 1 的比例（= 可當合格答案的比例）；(d) 推估可用量 = 命中總數 × (c)（附 95% 信賴區間；n=30 很小要寫明）；(e) 品項規則和標註者品項不一致的比例。
- **每個維度**：Fleiss κ、兩兩一致率（Claude–Qwen、Claude–Gemma、Qwen–Gemma）、各標註者的信心分布。
- **成本**：Claude 每件實測美元與 token；兩個本地模型每件秒數。推估階段 2：依 (c) 算出每格要標多少件才能湊到「每格 ≥ 12 件確定合格 × 足夠題數」（題數規劃見 D 文件；開發集目標情境一、情境二各 50 題），換算 Claude 美元與「五小時額度」數（用 1 個額度 ≈ 10–15 美元的經驗值，寫明是經驗值）。
- **給 Skyler 人工抽查用**：分層抽 60 件（每格 2 件，優先三方不一致的）存 `D/stage1/review_sample.json`（不要做網頁、不要發布 artifact）。

## 4. 限制
- 不下載模型；不升級 vLLM；不建新 conda 環境；不在 `R/.venv` 安裝套件（需要 imagehash 之類的套件時，先檢查是否已安裝；沒有就自己用 PIL 寫簡單的 pHash/aHash）。
- 不修改或刪除任何既有檔案（`R/pilot1/`、`R/pilot2/`、`R/overnight_*`、`R/smoke_*`、`R/models/`、`R/data/` 既有內容）；新檔只寫在 D 和 `R/data/derived/devset_images/`。
- 只 kill 自己 served name 含 `devset_2026-11-17` 的 vLLM。不呼叫 Gemini 或其他付費 API；不讀或印出 `~/.config/gemini_api_key`；不 git push；不發布 artifact。
- 除了 3.3 規定的 `claude -p` 標註呼叫，不要使用 subagent。
- 規模就是上面寫的；不要開始階段 2，不要出題、不要跑選品實驗。

## 5. 產出
- `D/REPORT_白話版.md`：給博一新生看（寫法同 `R/overnight_2026-11-16/REPORT_白話版.md`：先講結論、名詞解釋、每段「為什麼 / 怎麼做 / 結果 / 代表什麼」、數字附來源檔、限制、需要 Skyler 決定的事）。重點表格：30 格的命中數、關鍵字準確率、三方一致率、推估可用量；各維度 κ；成本與階段 2 推估（含額度數）；建議保留 / 拿掉哪些格子。
- 自我驗收（寫進報告最後一節）：重跑分析腳本結果相同；報告數字和 results 一致；沒有殘留的自己的 vLLM；沒有寫入受保護的資料夾。
- 全部完成後在 PROGRESS.md 最後一行寫 `ALL DONE`。
