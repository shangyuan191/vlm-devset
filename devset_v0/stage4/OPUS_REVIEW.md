# 階段 4 審查報告（Opus 主控，2026-11-18）

## 一段話總結
**數字可以信。** 我用自己寫的程式（`review4/recheck.py`，不 import `score4.py` 或 `metrics.py`）從 `out/` 的原始輸出重算 3 個模型（qwen38-27b、internvl35-1tile、llavaov2-8b）× 3 種寫法 × 4 種題型的 Align@5 / EffCov@5，和 `results/scores4.json` 一致（例：qwen38-27b T4 tmpl_zh 原順序 Align 0.9037、EffCov 0.6733，兩邊相同）。388 題每題正確答案都是 12 件、自由維度 ≥ 2 個、`valid` 標記和限制條件一致。

**但「合成 query 讓分數變差」這個結論要小心解讀**（見第 2 點）。

## 檢查清單
| # | 檢查 | 結果 |
|---|---|---|
| 1 | 獨立重算分數 | 通過（3 模型 × 3 寫法 × 4 題型，全部一致） |
| 2 | 題目結構（正確答案 12 件、自由維度 ≥ 2、valid 標記） | 通過（0 個問題） |
| 3 | 合理性：Random < 模型、Oracle = 1 | 通過。T4：SigLIP2 top-5 Align 0.067、被陷阱騙 0.909，模型 0.46–0.90；T3：SigLIP2 0.547，模型 0.68–0.81 |
| 4 | 合成 query 的品質 | 388 題全部通過自動檢查；平均 8–9 個英文字 |
| 5 | **合成 query 條件的設計** | **有混淆因素，需要在報告中說明**（下面） |

## 主要發現：合成 query 的分數下降，大部分來自「沒有說要同風格」
- `texts4.py` 第 66–83 行：`tmpl_en` 的開頭寫「wants to find products in the **same style**」，任務句也寫「in the same style as the reference image」；`syn_en` 的開頭只寫「together with a shopping request」，任務句只放改寫後的句子。
- 改寫後的句子 **89% 沒有出現 style 這個字**，多半是「like this」「similar to this」「chairs like the one in this photo」。
- 以 qwen38-27b 為例，syn_en − tmpl_en 的 Align@5 差：
  - 句子**有**提到 style：S1 −0.045（22 題）、S2 −0.033（12 題）
  - 句子**沒有**提到 style：S1 −0.121（86 題）、S2 −0.098（96 題）、T3 −0.088（64 題）、T4 −0.168（107 題）
- **解讀**：真人說「像這個的」時，沒有講清楚「像」是指風格、還是外觀、品項或顏色；模型就不一定照風格挑，但我們仍用風格計分。所以這個條件測的是「**需求寫得模糊時，模型會不會自己推斷出要找同風格**」，而不只是「措辭不同」。
- 這本身是有意義的發現（真實 query 很少明講風格，C2：ESCI 家具 query 只有約 1.3% 帶風格字），但投影片和論文要這樣描述，不能說成「純粹換個說法就變差」。
- **建議（給 Skyler 決定）**：若要分開兩個因素，可以加一個條件「口語句 + 明講要同風格」（例如固定開頭「I want things in the same style as this photo:」），只跑 1–2 個模型就夠。

## 需要 Skyler 決定的事
1. 合成 query 要定位成「模糊需求」條件，還是補一個「口語 + 明講風格」的條件來拆開兩個因素？
2. （沿用階段 3）標註者 = 受測者（gemma4-12b、qwen38-27b 標 ‡）。

REVIEW DONE
