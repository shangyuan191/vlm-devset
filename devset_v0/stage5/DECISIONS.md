# 階段 5 DECISIONS
1. 題目／候選／順序全部沿用 T/questions.json；o1、o2 用 `random.Random(f'stage3-{order}-{qid}')` 打亂，與 run_select.py 相同。
2. `img_goldstyle` 任務句保留「參考圖片」（和 style_given 逐字相同，只換 style_line，RUNBOOK 3.1 第一點；§3.1 的「參考圖片→參考商品」只套用在沒有圖的條件）。理由：要和 style_given 做配對比較，prompt 必須只差一行風格。
3. gold caption 的品項用題目 category 原文（chair、table、lamp、chandelier/pendant）；值一律英文原文。
4. GPU 2（3070，8GB）不使用：7 個模型權重最小約 9GB 放不下，量化會變成不同模型，不能和階段 3 比。
5. qwen35-4b NEED 14000、GPUS='5 0 1 3 4'（誰先空出來用誰；4080 目前被他人佔用 9.5GB，放不下就等 5090）。實際用的卡報告中註明。
6. SigLIP2 文字模板見 siglip_text.py 檔頭（g1 `a {style} style item` … g5 `…, made of {material}, {color} color, {shape} shape`；chandelier/pendant 寫成 `chandelier pendant light`）。文字編碼 padding=max_length、max_length=64；候選圖向量用 stage3/siglip_emb.json。
7. 其他 5 個模型第一輪等卡超過 4 小時（GPU 被他人佔用，且 qwen35-9b/4b 佔住兩張）→ job 迴圈自動重試（最多 4 次）；qwen35-9b/4b 跑完會釋放卡。
8. 不降低 llavaov2 的 NEED（8B bf16 權重約 17GB，16384 長度的 KV 約 2.4GB，降到 22000 以下會不穩）；繼續等卡。
9. 三個模型 4 次（每次等 4 小時）沒等到卡，依主控指示重啟迴圈再等 4 輪；等卡期間不碰別人的卡。
