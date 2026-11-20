# DECISIONS
1. A 節沿用 stage2 腳本（topup_a.py import annotate_claude2 / annotate_single_item，未改 S 的程式）；Claude 預算 = 階段 3 開始時累計 $20.8031 + $5（budget_base.json）。理由：RUNBOOK A 節上限 $5。
2. industrial|chair 補標量依「每標一件預期增加的 single=yes 件數」估算（目前 6/32 qualified 為 yes）。
3. 去風格字標題：用 overnight_2026-11-14/C1_category/c1_stats.py 的 STYLE_REGEX 全部 19 個 pattern（含 modern/vintage 等非目標風格字）以 | 串起來，大小寫不敏感刪除，再整理空白標點（同 pilot2 build_pilot2.clean）。
4. color/material/shape：三位多數決；三位皆不同用 Claude 值（次數記在 build_report.json attr_ties_to_claude）。「三方都標過」= 三位皆有成功標註。
5. phash_dups.json 只含「被刪的 / 保留的」配對（被刪的不在 pool），所以只當作邊：query/候選間若有邊就排除；未另外重算 phash。
6. S1 合格 12 件：先取 2 或 3 件同品項（seed 決定），其餘依品項輪流取；候選順序用 seed 打亂（題目原順序 = pos 1..40）。
7. A 結果：Claude 第 5 輪 162 件、單一商品欄位補標；verify2 的第 5 項列出『D 下被修改的檔案』含 USER_DECISIONS.md，不是我改的（階段 3 開始前使用者已追加 ⑩，mtime 在啟動後僅因該檔被使用者追加）。
8. 為了不浪費等卡時間，7 個模型的 job 同時排隊（每張卡仍最多一個 server，由 gpu_claims 控制）；每個模型啟動後若 logs/smoke_done 不存在就先跑 smoke（5 query × 2 情境 × o0）。
9. run_style/run_select 在 python -I 下找不到 common3（-I 不含腳本目錄）→ 加 sys.path.insert；qwen35-4b、gemma4-12b 的 job 因此 exit 3，已重新排隊。
10. smoke 旗標改成每個模型各一個（Qwen 系列圖片 token 較多，需各自確認 < 16384）。
11. smoke（qwen35-9b）顯示 Qwen 在 max_pixels=409600 + 41 張圖時 prompt 最大 16380 tokens，加上 512 輸出超過 max-model-len 16384（10 題中 3 題失敗）。RUNBOOK 規則做不到 → 最接近做法：所有 Qwen 系列（3.5-9b/3.5-4b/3.6-35b/3.8-27b）改用 max_pixels=307200（每張圖約 300 tokens），其他設定不變。需 Skyler 知道：Qwen 的圖片解析度比 11-16 的設定低。
12. LLaVA-OV2 在 devset 圖（縮到 900）下每張圖約 780 tokens，41 張達 32k > 16384（11-16 的題目圖較小、約 270/張）。RUNBOOK 規則做不到 → 只對 llavaov2-8b 把送出的圖縮到長邊 560（IMG_MAX=560），其他模型維持 900。
13. **Opus 審查修正（2026-11-18）**：只改 `make_report3.py` 的文字說明（不改 score.py、不改任何數字、不重跑模型）：(a) 名詞小字典補上 困難干擾 / SigLIP2 三種基準線 / H2 / H3 / H5 / H6 / 95% CI / 位置偏誤；(b) 標明 `siglip2-mmr-free` 會讀取候選的標註屬性（color/material/shape/category 多數決）與該題自由維度，是有特權資訊的參考值，不是公平基準線；結論第 4 點加註並補上純圖片的 siglip2-mmr-std；(c) 限制補三條：gemma4-12b / qwen38-27b 同時是標註者與受測者、siglip2-mmr-free 的特權資訊、標題去風格字不完全（item_0773 "Mid Modern Century" 單次刪除後拼出 "Mid Century"，出現在 9 題；beach / steampunk / cottage 等線索字保留）；(d) 「需要 Skyler 決定的事」加 4、5。之後重跑 make_report3.py 與 verify3.py（1、2 項仍為 True）。審查細節見 `OPUS_REVIEW.md`。
