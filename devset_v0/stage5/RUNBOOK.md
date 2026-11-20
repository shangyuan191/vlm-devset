> **2026-11-20 更新（USER_DECISIONS ⑬）**：`img_goldstyle` 與它的比較對象 style_given 已移出實驗矩陣；下文關於這兩個條件的設計只是歷史紀錄。

# 開發集 v0：階段 5（正確 caption 階梯）守則（2026-11-19 起，無人值守；Skyler 已確認設計）

你是無人值守的 agent。使用者 Skyler（博一新生）**不會回答問題**，不要呼叫 AskUserQuestion。自己判斷，判斷寫進 `V/DECISIONS.md`（每條附理由）。
R = `/mnt/raid0/home/skyler/vlm-diverse-retrieval/`，D = `R/devset_v0/`，T = `D/stage3/`，U = `D/stage4/`，**V = `D/stage5/`（本階段工作目錄）**。
進度寫 `V/PROGRESS.md`（每步一行：`[UTC 時間] 步驟 — 結果`）。被中斷重啟時先讀 V 的 PROGRESS.md、DECISIONS.md，從中斷處繼續；所有腳本都要能續跑。
**設計已由 Skyler 和主控（Opus）決定，寫在本文件。照做，不要自己改設計。** 做不到時選最接近的做法，寫進 DECISIONS 與報告「需要 Skyler 決定的事」。

## 0. 為什麼做（一段話）
pilot（11-16）的 caption 階梯用的是「模型自己看圖寫的 caption」，分數低時分不出是「caption 寫錯」還是「寫對了但作答時沒用上」。這次改用**參考圖的正確屬性**當 caption，而且**不給參考圖**，只給文字描述，一階一階加維度。這樣分數只反映「拿到正確描述後，能不能在 40 件候選中認出符合的商品」。另外加一個「圖 + 正確風格」條件，和階段 3 的「圖 + 模型自己寫的風格」（style_given）比，量出「風格寫錯」造成的損失。

## 1. 先讀這些
- `T/RUNBOOK.md`、`T/DECISIONS.md`、`T/OPUS_REVIEW.md`、`U/RUNBOOK.md` 開頭的「Opus 審查後修改」（解析度偏離、smoke 標準、‡ / † 標示），**全部沿用**
- `T/` 的腳本：`common3.py`、`run_select.py`（prompt 結構，`build()` 第 9 行）、`score.py`、`serve_devset3.sh`、`tasks_run.sh`；`U/serve_devset4.sh`、`U/launch_models.sh`、`U/watch.sh`（**複製到 V 再改，不改 T、U 的檔案**）
- `D/USER_DECISIONS.md`
- `R/overnight_2026-11-16/REPORT_白話版.md` 第 4 節（pilot 階梯的設計與結果，報告要和它對照）

## 2. 題目與 caption
- 題目：**`T/questions.json` 的 216 題（S1 108、S2 108），原樣使用**，候選、順序、去風格字標題都不變，才能和階段 3 配對比較。不出新題。
- 參考圖的正確屬性（gold caption）：
  - 風格 = 題目的 `style`（參考圖是三方一致的合格商品）；品項 = 題目的 `category`
  - 材質、顏色、形狀 = 題目 `query` 欄位的 `material`、`color`、`shape`（三方多數決，與計分用的相同）
  - 值一律用標註選項的英文原文（例如 `farmhouse/rustic`、`natural wood`），和 style_given 的寫法一致。

## 3. 條件（每個模型 8 個條件，全部 216 題 × 3 個順序 o0 o1 o2）
| 條件 | 參考圖 | 給的 caption（依序） |
|---|---|---|
| `cap_g0` | ✘ | 無 |
| `cap_g1` | ✘ | 風格 |
| `cap_g2` | ✘ | 風格、品項 |
| `cap_g3` | ✘ | 風格、品項、材質 |
| `cap_g4` | ✘ | 風格、品項、材質、顏色 |
| `cap_g5` | ✘ | 風格、品項、材質、顏色、形狀 |
| `cap_g5_nostyle` | ✘ | 品項、材質、顏色、形狀 |
| `img_goldstyle` | ✔ | 風格（正確答案），寫法和 style_given 完全相同：`參考商品的風格是：{style}` |

- 順序 o0 o1 o2 = 階段 3 的同一套打亂（直接沿用 `run_select.py` 的做法），每個條件 3 個順序都跑。
- 對照組不用重跑：`T/out/<model>/select_img_*.jsonl`（只看圖）、`select_style_given_*.jsonl`（圖 + 模型自己寫的風格）、`style.jsonl`（模型自己寫的風格答案）。

