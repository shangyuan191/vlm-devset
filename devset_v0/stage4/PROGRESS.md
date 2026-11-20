[2026-11-18 01:51] 0 開始 — 已複製 T 腳本到 U（common3/run_select/run_style/score/baselines/serve/job/tasks/verify/make_report/build_questions）
[2026-11-18 01:52] 2 出題 — questions4.json 完成：T4 108、T3 64（23 組合/16 格）、S1/S2 沿用 216；dropped 3 個 T3 query 已換人（見 build_report4.json）
[2026-11-18 01:54] C/qwen38-27b — 等卡並啟動 vLLM（NEED 20000 × TP 2，port 8101，嘗試 1）
[2026-11-18 01:55] C/gemma4-12b — 等卡並啟動 vLLM（NEED 18000 × TP 2，port 8102，嘗試 1）
[2026-11-18 01:55] C/qwen36-35b — 等卡並啟動 vLLM（NEED 22000 × TP 2，port 8103，嘗試 1）
[2026-11-18 01:55] C 啟動 — 7 個模型 job 已排隊（launch_models.sh；qwen38-27b 先做 gen_syn）
[2026-11-18 01:55] C/qwen35-9b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8106，嘗試 1）
[2026-11-18 01:56] C/internvl35-1tile — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8104，嘗試 1）
[2026-11-18 01:56] C/llavaov2-8b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8105，嘗試 1）
[2026-11-18 01:56] C/qwen35-4b — 等卡並啟動 vLLM（NEED 18000 × TP 1，port 8107，嘗試 1）
[2026-11-18 01:59] C/smoke qwen35-9b — 12 題，解析成功 12，prompt tokens 最大 13066（+512 = 13578，上限 16384）、最小 12451
[2026-11-18 02:03] 3 基準線 — baselines.py 完成（Random/Oracle/SigLIP2 ×4 題型）；score4.py、verify4.py 已寫好並試跑
[2026-11-18 02:14] C 調整 — tasks_run4.sh：syn 文字未完成時 exit 4 釋放 GPU（避免卡位）；relaunch.sh 可補排隊
[2026-11-18 02:57] C/qwen35-9b — 結束 exit 143（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-18 02:58] C/qwen35-9b — tmpl_zh、tmpl_en 完成（手動停掉等待合成 query 的舊版 task，釋放 GPU；syn_en 待補跑，用 relaunch.sh）
[2026-11-18 03:00] C/smoke qwen35-4b — 12 題，解析成功 12，prompt tokens 最大 13066（+512 = 13578，上限 16384）、最小 12451
[2026-11-18 03:46] C/qwen35-4b — tmpl_zh、tmpl_en 完成，syn_en 等合成 query（釋放 GPU）
[2026-11-18 03:46] C/qwen35-4b — 結束 exit 4（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-18 03:48] C/qwen35-4b — 等卡並啟動 vLLM（NEED 18000 × TP 1，port 8107，嘗試 2）
[2026-11-18 03:49] C/smoke internvl35-1tile — 12 題，解析成功 12，prompt tokens 最大 12172（+512 = 12684，上限 16384）、最小 12031
[2026-11-18 03:49] C/qwen35-4b — 停掉重試迴圈（syn_en 待合成 query 後用 relaunch.sh 補跑）
[2026-11-18 04:36] C/internvl35-1tile — tmpl_zh、tmpl_en 完成，syn_en 等合成 query（釋放 GPU）
[2026-11-18 04:36] C/internvl35-1tile — 結束 exit 4（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-18 04:38] C/internvl35-1tile — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8104，嘗試 2）
[2026-11-18 04:38] C/smoke llavaov2-8b — 12 題，解析成功 12，prompt tokens 最大 14976（+512 = 15488，上限 16384）、最小 13129
[2026-11-18 04:40] C/internvl35-1tile — tmpl_zh、tmpl_en 完成，停掉重試迴圈（syn_en 待合成 query 後 relaunch.sh）
[2026-11-18 05:25] C/llavaov2-8b — tmpl_zh、tmpl_en 完成，syn_en 等合成 query（釋放 GPU）
[2026-11-18 05:25] C/llavaov2-8b — 結束 exit 4（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-18 05:25] C/llavaov2-8b — 停掉重試迴圈（syn_en 待合成 query 後 relaunch.sh）
[2026-11-18 05:33] C/smoke gemma4-12b — 12 題，解析成功 12，prompt tokens 最大 12333（+512 = 12845，上限 16384）、最小 12125
[2026-11-18 05:54] C/qwen38-27b — 結束 exit 2（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-18 05:55] C/qwen36-35b — 結束 exit 2（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-18 05:56] C/qwen38-27b — 等卡並啟動 vLLM（NEED 20000 × TP 2，port 8101，嘗試 2）
[2026-11-18 05:57] C/qwen36-35b — 等卡並啟動 vLLM（NEED 22000 × TP 2，port 8103，嘗試 2）
[2026-11-18 07:32] C/gen_syn — 合成 query 完成（主控改用 Claude Sonnet 5.5，gen_syn_claude.py；388/388 通過，$0.86）；請 relaunch 等待 syn_en 的模型
[2026-11-18 07:32] C/qwen35-9b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8106，嘗試 1）
[2026-11-18 07:32] C/internvl35-1tile — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8104，嘗試 1）
[2026-11-18 07:33] C/llavaov2-8b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8105，嘗試 1）
[2026-11-18 07:33] C/qwen35-4b — 等卡並啟動 vLLM（NEED 18000 × TP 1，port 8107，嘗試 1）
[2026-11-18 08:03] 報告 — 依主控決定（syn_en 改用 Claude 改寫）更新 make_report4.py / score4.py 文字
[2026-11-18 08:24] C — Skyler 要求讓出 GPU 3：主控停掉 gemma4-12b（syn_en 已完成 107/388，會續跑）與所有等卡中的 job；serve_devset4.sh 預設 GPU 改為 0 1 4；之後一律用 resume.sh 重新排隊（不要用 GPU 3，除非 Skyler 允許）
[2026-11-18 08:24] C/qwen38-27b — 等卡並啟動 vLLM（NEED 20000 × TP 2，port 8101，嘗試 1）
[2026-11-18 08:24] C/gemma4-12b — 等卡並啟動 vLLM（NEED 18000 × TP 2，port 8102，嘗試 1）
[2026-11-18 08:24] C/qwen36-35b — 等卡並啟動 vLLM（NEED 22000 × TP 2，port 8103，嘗試 1）
[2026-11-18 08:24] C/qwen35-9b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8106，嘗試 1）
[2026-11-18 08:25] C/internvl35-1tile — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8104，嘗試 1）
[2026-11-18 08:25] C/llavaov2-8b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8105，嘗試 1）
[2026-11-18 08:30] C — 更正：admin 說的是 CUDA 3 = nvidia-smi / PCI 的 GPU 4。主控停掉 GPU 4 上的 qwen35-4b（syn_en 217/388，會續跑）與等卡 job；預設 GPU 改為 0 1 3；重新排隊用 resume.sh。**不要用 GPU 4**
[2026-11-18 08:30] C/qwen38-27b — 等卡並啟動 vLLM（NEED 20000 × TP 2，port 8101，嘗試 1）
[2026-11-18 08:30] C/gemma4-12b — 等卡並啟動 vLLM（NEED 18000 × TP 2，port 8102，嘗試 1）
[2026-11-18 08:31] C/qwen36-35b — 等卡並啟動 vLLM（NEED 22000 × TP 2，port 8103，嘗試 1）
[2026-11-18 08:31] C/internvl35-1tile — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8104，嘗試 1）
[2026-11-18 08:31] C/llavaov2-8b — 等卡並啟動 vLLM（NEED 24000 × TP 1，port 8105，嘗試 1）
[2026-11-18 08:31] C/qwen35-4b — 等卡並啟動 vLLM（NEED 18000 × TP 1，port 8107，嘗試 1）
[2026-11-18 08:50] C/qwen35-9b — 完成，server 已關
[2026-11-18 09:12] C/llavaov2-8b — 完成，server 已關
[2026-11-18 09:24] C/qwen35-4b — 完成，server 已關
[2026-11-18 09:46] C/internvl35-1tile — 完成，server 已關
[2026-11-18 10:24] C/gemma4-12b — 完成，server 已關
[2026-11-18 10:35] C/smoke qwen38-27b — 12 題，解析成功 12，prompt tokens 最大 13066（+512 = 13578，上限 16384）、最小 12451
[2026-11-18 12:31] C/qwen36-35b — 結束 exit 2（2 = 等卡超過 4 小時；1 = 啟動或工作中斷）
[2026-11-18 12:33] C/qwen36-35b — 等卡並啟動 vLLM（NEED 22000 × TP 2，port 8103，嘗試 2）
[2026-11-18 13:53] C/qwen38-27b — 完成，server 已關
[2026-11-18 13:57] C/smoke qwen36-35b — 12 題，解析成功 12，prompt tokens 最大 13066（+512 = 13578，上限 16384）、最小 12451
[2026-11-18 16:54] C/qwen36-35b — 完成，server 已關
[2026-11-18 16:54] C — 7/7 模型完成
[2026-11-18 16:56] D — 最終 score4.py、REPORT_白話版.md、verify4.py 全部通過（Claude 只用於 syn_en 改寫，由主控執行）
ALL DONE
