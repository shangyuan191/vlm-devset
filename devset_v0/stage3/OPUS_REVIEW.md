# 階段 3 審查報告（Opus 主控，2026-11-18 01:44 UTC 開始，無人值守）

## 一段話總結
**這一輪的數字可以信，階段 4 可以照計畫開始。** 我用自己寫的程式（不 import `metrics.py`、`score.py`）從 `out/` 的原始輸出重算，3 個模型 × 2 條件 × 2 情境的 Align@5 / EffCov@5 和 `results/scores.json` **完全一樣**（差 0）；216 題的 Oracle 也自己窮舉一次，全部 = 1.00。7 個模型共 9,072 次選品請求只失敗 2 次，沒有被截斷的輸出。
最重要的 3 個發現：
1. **告訴模型風格名稱，S1 的「選對率」大幅上升**：例如 gemma4-12b 的 S1 Align@5 從 0.694 → 0.918，qwen38-27b 0.805 → 0.909；7 個模型 style_given − img 的差都在 +0.07～+0.14，95% CI 都不含 0。代表模型多半「認得出風格」，但只看圖選品時沒好好用上（H5 成立的跡象）。（`results/scores.json` → `models.*.H5`）
2. **在 S2（同風格 + 同品項），大模型幾乎沒贏過「純圖片相似度」**：純 SigLIP2 top-5 的 S2 EffCov@5 = 0.661，最好的模型 qwen35-9b 0.674、qwen38-27b 0.664。S1 才有明顯差距（qwen38-27b 0.581 vs SigLIP2 0.448）。另外報告原本拿來對照的「SigLIP2 + 輪流 MMR」（S2 0.740，比所有模型都高）**其實偷看了標註答案的屬性**，不是公平對手——我已在報告中標註 †。（`results/scores.json` → `baselines`；`baselines.py` 第 72–78 行）
3. **S1 中模型很「黏」參考圖的品項**：挑出的 5 件中和參考圖同品項的比例 0.48～0.70，但合格候選中只有 0.203、Oracle 解只有 0.215（H3）。也就是叫它「品項盡量不同」，它還是偏向挑同一種東西。（`results/scores.json` → `samecat_ref`、`models.*.img|S1.SameCat`）

另外要記得：**gemma4-12b 和 qwen38-27b 同時是出題用的標註者和受測模型**（`stage2/ann_gemma4-12b.jsonl`、`ann_qwen38-27b.jsonl`），query 圖必須是它們也標對風格的圖，所以這兩個模型的分數可能偏高。

## 檢查清單
| # | 檢查 | 怎麼做 | 結果 |
|---|---|---|---|
| 1 | 完成題數、失敗率 | 讀每個模型 6 個 select 檔 + style.jsonl，數筆數、status、attempt、finish_reason（`stage4/review_tmp/checks.py`） | **通過**。每個模型 × 條件 × 情境 × 順序都是 108/108、qid 不重複。失敗只有 2 筆（gemma4-12b style_given 1、qwen35-4b img 1），失敗率 ≤ 0.3%，沒有 > 10% 的格子。finish_reason 全是 stop（沒有被截斷）。風格判斷只有 qwen35-4b 1 題失敗（回答 "rustic"，不在選項中），因此它的 style_given 有 6 筆沒給風格行（`style_given_missing`），影響極小。 |
| 2 | 獨立重算 Align@5 / EffCov@5 | 自己寫計分（合格 = 風格相同，S2 再加品項相同；自由維度 = 合格 12 件中 ≥ 2 種值），算 qwen38-27b、internvl35-1tile、llavaov2-8b 的 S1、S2、img、style_given（`stage4/review_tmp/recompute.py`） | **通過**。12 個數字全部和 `scores.json` 相同（差 0 或 2e-16）。順便確認候選的 `valid` 標記和我自己判斷的合格一致、每題合格剛好 12 件。 |
| 3 | Oracle = 1、Random < 模型 | 自己窮舉每題合格 12 選 5 | **通過**。216/216 題 Oracle EffCov@5 = 1.00。Random 平均 EffCov 0.358，低於所有模型（最低 internvl35-1tile 0.508）。 |
| 4 | 打亂順序的位置換算 | 用同一個 seed 重排 o1 / o2，檢查 shown_positions → selected_positions | **通過**。0 筆換算錯。 |
| 5 | SigLIP2 基準線 | 讀 `baselines.py`、比數字 | **有問題 → 已在報告修正說明**。top-5（0.554）和標準 MMR（0.580）合理。但 `siglip2-mmr-free` 用候選的**標註屬性**（color/material/shape/category）和該題自由維度來輪流挑，這是模型拿不到的資訊；報告原本把它當一般對照。已在報告標 †、加入名詞解釋與限制，數字沒改。 |
| 6 | 位置偏誤、輸出異常 | 統計選中位置、連續 5 格、最常見組合 | **大致通過**。隨機時「選到第 1 位」約 0.125；6 個模型在 0.10～0.16，正常。**llavaov2-8b 偏誤明顯**：第 1 位 0.30，img 條件 30/648 次直接選 [1,2,3,4,5]（S1 8.3%）。沒有模型「全部選 1–5」。部分 Qwen 在 style_given 時偏好前 10 位（最高 41%，隨機約 25%），輕微。 |
| 7 | Style Acc 合理性 | 看 per-style 正確率與常見錯誤 | **合理，但有偏差來源**。多數 0.89～0.96；internvl35-1tile 0.694 明顯較差（bohemian 0.46）。常見錯誤合理（mid-century → glam / modern minimalist）。注意 gemma4-12b（0.963）、qwen38-27b（0.935）是標註者，query 是它們也標對的圖，分數有選擇偏差。 |
| 8 | prompt 洩漏風格名稱 | 讀 `run_select.py` / `run_style.py`；掃描 8,640 個候選標題（`stage4/review_tmp/leak.py`、`leak2.py`） | **大致通過，有 1 個小漏洞**。任務句與說明沒有風格名稱；style_given 的風格只出現在那一行；query 的標題不送進 prompt。標題中 6 個目標風格名稱只殘留 1 件：item_0773 原標題 "Mid **Modern** Century"，regex 刪掉 Modern 後拼成 "Mid Century"（出現在 9 題，其中 4 題它是合格候選）。影響很小，不需重跑。另外 beach（205 次）、steampunk（116）、country / cottage、barn、antique 等「風格線索字」照規則沒有刪——這是設計層面的問題，交給 Skyler 決定。 |
| 9 | 解析度偏離是否一致 | 看每個模型 style / select 的 prompt tokens 與時間 | **通過**。4 個 Qwen 模型的正式資料都是在改成 max_pixels 307200 之後跑的（style prompt tokens 都是 675–847，選品最大 13374）；llavaov2-8b 最大 15855 + 512 < 16384。舊設定的 smoke 輸出在獨立的 `select_smoke_*` 檔，沒被計分。 |
| 10 | 報告數字與 JSON 一致、術語解釋 | 讀 `make_report3.py`（數字全由 JSON 產生）、重跑 `verify3.py` | **數字通過；術語已修正**。原本名詞小字典沒有解釋 H2 / H3 / H5 / H6、SameCat、Dup、CI、困難干擾、三種 SigLIP2 基準線，已補上。修改後重跑 `make_report3.py`、`verify3.py`：「重跑 score.py 結果不變」與「報告數字由 JSON 產生」都仍為 True。修改記在 `DECISIONS.md` 第 13 條。 |
| 11 | 受保護資料 | verify3 第 5、6 項 | **通過**。stage1 sha256 不變；受保護資料夾沒有新修改。 |