### 3.1 prompt（新寫 `V/run_caption.py`，其餘和 `T/run_select.py` 的 `build()` 逐字相同）
- 有圖的條件（`img_goldstyle`）：和 `T/run_select.py` 的 style_given 完全相同，只把 `style_line` 換成正確風格。
- 沒有圖的條件：把開頭兩段（介紹句 + 參考圖片）換成
  - `cap_g0`：`使用者想找和某件參考商品風格一樣的商品，但這次沒有提供參考商品的圖片或描述。`
  - 其他：`使用者想找和某件參考商品風格一樣的商品。這次沒有參考商品的圖片，只有它的描述：` + 每條一行 `- 風格：farmhouse/rustic`（維度名稱用中文：風格、品項、材質、顏色、形狀；值用英文原文）
- 任務句：把 `參考圖片` 改成 `參考商品`，其餘一字不改（S1：「…挑 5 件和參考商品**同風格**的商品，並且讓這 5 件盡量多樣：品項、顏色、材質、形狀盡量不同。」；S2 同理）。
- 候選列表、JSON 輸出要求、K = 5、max_tokens、容錯解析、重試 3 次、失敗記 0 分，全部同階段 3。
- 每個條件存 `V/out/<model>/select_<cond>_<order>.jsonl`，欄位同階段 3，另加 `caption_lines`（實際給的 caption 文字）。**存檔前用 1 題印出完整 prompt 文字到 `V/logs/prompt_example_<cond>.txt`，報告附錄要附 8 個條件各 1 個 prompt 範例。**

## 4. 跑模型
- 7 個模型：qwen38-27b‡、qwen36-35b、gemma4-12b‡、qwen35-9b、qwen35-4b、internvl35-1tile、llavaov2-8b。啟動參數同階段 4（Qwen 系列 max_pixels 307200、LLaVA-OV2 `IMG_MAX=560`、其他 900；Qwen `enable_thinking=false`）。
- served name 結尾 **`-devset5`**，port **8111–8119**；一張卡最多一個自己的 server；只用空閒記憶體（別人的程式和 Skyler 其他專案的程式都不要碰）；可平行；等卡上限 4 小時。
- **GPU（Skyler 11-19 授權）**：
  - 5090：**0 1 3 4 都可以用**（GPU 4 這次 Skyler 允許）。`GPUS` 預設 `0 1 3 4`。
  - **RTX 4080（GPU 5，16 GB，compute 8.9）**：只給 **qwen35-4b**（權重約 9 GB，是唯一可能放得下的模型），`NEED` 設 14000、`--max-model-len 16384`。先在 4080 上跑 smoke test；啟動失敗、OOM、或 smoke 不過，就改回只用 5090，寫進 DECISIONS。qwen35-4b 的 job 讓它在 `5` 和 5090 之間誰先空出來就用誰（`GPUS="5 0 1 3 4"`，NEED 仍 14000；在 5090 上照舊）。報告註明 qwen35-4b 實際用了哪張卡（不同 GPU 的數值結果可能有極小差異）。
  - **RTX 3070（GPU 2，8 GB）不使用**：7 個模型的權重最小約 9 GB，放不下；量化會換成不同的模型，不能和階段 3 比。寫進 DECISIONS。
  - 其他模型的 NEED / TP 同 `U/job4.sh` 的 CFG。
- 請求數：8 條件 × 216 題 × 3 順序 = **每個模型 5,184 個**，7 個模型共 36,288 個。沒有圖的條件每題少一張圖，比階段 3 快一點。
- smoke test（每個模型先跑 2 題 × 8 條件）：格式成功、prompt tokens 最大值 + 512 ≤ 16384、`cap_*` 的請求確實沒有參考圖。
- 跑的順序：每個模型先跑 `cap_g1`、`img_goldstyle`、`cap_g0`（最重要的比較），再跑其他。

## 4.5 SigLIP2 文字檢索基準線（不需要 vLLM，CPU 或任一張有空的卡都可以）
- 模型同階段 3：`R/models/siglip2-so400m-patch14-384`；候選圖片向量直接用 `T/siglip_emb.json`（不重算；同一個前處理）。
- 對 cap_g1 … cap_g5、cap_g5_nostyle 每一階，把 gold caption 組成一句英文，用 SigLIP2 的**文字編碼器**轉成向量（固定模板，寫在 `V/siglip_text.py` 與 DECISIONS），例如 g5：`a farmhouse/rustic style chair, made of wood, natural wood color, rectilinear shape`；g1：`a farmhouse/rustic style item`；g2：`a farmhouse/rustic style chair`。
- 兩種選法（和階段 3 的公平基準線一樣）：
  - `siglip2txt-top5`：和文字最像的 5 件候選；
  - `siglip2txt-mmr-std`：標準 MMR，λ = 0.7，相關度 = 文字–候選相似度，多樣性 = 候選–候選圖片相似度（同 `T/baselines.py` 的 siglip2-mmr-std）。
