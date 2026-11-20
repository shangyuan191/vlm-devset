# 階段 2 DECISIONS（無人值守 agent 的判斷）

1. **共用程式**：`common2.py` 直接 import 階段 1 的 `common.py`（選項、SYSTEM_PROMPT、parse_lines），不複製、不改，確保 system prompt 與階段 1 逐字相同。理由：RUNBOOK 規定「一個字都不要改」。
2. **queue**：`make_queue.py` 依 RUNBOOK 3.1 建立（共 6,258 件，27 格）。id 在「發出」時才依該輪打亂後的順序編號（item_0901 起），縮圖也在發出時才做。
3. **Claude 一輪的取件數**：第 1 輪依 RUNBOOK 3.2 公式 take = max(20, ceil(還差正票 ÷ 正票率))，正票率 0 → 40，上限 = queue 剩餘。農舍 × 椅子（階段 1 正票率 3/30）因此取滿 270 件，是第 1 輪最大的一格；全輪共 1,362 件，以 $0.0092/件 約 $12.5。
4. **預算保護**：每次呼叫前檢查「累計花費 + $0.30 > $40」就停（單次 20 張約 $0.19–0.25），確保不會超過 $40。
5. **檢查點 1 的推估公式**：每件平均成本 ×（1,300 件主標註）+ 單一商品欄位（約 700 件 × 0.5 × 每件成本，粗估）；寫在 `checkpoint1.json`。
6. **合格條件實作**（`common2.qualified`）：完全照 RUNBOOK 第 2 節；標註失敗 = None = 不同意；wall_art 目標 13，其他 26。
7. **補標（3.4）**：qwen 等卡約 2 小時才排到（5090 被別人佔用），1,659 件三方標註完成後 25/27 格達標；只有 farmhouse_rustic×chandelier_pendant 與 boho×lamp 各差 3 件，各補一輪（Claude 目標 = ceil(差額 ÷ 實測確認率) + 2，至少 10 件正票換算，上限為 queue 剩餘；boho×lamp 的 queue 只剩 22 件）。已記在 `topup_rounds.json`。
8. **補標只送 Claude，再讓本地模型補標新 id**：新增商品 id 接在 item_1560 之後；本地模型重啟一次標新商品（annotate_local2 可續跑）。