## 階段 4 要注意（給階段 4 agent；已同步寫在 `stage4/RUNBOOK.md` 最上面）
1. **解析度照階段 3**：Qwen 系列 max_pixels = 307200、llavaov2-8b `IMG_MAX=560`，其他 900。複製 T 的 `serve_devset3.sh`、`tasks_run.sh` 再改成 `-devset4`、port 8101–8109。
2. **smoke 標準**：prompt tokens 最大值 + 512 ≤ 16384（不是只 < 16384）。llavaov2-8b 階段 3 已到 15855，T3 / T4 若候選標題較長要特別看它。
3. **去風格字標題反覆刪到不變**（修 "Mid Modern Century" 這類拼接）。只用在 T3 / T4 新題；S1 / S2 沿用 `T/questions.json`，不重建、不重跑階段 3 的 tmpl_zh 結果。syn_en 的 STYLE_REGEX 檢查同樣用「反覆刪到不變後再檢查有沒有命中」的方式（等同：原句不可命中任一 pattern，且刪除後也不可命中）。
4. **siglip2-mmr-free 標 †**（使用標註屬性，非公平基準線）；報告結論的「對照」要以 siglip2-top5、siglip2-mmr-std 為主。
5. **標註者模型標 ‡**：gemma4-12b、qwen38-27b 在所有主表加 ‡ 並寫進限制；qwen38-27b 也是 syn_en 改寫者，它的 syn_en 分數要提醒「自己改寫、自己作答」。
6. **不需要補跑階段 3 的任何模型請求**（沒有發現需要重跑的錯）。
7. 風格判斷失敗時 style_given 不給風格行的做法可以沿用（階段 4 本來就不跑 style_given）。

## 需要 Skyler 決定的事
1. （階段 3 agent 已提）Qwen / LLaVA-OV2 解析度偏離要不要接受，或調大 `--max-model-len` 重跑。我的建議：**先接受**——目前所有模型 prompt 都塞得進、輸出沒截斷；論文正式版再決定。
2. （階段 3 agent 已提）教授對 ③ 的意見回來後是否重新出題。
3. （階段 3 agent 已提）要不要人工確認 108 張 query 圖的風格。
4. **（新）標註者 = 受測者**：gemma4-12b、qwen38-27b 既幫忙決定「正確答案」，又被拿來考。建議論文主表標出來，或用人工確認過的子集另算一版；長期可考慮換掉其中一位標註者。
5. **（新）標題中的風格線索字**（beach、steampunk、cottage、barn、antique…）要不要也刪，或加一個「不給標題、只給圖」的條件，才知道 S1 的分數有多少是靠讀字。這是改設計，所以沒有自己動。
6. **（新）S2 大模型 ≈ 純圖片相似度**（0.66 vs 0.661）：S2 可能太容易用「長得像」解決，若要讓 S2 有鑑別力，可能需要更難的干擾項（例如同品項、外型很像但不同風格）。

REVIEW DONE
