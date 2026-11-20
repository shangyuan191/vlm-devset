# VLM 風格對齊 × 多樣選品：開發集 v0（dev set）

從 Amazon Reviews 2023 建立的家具家飾開發集，以及在上面跑的 VLM 實驗。任務：VLM 看一張參考商品圖，從 40 件候選中挑 5 件**同風格、而且其他屬性盡量多樣**的商品。

資料夾結構和原始工作目錄相同，所以程式裡的相對路徑都能對上：

| 路徑 | 內容 |
|---|---|
| `devset_v0/RUNBOOK.md`、`stage0/`、`stage1/` | 建商品池、每格試標 30 件（三方標註：Claude Opus 5.5、Qwen3.8-27B、gemma-4-12B） |
| `devset_v0/stage1/guideline_v1.md` | 三位標註者共用的標註準則（system prompt 全文的來源） |
| `devset_v0/stage2/` | 補標到每格湊滿合格數、單一商品欄位（`single_item_prompt.md`） |
| `devset_v0/stage3/` | 出題（情境一、二）、7 個 VLM 選品實驗、SigLIP2 基準線 |
| `devset_v0/stage4/` | Negation、多重限制題、合成 query（`gen_syn.py`、`gen_syn_claude.py`） |
| `devset_v0/stage5/` | 正確 caption 階梯、SigLIP2 文字檢索基準線（**快照：部分模型還在跑**） |
| `devset_v0/USER_DECISIONS.md` | 研究者的決定；各 stage 的 `DECISIONS.md` 是執行時的判斷紀錄 |
| `overnight_2026-11-14/D_main_table/metrics.py` | 計分（Align@5、EffCov@5、Div@5、Oracle、Random） |
| `overnight_2026-11-14/C1_category/c1_stats.py` | 品項與風格關鍵字規則 |

**沒有放進來的**：商品圖片（請依 Amazon Reviews 2023 的條款自行下載）、模型權重、執行 log、agent 對話紀錄、API 呼叫的花費紀錄。`stage*/out/` 只放了選品結果（`select_*.jsonl`），每筆含模型的原始輸出。
