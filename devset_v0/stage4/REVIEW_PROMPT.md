# 主控審查：階段 3 結果（由 Opus 執行，無人值守）

你是主控（Opus），負責**審查**無人值守 agent（Sonnet）做完的階段 3，並決定階段 4 能不能照原計畫開始。Skyler 在睡覺，不會回答問題，不要呼叫 AskUserQuestion。
R = `/mnt/raid0/home/skyler/vlm-diverse-retrieval/`，T = `R/devset_v0/stage3/`，U = `R/devset_v0/stage4/`。

## 要做的事
1. 讀 `T/RUNBOOK.md`、`T/PROGRESS.md`、`T/DECISIONS.md`、`T/REPORT_白話版.md`、`T/results/`、`T/build_report.json`。
2. 抽查（自己寫小段 Python，**唯讀**，暫存檔放 `U/review_tmp/`）：
   - 每個模型 × 條件 × 情境 × 順序的完成題數、失敗率；失敗率 > 10% 的要看 raw_output 找原因。
   - 用 `T/out/` 的原始輸出 + `T/questions.json` **自己獨立重算**至少 2 個模型的 Align@5 / EffCov@5（S1、S2 各一），和 `T/results/scores.json` 比對。
   - 合理性：Random < 模型、Oracle = 1；SigLIP2 基準線數字合理；位置偏誤是否嚴重；Style Acc 是否合理；有沒有哪個模型的輸出明顯異常（例如全部選 1–5）。
   - prompt 中有沒有洩漏風格名稱（img 條件不可以有；style_given 只能在那一行）。
   - 報告數字和 JSON 是否一致；報告有沒有把術語解釋清楚。
3. 發現問題時：
   - **計分 / 報告的錯**：直接修 T 的計分或報告腳本並重跑（不重跑模型），在 `T/DECISIONS.md` 追加一條「Opus 審查修正」。
   - **需要重跑模型的錯**（例如 prompt 錯了）：不要自己跑；寫進審查報告，並在「階段 4 要注意」裡寫清楚要階段 4 agent 順便補跑什麼。
   - 會影響階段 4 設計的發現（例如 prompt 太長、某模型完全不能用應該排除、某種題目設計有漏洞）：寫進「階段 4 要注意」。可以小幅修改 `U/RUNBOOK.md`，但要在檔案最上面加一段「Opus 審查後修改」說明改了什麼、為什麼。**不要改變 Skyler 已決定的事**（USER_DECISIONS、題型範圍、不跑付費模型）。
4. 寫 `T/OPUS_REVIEW.md`（中文、白話，給 Skyler 看）：
   - 一段話總結：這一輪的結果能不能信、最重要的 3 個發現（用數字，附來源檔）。
   - 檢查清單：每項檢查做了什麼、結果（通過 / 有問題 / 已修正）。
   - 「階段 4 要注意」：給階段 4 agent 的具體指示（沒有就寫「無」）。
   - 「需要 Skyler 決定的事」。
5. 最後一行寫 `REVIEW DONE`（階段 4 才會啟動）。如果發現**嚴重問題導致階段 4 不應該開始**（例如出題邏輯錯誤會讓結果全部無效），最後一行改寫 `REVIEW BLOCK`，並寫清楚原因；看守程式就不會啟動階段 4。

## 限制
- 不跑任何模型、不啟動 vLLM、不呼叫 Claude 標註或任何付費 API、不使用 subagent、不發布 artifact、不 git push。
- 不修改 `D/stage0`、`D/stage1`、`S/`、`D/USER_DECISIONS.md`，以及 `R/pilot*`、`R/overnight_*`、`R/smoke_*`、`R/models/`、既有的 `R/data/`。
- 審查要有效率：重點是找出會讓結論錯的問題，不是重寫報告。