- cap_g0 沒有文字，不算（等於 Random）。SigLIP2 與候選順序無關，只存 o0。輸出 `V/out/<名稱>/select_<cond>_o0.jsonl`，格式同模型輸出。
- 報告的階梯表和折線圖都要加這兩條線，並和階段 3 的 siglip2-top5、siglip2-mmr-std（以圖找圖）並列。重點看：VLM 拿到正確 caption 後，是否明顯比 SigLIP2 的文字檢索好（如果差不多，表示 VLM 只是在做簡單的文字比對）。

## 5. 計分與報告
- `V/score5.py` → `V/results/scores5.json`、`.md`。計分定義同 `T/score.py`（Align@5、EffCov@5、Div@5、SameCat@5、Dup@5、失敗率；3 順序平均 ± 標準差；題目層級 bootstrap 95% CI，3 順序先在題內平均）。
- 另外加一個指標 **CopyQ@5**：選中的合格商品中，顏色和參考圖相同的比例、材質和參考圖相同的比例（分開報告）。用來看「給了參考圖的顏色、材質後，模型是不是往『找相似』而不是『找多樣』的方向走」。對照組（img、style_given）也要算。
- 表格（每個模型一列，S1、S2 分開；‡ 標出標註者模型）：
  1. **階梯表**：img、cap_g0 … cap_g5、cap_g5_nostyle 的 Align@5、EffCov@5。另外畫一張折線圖（x = 階，y = 分數，每個模型一條線；圖存 `V/results/ladder_S1.svg`、`ladder_S2.svg`）。
  2. **每一階的配對差**：g1−g0、g2−g1、g3−g2、g4−g3、g5−g4、g5−g5_nostyle、g1−img，附 95% CI，標出 CI 不含 0 的。
  3. **caption 寫錯的損失**：img_goldstyle − style_given（配對差 + CI），並依「模型自己寫的風格對不對」（`style.jsonl` 的 answer 是否 = 正確風格）把 108 個 query 分成兩組分開報告。預期：寫對的那組差距接近 0（這同時是檢查 prompt 有沒有寫錯）；寫錯的那組差距大。兩組各有幾題也要列。
  4. **找相似的傾向**：各條件的 CopyQ@5（顏色、材質）與 EffCov@5 並列。
  5. 和 pilot 階梯對照：用一小段文字比較這次與 `R/overnight_2026-11-16/results/ladder_compare.md` 的結論是否一致（pilot 是模型自己的 caption + 有圖、只有燈具、K=3，條件不同要寫明）。
- `V/REPORT_白話版.md`：寫法同 `T/REPORT_白話版.md`（白話、先講結論、名詞小字典、每段「為什麼 / 怎麼做 / 結果 / 代表什麼」、數字由腳本產生、限制、需要 Skyler 決定的事）。限制一定要寫：
  - 階梯的順序是固定的（風格 → 品項 → 材質 → 顏色 → 形狀），某一階的效果可能和加入順序有關；
  - S2 的任務句本來就有品項，所以 S2 的 g1 → g2 預期接近 0；
  - gold caption 的材質、顏色、形狀是三方多數決，不是人工標註；
  - qwen38-27b、gemma4-12b 也是標註者（‡）。
- 自我驗收：重跑計分結果相同；報告數字和 JSON 一致；7 × 8 × 3 × 216 全部完成（或失敗已記 0 分並列出失敗率）；無殘留 `-devset5` vLLM；沒寫受保護資料夾；`D/stage1/*.jsonl` 的 sha256 不變；T、U 的檔案沒被改。
- 全部完成後在 `V/PROGRESS.md` 最後一行寫 `ALL DONE`。

## 6. 限制
- 同階段 3、4 的全部限制；新檔只寫在 V，不修改 T、U、S、D 的其他檔案。
- 不呼叫 Claude 或任何付費 API，不使用 subagent。
- 只 kill 自己的 `-devset5` vLLM（記 PID），不用沒限定範圍的 `pkill -f`。
- 不自己加題型、條件或模型；不改題目。
- 不讀或印出 `~/.config/gemini_api_key`；不 git push；不發布 artifact。
