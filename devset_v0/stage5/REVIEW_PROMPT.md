# 階段 5 審查（Opus，無人值守）

你是主控 Opus。階段 5（正確 caption 階梯）已由 Sonnet agent 做完。V = `/mnt/raid0/home/skyler/vlm-diverse-retrieval/devset_v0/stage5/`。
Skyler 不會回答問題，不要呼叫 AskUserQuestion。**不要修改 V 裡 agent 產生的任何結果檔**；只新增 `V/review5/`（你的檢查腳本）和 `V/OPUS_REVIEW.md`。

**注意（11-20 Skyler 決定，USER_DECISIONS ⑬）**：「圖＋模型自己寫的風格」（style_given）和「圖＋正確風格」（img_goldstyle）都不再屬於主實驗；情境一、二的主實驗 = 只給參考圖（img）＋ caption 階梯 g0–g5、g5_nostyle。審查時不檢查也不報告這兩個條件。

## 要檢查的事
1. 讀 `V/RUNBOOK.md`、`PROGRESS.md`、`DECISIONS.md`、`REPORT_白話版.md`、`results/scores5.md`。
2. **prompt 對不對**：看 `V/logs/prompt_example_*.txt` 與 `V/run_caption.py`：
   - cap_* 真的沒有參考圖；caption 行數和維度順序符合 RUNBOOK 第 3 節；值是 gold（題目 `style`、`category`、`query` 的 material/color/shape）。
   - 任務句只把「參考圖片」改成「參考商品」。
3. **獨立重算**：自己寫 `V/review5/recheck.py`，直接從 `V/out/` 與 `T/questions.json` 重算每個模型 × 條件的 Align@5、EffCov@5（3 順序平均），和 `scores5.json` 比，差距 > 0.001 就列出。
4. **完整性**：7 模型 × 7 個 cap_* 條件 × 3 順序 × 216 題是否齊全（img_goldstyle 已依 USER_DECISIONS ⑬ 移出主實驗，有些模型有、有些沒有，不算缺漏，報告也不再列）；失敗率；SigLIP2 文字基準線是否存在。
5. **合理性檢查**：
   - cap_g0 應接近 Random 期望值（Align 約 0.30）。
   - S2 的 g2 − g1 應接近 0。
   - qwen35-4b 用了哪張卡；若用了 4080，抽 20 題在報告裡看 cap_g1 與其他模型相比是否有異常（只看，不重跑）。
6. 報告的結論有沒有超出數據（例如把不顯著的差異寫成結論）、限制是否寫齊（RUNBOOK 第 5 節列的四點）。

## 產出
`V/OPUS_REVIEW.md`（白話中文）：先一段結論，再逐項列「通過 / 問題 + 證據（檔案:行號或數字）」，最後「給 Skyler 的重點（3–5 點）」與「需要 Skyler 決定的事」。
最後一行只寫 `REVIEW DONE`（沒有重大問題）或 `REVIEW BLOCK`（有會影響結論的問題）。
