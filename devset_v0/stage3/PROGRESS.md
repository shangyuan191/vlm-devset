[2026-11-17 16:27] 階段3 開始 — 讀 RUNBOOK
[2026-11-17 16:35] A/Claude 第 5 輪完成 — 新增 1864 件累計 items；階段3 Claude 花費 $1.56；啟動本地標註
[2026-11-17 16:35] A/gemma4-12b — 等卡並啟動 vLLM（NEED 18000 × TP 2，port 8092，嘗試 1）
[2026-11-17 16:35] A/qwen38-27b — 等卡並啟動 vLLM（NEED 20000 × TP 2，port 8091，嘗試 1）
[2026-11-17 16:48] A/gemma4-12b — 完成，server 已關
[2026-11-17 17:12] A/qwen38-27b — 完成，server 已關
[2026-11-17 17:14] 階段3/A 完成 — 27/27 達標（合格 891），緩衝皆 ≥ 目標+4，industrial|chair single=yes ≥ 13；階段3 Claude 花費 $1.87（上限 $5）；analyze/make_report2/verify2 已重跑
[2026-11-17 17:14] 階段3/B 完成 — questions.json 216 題（108 query，boho|lamp 只有 3 個合格 query），0 題丟棄
[2026-11-17 17:14] C/qwen35-9b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8096，嘗試 1）
[2026-11-17 17:29] C/llavaov2-8b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8095，嘗試 1）
[2026-11-17 17:29] C/internvl35-1tile — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8094，嘗試 1）
[2026-11-17 17:29] C/qwen35-4b — 等卡並啟動 vLLM（NEED 18000 × TP 1，port 8097，嘗試 1）
[2026-11-17 17:29] C/qwen38-27b — 等卡並啟動 vLLM（NEED 20000 × TP 2，port 8091，嘗試 1）
[2026-11-17 17:29] C/gemma4-12b — 等卡並啟動 vLLM（NEED 18000 × TP 2，port 8092，嘗試 1）
[2026-11-17 17:29] C/qwen36-35b — 等卡並啟動 vLLM（NEED 22000 × TP 2，port 8093，嘗試 1）
[2026-11-17 17:31] C/qwen35-4b — 結束 exit 3（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-17 18:06] C/gemma4-12b — 結束 exit 3（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-17 18:19] C — 修正 run_*.py import 路徑，重排 qwen35-4b、gemma4-12b；SigLIP/Random/Oracle 基準線完成
[2026-11-17 18:19] C/qwen35-4b — 等卡並啟動 vLLM（NEED 18000 × TP 1，port 8097，嘗試 1）
[2026-11-17 18:19] C/gemma4-12b — 等卡並啟動 vLLM（NEED 18000 × TP 2，port 8092，嘗試 1）
[2026-11-17 18:24] C/smoke gemma4-12b — 10 題 × 1 順序，解析成功 10，prompt tokens 最大 12422、最小 12024
[2026-11-17 18:37] C/smoke qwen35-9b — 10 題 × 1 順序，解析成功 7，prompt tokens 最大 16380、最小 15201
[2026-11-17 18:38] C/qwen35-9b — 結束 exit 3（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-17 18:38] C — Qwen max_pixels 409600→307200（smoke 超過 16384），重排 qwen35-9b/4b/38-27b/36-35b
[2026-11-17 18:38] C/qwen35-9b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8096，嘗試 1）
[2026-11-17 18:38] C/qwen35-4b — 等卡並啟動 vLLM（NEED 18000 × TP 1，port 8097，嘗試 1）
[2026-11-17 18:38] C/qwen38-27b — 等卡並啟動 vLLM（NEED 20000 × TP 2，port 8091，嘗試 1）
[2026-11-17 18:38] C/qwen36-35b — 等卡並啟動 vLLM（NEED 22000 × TP 2，port 8093，嘗試 1）
[2026-11-17 18:41] C/smoke llavaov2-8b — 10 題 × 1 順序，解析成功 0，prompt tokens 最大 0、最小 0
[2026-11-17 18:42] C/llavaov2-8b — 結束 exit 3（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-17 18:42] C/llavaov2-8b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8095，嘗試 1）
[2026-11-17 18:44] C/smoke internvl35-1tile — 10 題 × 1 順序，解析成功 10，prompt tokens 最大 12339、最小 11888
[2026-11-17 19:55] C/internvl35-1tile — 完成，server 已關
[2026-11-17 19:55] D — 已更新 scores 與報告草稿（完成模型：internvl35-1tile；gemma4-12b 進行中）
[2026-11-17 19:57] C/smoke qwen35-9b — 10 題 × 1 順序，解析成功 10，prompt tokens 最大 13185、最小 12099
[2026-11-17 21:17] C/qwen35-9b — 完成，server 已關
[2026-11-17 21:18] D — 已更新 scores 與報告草稿（完成：internvl35-1tile、qwen35-9b）
[2026-11-17 21:19] C/gemma4-12b — 完成，server 已關
[2026-11-17 21:20] C/smoke qwen35-4b — 10 題 × 1 順序，解析成功 10，prompt tokens 最大 13185、最小 12099
[2026-11-17 21:21] C/smoke llavaov2-8b — 10 題 × 1 順序，解析成功 10，prompt tokens 最大 15157、最小 13008
[2026-11-17 22:08] C/smoke qwen36-35b — 10 題 × 1 順序，解析成功 10，prompt tokens 最大 13185、最小 12099
[2026-11-17 22:24] C/qwen35-4b — 完成，server 已關
[2026-11-17 22:25] D — 已更新 scores 與報告草稿（完成：internvl35-1tile、qwen35-9b、gemma4-12b、qwen35-4b）
[2026-11-17 22:30] C/llavaov2-8b — 完成，server 已關
[2026-11-17 22:34] C/smoke qwen38-27b — 10 題 × 1 順序，解析成功 10，prompt tokens 最大 13185、最小 12099
[2026-11-17 22:34] D — 已更新 scores 與報告草稿（完成 5/7；進行中：qwen36-35b、qwen38-27b）
[2026-11-18 00:18] C/qwen36-35b — 完成，server 已關
[2026-11-18 00:18] D — 已更新 scores 與報告草稿（完成 6/7；進行中：qwen38-27b）
[2026-11-18 01:41] C/qwen38-27b — 完成，server 已關
[2026-11-18 01:42] D — 7/7 模型完成；最終 score.py、REPORT_白話版.md、verify3.py 全部通過（Claude 階段 3 花費 $1.87）
ALL DONE
