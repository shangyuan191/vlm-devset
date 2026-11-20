# 開發集 v0：階段 4 報告（Negation、多重限制、合成 query）

> 本報告所有數字由腳本從 `results/scores4.json`、`build_report4.json`、`query_texts.json` 產生。已全部跑完的模型：7/7（qwen38-27b‡, qwen36-35b, gemma4-12b‡, qwen35-9b, qwen35-4b, internvl35-1tile, llavaov2-8b）；有部分資料的：無。

## 先講結論

1. **T4「同風格但不是這個品項」**：7 個模型的 Align@5（5 件裡真正符合的比例）qwen38-27b‡ 0.898（最高）、llavaov2-8b 0.459（最低）；純圖片相似度（SigLIP2 top-5）只有 0.067，隨機 0.300。純看「長得像」會被陷阱（同風格同品項、但題目說不要）騙：SigLIP2 的 Trap@5 = 0.909（隨機 0.300）。模型的 Trap@5：qwen36-35b 0.005（最低）、llavaov2-8b 0.220（最高）。
2. **T3「同風格 + 同品項 + 指定顏色 / 材質」**：模型的 Align@5 qwen38-27b‡ 0.811（最高）、internvl35-1tile 0.677（最低）；SigLIP2 top-5 0.547。屬性陷阱（風格對、品項對、但顏色 / 材質不是指定值）被選中的比例 qwen38-27b‡ 0.081（最低）、llavaov2-8b 0.223（最高）；SigLIP2 top-5 0.403。
3. **query 圖本身的屬性等不等於指定值**會影響 T3：query 屬性 = 指定值（例如參考圖就是木頭、要求木頭）時，模型平均 Align@5 = 0.776；不等於（參考圖是金屬、卻要木頭）時 = 0.726。
4. **措辭（合成 query vs 英文模板句）**：28 個「模型 × 題型」格子中，syn_en − tmpl_en 的 EffCov@5 差：顯著變好 0、顯著變差 14、看不出差別 14（95% CI 是否含 0）；平均差 -0.042。（syn_en 由 Claude Sonnet 5.5 改寫，不是受測模型，沒有「自己改寫自己作答」的問題。）
5. **注意**：gemma4-12b‡、qwen38-27b‡ 同時是出題用的標註者；siglip2-mmr-free† 會讀候選的標註屬性，不是公平基準線（公平的純圖片對照是 siglip2-top5、siglip2-mmr-std）。

## 名詞小字典

- **T3 多重限制**：同風格 + 同品項，再加一個屬性限制（顏色或材質等於某個值），例如「這個風格的椅子，要布面的」。
- **T4 Negation**：同風格，但**不要**某個品項（query 圖的品項），例如「我已經有這張椅子，要同風格但不是椅子的東西」。
- **S1 / S2**：階段 3 的兩種題：S1 只限風格；S2 限風格 + 同品項。本階段只補跑新的措辭，沿用階段 3 的題目。
- **Align@5**：模型挑的 5 件中「真的符合所有限制」的比例。
- **Div@5**：符合限制的那幾件，在「可以不同的維度」（顏色、材質、形狀、T4 還有品項）上有多分散；只算符合件數 ≥ 2 的題。
- **EffCov@5**：主指標：同樣看分散度，但分母固定用 5 件，所以選到不符合的件會被扣分；1.00 = 滿分。
- **Trap@5（陷阱）**：T4：5 件中選到「同風格、同品項」（題目說不要的那種）的比例。T3 分兩種：屬性陷阱 = 風格 / 品項對、但顏色或材質不是指定值（或補位商品）；風格陷阱 = 品項 / 屬性對、但風格不對。越低越好；隨機的期望值就是該桶佔 40 件的比例。
- **tmpl_zh / tmpl_en / syn_en**：三種 query 寫法：中文模板句、英文直譯模板句、由 Claude Sonnet 5.5 改寫成真人購物語氣的英文需求句（RUNBOOK 原訂本地 Qwen3.8-27B，因等不到 2 張 GPU 改用，見 DECISIONS）。
- **SigLIP2 三種基準線**：siglip2-top5 = 只挑和 query 圖最像的 5 件；siglip2-mmr-std = 標準 MMR（相似又不重複，只用圖片）；**siglip2-mmr-free† = 依標註屬性輪流挑，偷看了答案相關資訊，不是公平基準線**。
- **‡ / †**：‡ = 該模型同時是出題標註者（分數可能偏高）；† = 非公平基準線。
- **95% CI**：題目層級 bootstrap（重抽 10,000 次）的 95% 信賴區間；區間不含 0 才表示差距比較可信。
- **o0 / o1 / o2**：候選順序：o0 = 原順序，o1、o2 = 兩種打亂；±是三種順序的標準差。

## 1. 出題結果（`build_questions4.py` → `questions4.json`、`build_report4.json`）

- 可用合格商品 881 件（沿用階段 3「三方都標過」規則；`stage2/qualified.jsonl` 的 891 件中有 10 件缺一位標註者，排除）。
- **T4 Negation：108 題**（用階段 3 的 108 個 query；全部 |自由維度| = {'4': 108}，Oracle EffCov@5 = 1.00）。
- **T3 多重限制：64 題**，來自 23 個可出題組合 / 16 個格子（規則：該格 a = v 件數 ≥ 12、排除比例 ≥ 30%、另兩個屬性各 ≥ 2 種值）；同一組合內 query 不重複，共 59 個不同 query。主控 11/17 用 891 件試算是 25 組合 / 17 格，我用 881 件實算是 23 / 16。
- T3 補位與放寬（記在 `build_report4.json` → `relaxed`）：17 題有補位 / 放寬（屬性陷阱不足改用「風格 X 其他品項、a = v」補；風格陷阱不足改為 a 任意）；被換掉的 query（該 query 自己在該組合建不出題）3 次。
- 沿用階段 3 的 S1、S2 各 108、108 題；T3、T4 的標題去風格字改為**反覆刪到不再變**（修掉 "Mid Modern Century" 這類拼接）；S1 / S2 沿用原標題以保持可配對。

### T3 可出題組合

| 格子 | 屬性 | 值 | 該格符合件數 / 合格數 | 排除比例 | query 屬性 = 值的題數 |
|---|---|---|---|---|---|
| mid_century|chair | material | fabric | 18 / 41 | 0.56 | 1 / 3 |
| mid_century|table | color | natural wood | 17 / 39 | 0.56 | 0 / 3 |
| mid_century|chandelier_pendant | color | metallic | 29 / 42 | 0.31 | 3 / 3 |
| industrial|chair | color | black | 25 / 66 | 0.62 | 2 / 3 |
| industrial|table | material | wood | 22 / 32 | 0.31 | 1 / 3 |
| industrial|table | color | natural wood | 19 / 32 | 0.41 | 1 / 3 |
| farmhouse_rustic|chair | color | brown | 12 / 51 | 0.77 | 0 / 2 |
| farmhouse_rustic|chair | color | natural wood | 15 / 51 | 0.71 | 1 / 3 |
| farmhouse_rustic|lamp | material | metal | 12 / 37 | 0.68 | 0 / 2 |
| farmhouse_rustic|lamp | material | wood | 18 / 37 | 0.51 | 2 / 3 |
| farmhouse_rustic|chandelier_pendant | color | natural wood | 18 / 33 | 0.46 | 1 / 3 |
| boho|chair | material | rattan/wicker/rope | 22 / 33 | 0.33 | 3 / 3 |
| boho|lamp | material | rattan/wicker/rope | 12 / 29 | 0.59 | 0 / 2 |
| boho|chandelier_pendant | color | beige/cream | 20 / 34 | 0.41 | 2 / 3 |
| coastal|chair | color | blue | 12 / 30 | 0.60 | 0 / 2 |
| coastal|chair | color | white | 12 / 30 | 0.60 | 0 / 2 |
| coastal|table | material | wood | 16 / 32 | 0.50 | 0 / 3 |
| coastal|table | color | white | 14 / 32 | 0.56 | 2 / 3 |
| traditional|table | color | brown | 23 / 33 | 0.30 | 3 / 3 |
| traditional|lamp | material | metal | 23 / 36 | 0.36 | 3 / 3 |
| traditional|lamp | color | brown | 13 / 36 | 0.64 | 1 / 3 |
| traditional|lamp | color | metallic | 17 / 36 | 0.53 | 2 / 3 |
| traditional|chandelier_pendant | color | metallic | 22 / 34 | 0.35 | 3 / 3 |

## 2. 結果（由 `score4.py` 產生；完整檔案 `results/scores4.md`）

## T4 Negation 主表（tmpl_zh，3 順序）— Trap@5 = 5 件中選到「同風格同品項」陷阱的比例

| 模型 | Align@5 | Div@5 | EffCov@5 | Trap@5 | 失敗率 |
|---|---|---|---|---|---|
| qwen38-27b‡ | 0.898±0.004 | 0.705±0.003 | **0.673±0.001** | 0.014±0.001 | 0.000 |
| qwen36-35b | 0.859±0.006 | 0.703±0.003 | **0.660±0.003** | 0.005±0.002 | 0.000 |
| gemma4-12b‡ | 0.865±0.008 | 0.705±0.004 | **0.661±0.002** | 0.013±0.002 | 0.000 |
| qwen35-9b | 0.798±0.013 | 0.704±0.005 | **0.632±0.012** | 0.009±0.003 | 0.000 |
| qwen35-4b | 0.709±0.014 | 0.730±0.015 | **0.607±0.012** | 0.019±0.007 | 0.012 |
| internvl35-1tile | 0.504±0.013 | 0.701±0.019 | **0.454±0.018** | 0.207±0.003 | 0.000 |
| llavaov2-8b | 0.459±0.031 | 0.728±0.013 | **0.435±0.024** | 0.220±0.033 | 0.000 |
| siglip2-top5 | 0.067 | 0.644 | **0.079** | 0.909 | 0.000 |
| siglip2-mmr-std | 0.106 | 0.753 | **0.131** | 0.844 | 0.000 |
| siglip2-mmr-free† | 0.174 | 0.831 | **0.224** | 0.772 | 0.000 |
| random | 0.300 | 0.828 | 0.351 | 0.300 | 0 |
| oracle | 1.000 | 1.000 | 1.000 | 0.000 | 0 |

## T3 多重限制主表（tmpl_zh，3 順序）— 屬性陷阱 = 風格對但屬性 ≠ 指定值；風格陷阱 = 品項 / 屬性對但風格不對


### 顏色限制（42 題）

| 模型 | Align@5 | Div@5 | EffCov@5 | 屬性陷阱@5 | 風格陷阱@5 | 失敗率 |
|---|---|---|---|---|---|---|
| qwen38-27b‡ | 0.827±0.019 | 0.674±0.007 | **0.656±0.010** | 0.073±0.006 | 0.100±0.022 | 0.000 |
| qwen36-35b | 0.779±0.002 | 0.674±0.008 | **0.650±0.010** | 0.100±0.010 | 0.117±0.011 | 0.000 |
| gemma4-12b‡ | 0.789±0.002 | 0.704±0.023 | **0.679±0.026** | 0.097±0.002 | 0.106±0.010 | 0.000 |
| qwen35-9b | 0.757±0.022 | 0.676±0.006 | **0.645±0.012** | 0.095±0.017 | 0.143±0.035 | 0.000 |
| qwen35-4b | 0.757±0.017 | 0.664±0.006 | **0.641±0.005** | 0.100±0.000 | 0.137±0.015 | 0.000 |
| internvl35-1tile | 0.700±0.041 | 0.665±0.011 | **0.629±0.007** | 0.151±0.019 | 0.140±0.018 | 0.000 |
| llavaov2-8b | 0.690±0.021 | 0.652±0.008 | **0.613±0.017** | 0.227±0.020 | 0.075±0.016 | 0.000 |
| siglip2-top5 | 0.567 | 0.694 | **0.588** | 0.367 | 0.062 | 0.000 |
| siglip2-mmr-std | 0.552 | 0.675 | **0.606** | 0.367 | 0.071 | 0.000 |
| siglip2-mmr-free† | 0.557 | 0.723 | **0.615** | 0.357 | 0.076 | 0.000 |

### 材質限制（22 題）

| 模型 | Align@5 | Div@5 | EffCov@5 | 屬性陷阱@5 | 風格陷阱@5 | 失敗率 |
|---|---|---|---|---|---|---|
| qwen38-27b‡ | 0.782±0.013 | 0.736±0.017 | **0.682±0.024** | 0.097±0.015 | 0.118±0.022 | 0.000 |
| qwen36-35b | 0.788±0.015 | 0.704±0.016 | **0.643±0.015** | 0.127±0.013 | 0.085±0.011 | 0.000 |
| gemma4-12b‡ | 0.733±0.017 | 0.693±0.016 | **0.622±0.013** | 0.139±0.017 | 0.124±0.030 | 0.000 |
| qwen35-9b | 0.761±0.015 | 0.724±0.007 | **0.657±0.003** | 0.136±0.013 | 0.103±0.011 | 0.000 |
| qwen35-4b | 0.773±0.022 | 0.706±0.009 | **0.656±0.020** | 0.121±0.017 | 0.106±0.028 | 0.000 |
| internvl35-1tile | 0.633±0.011 | 0.668±0.018 | **0.563±0.008** | 0.245±0.007 | 0.106±0.011 | 0.000 |
| llavaov2-8b | 0.694±0.037 | 0.664±0.023 | **0.582±0.012** | 0.215±0.049 | 0.073±0.020 | 0.000 |
| siglip2-top5 | 0.509 | 0.731 | **0.495** | 0.473 | 0.018 | 0.000 |
| siglip2-mmr-std | 0.491 | 0.773 | **0.524** | 0.455 | 0.045 | 0.000 |
| siglip2-mmr-free† | 0.518 | 0.897 | **0.617** | 0.464 | 0.018 | 0.000 |

### 全部 T3（64 題）

| 模型 | Align@5 | Div@5 | EffCov@5 | 屬性陷阱@5 | 風格陷阱@5 | 失敗率 |
|---|---|---|---|---|---|---|
| qwen38-27b‡ | 0.811±0.012 | 0.696±0.005 | **0.665±0.007** | 0.081±0.005 | 0.106±0.011 | 0.000 |
| qwen36-35b | 0.782±0.006 | 0.684±0.008 | **0.648±0.008** | 0.109±0.010 | 0.106±0.005 | 0.000 |
| gemma4-12b‡ | 0.770±0.005 | 0.700±0.019 | **0.659±0.021** | 0.111±0.005 | 0.113±0.009 | 0.000 |
| qwen35-9b | 0.758±0.016 | 0.693±0.002 | **0.649±0.007** | 0.109±0.007 | 0.129±0.021 | 0.000 |
| qwen35-4b | 0.763±0.013 | 0.678±0.007 | **0.646±0.010** | 0.107±0.006 | 0.126±0.007 | 0.000 |
| internvl35-1tile | 0.677±0.027 | 0.666±0.012 | **0.607±0.002** | 0.183±0.010 | 0.128±0.016 | 0.000 |
| llavaov2-8b | 0.692±0.004 | 0.655±0.012 | **0.602±0.012** | 0.223±0.006 | 0.074±0.015 | 0.000 |
| siglip2-top5 | 0.547 | 0.706 | **0.556** | 0.403 | 0.047 | 0.000 |
| siglip2-mmr-std | 0.531 | 0.704 | **0.578** | 0.397 | 0.062 | 0.000 |
| siglip2-mmr-free† | 0.544 | 0.777 | **0.616** | 0.394 | 0.056 | 0.000 |
| random | 0.301 | 0.728 | 0.431 | 0.300 | 0.200 | 0 |
| oracle | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0 |

### query 本身的屬性是否等於指定值（T3，tmpl_zh；等於 31 題 / 不等於 33 題）

| 模型 | 等於：Align | 等於：EffCov | 等於：屬性陷阱 | 不等於：Align | 不等於：EffCov | 不等於：屬性陷阱 |
|---|---|---|---|---|---|---|
| qwen38-27b‡ | 0.826 | 0.674 | 0.101 | 0.798 | 0.656 | 0.063 |
| qwen36-35b | 0.789 | 0.648 | 0.120 | 0.776 | 0.648 | 0.099 |
| gemma4-12b‡ | 0.852 | 0.681 | 0.090 | 0.693 | 0.639 | 0.131 |
| qwen35-9b | 0.783 | 0.657 | 0.114 | 0.735 | 0.642 | 0.105 |
| qwen35-4b | 0.785 | 0.646 | 0.110 | 0.741 | 0.646 | 0.105 |
| internvl35-1tile | 0.686 | 0.611 | 0.191 | 0.669 | 0.603 | 0.176 |
| llavaov2-8b | 0.712 | 0.609 | 0.215 | 0.673 | 0.597 | 0.230 |
| siglip2-top5 | 0.684 | 0.631 | 0.284 | 0.418 | 0.485 | 0.515 |
| siglip2-mmr-std | 0.658 | 0.632 | 0.290 | 0.412 | 0.527 | 0.497 |
| siglip2-mmr-free† | 0.665 | 0.679 | 0.297 | 0.430 | 0.556 | 0.485 |

## 措辭比較（只取原順序 o0；tmpl_zh = 中文模板、tmpl_en = 英文直譯、syn_en = 合成 query）

配對差 = 同一題兩種措辭的分數相減，題目層級 bootstrap 95% CI（10,000 次）。syn_en 由 Claude Sonnet 5.5 改寫。


### Align@5

| 模型 | 題型 | tmpl_zh | tmpl_en | syn_en | tmpl_en − tmpl_zh [95% CI] | syn_en − tmpl_en [95% CI] | syn_en − tmpl_zh [95% CI] |
|---|---|---|---|---|---|---|---|
| qwen38-27b‡ | S1 | 0.806 | 0.722 | 0.617 | -0.083 [-0.117, -0.052] | -0.106 [-0.144, -0.069] | -0.189 [-0.231, -0.148] |
| qwen38-27b‡ | S2 | 0.913 | 0.900 | 0.809 | -0.013 [-0.031, +0.004] | -0.091 [-0.122, -0.061] | -0.104 [-0.135, -0.072] |
| qwen38-27b‡ | T3 | 0.825 | 0.775 | 0.688 | -0.050 [-0.084, -0.016] | -0.087 [-0.138, -0.034] | -0.137 [-0.184, -0.091] |
| qwen38-27b‡ | T4 | 0.904 | 0.878 | 0.711 | -0.026 [-0.046, -0.007] | -0.167 [-0.206, -0.128] | -0.193 [-0.235, -0.152] |
| qwen36-35b | S1 | 0.730 | 0.717 | 0.631 | -0.013 [-0.039, +0.013] | -0.085 [-0.130, -0.043] | -0.098 [-0.144, -0.052] |
| qwen36-35b | S2 | 0.928 | 0.898 | 0.807 | -0.030 [-0.059, -0.002] | -0.091 [-0.133, -0.048] | -0.120 [-0.161, -0.081] |
| qwen36-35b | T3 | 0.775 | 0.731 | 0.628 | -0.044 [-0.091, -0.000] | -0.103 [-0.153, -0.056] | -0.147 [-0.200, -0.097] |
| qwen36-35b | T4 | 0.867 | 0.835 | 0.606 | -0.031 [-0.067, +0.002] | -0.230 [-0.274, -0.185] | -0.261 [-0.307, -0.215] |
| gemma4-12b‡ | S1 | 0.676 | 0.656 | 0.563 | -0.020 [-0.054, +0.011] | -0.093 [-0.139, -0.044] | -0.113 [-0.159, -0.067] |
| gemma4-12b‡ | S2 | 0.883 | 0.887 | 0.650 | +0.004 [-0.017, +0.024] | -0.237 [-0.283, -0.191] | -0.233 [-0.283, -0.185] |
| gemma4-12b‡ | T3 | 0.775 | 0.766 | 0.606 | -0.009 [-0.047, +0.028] | -0.159 [-0.222, -0.100] | -0.169 [-0.231, -0.109] |
| gemma4-12b‡ | T4 | 0.854 | 0.846 | 0.546 | -0.007 [-0.035, +0.019] | -0.300 [-0.356, -0.246] | -0.307 [-0.361, -0.257] |
| qwen35-9b | S1 | 0.728 | 0.676 | 0.646 | -0.052 [-0.085, -0.019] | -0.030 [-0.070, +0.013] | -0.081 [-0.124, -0.039] |
| qwen35-9b | S2 | 0.887 | 0.891 | 0.841 | +0.004 [-0.015, +0.022] | -0.050 [-0.078, -0.024] | -0.046 [-0.072, -0.022] |
| qwen35-9b | T3 | 0.738 | 0.722 | 0.675 | -0.016 [-0.053, +0.019] | -0.047 [-0.106, +0.009] | -0.062 [-0.119, -0.006] |
| qwen35-9b | T4 | 0.815 | 0.741 | 0.576 | -0.074 [-0.102, -0.048] | -0.165 [-0.207, -0.122] | -0.239 [-0.276, -0.202] |
| qwen35-4b | S1 | 0.630 | 0.580 | 0.517 | -0.050 [-0.083, -0.017] | -0.063 [-0.100, -0.028] | -0.113 [-0.157, -0.070] |
| qwen35-4b | S2 | 0.857 | 0.733 | 0.693 | -0.124 [-0.165, -0.085] | -0.041 [-0.078, -0.002] | -0.165 [-0.207, -0.124] |
| qwen35-4b | T3 | 0.747 | 0.669 | 0.556 | -0.078 [-0.122, -0.034] | -0.112 [-0.153, -0.072] | -0.191 [-0.238, -0.144] |
| qwen35-4b | T4 | 0.719 | 0.572 | 0.489 | -0.146 [-0.185, -0.107] | -0.083 [-0.117, -0.052] | -0.230 [-0.278, -0.181] |
| internvl35-1tile | S1 | 0.431 | 0.413 | 0.394 | -0.019 [-0.050, +0.013] | -0.019 [-0.052, +0.015] | -0.037 [-0.078, +0.002] |
| internvl35-1tile | S2 | 0.804 | 0.743 | 0.756 | -0.061 [-0.091, -0.031] | +0.013 [-0.015, +0.041] | -0.048 [-0.078, -0.019] |
| internvl35-1tile | T3 | 0.659 | 0.622 | 0.578 | -0.037 [-0.075, -0.003] | -0.044 [-0.081, -0.006] | -0.081 [-0.125, -0.038] |
| internvl35-1tile | T4 | 0.509 | 0.470 | 0.426 | -0.039 [-0.081, +0.004] | -0.044 [-0.089, -0.000] | -0.083 [-0.135, -0.033] |
| llavaov2-8b | S1 | 0.480 | 0.506 | 0.430 | +0.026 [-0.006, +0.057] | -0.076 [-0.117, -0.039] | -0.050 [-0.091, -0.009] |
| llavaov2-8b | S2 | 0.831 | 0.822 | 0.783 | -0.009 [-0.041, +0.022] | -0.039 [-0.067, -0.013] | -0.048 [-0.081, -0.015] |
| llavaov2-8b | T3 | 0.697 | 0.631 | 0.619 | -0.066 [-0.106, -0.028] | -0.012 [-0.056, +0.028] | -0.078 [-0.131, -0.028] |
| llavaov2-8b | T4 | 0.483 | 0.483 | 0.409 | +0.000 [-0.046, +0.048] | -0.074 [-0.120, -0.030] | -0.074 [-0.131, -0.017] |

### EffCov@5

| 模型 | 題型 | tmpl_zh | tmpl_en | syn_en | tmpl_en − tmpl_zh [95% CI] | syn_en − tmpl_en [95% CI] | syn_en − tmpl_zh [95% CI] |
|---|---|---|---|---|---|---|---|
| qwen38-27b‡ | S1 | 0.588 | 0.528 | 0.471 | -0.060 [-0.084, -0.037] | -0.057 [-0.084, -0.032] | -0.117 [-0.150, -0.086] |
| qwen38-27b‡ | S2 | 0.660 | 0.662 | 0.629 | +0.002 [-0.017, +0.021] | -0.034 [-0.057, -0.011] | -0.032 [-0.058, -0.006] |
| qwen38-27b‡ | T3 | 0.673 | 0.667 | 0.646 | -0.006 [-0.033, +0.020] | -0.021 [-0.055, +0.012] | -0.027 [-0.067, +0.013] |
| qwen38-27b‡ | T4 | 0.673 | 0.661 | 0.572 | -0.013 [-0.032, +0.006] | -0.089 [-0.117, -0.062] | -0.101 [-0.134, -0.070] |
| qwen36-35b | S1 | 0.533 | 0.528 | 0.485 | -0.005 [-0.025, +0.014] | -0.043 [-0.074, -0.013] | -0.048 [-0.080, -0.017] |
| qwen36-35b | S2 | 0.678 | 0.674 | 0.612 | -0.004 [-0.025, +0.017] | -0.062 [-0.090, -0.035] | -0.066 [-0.095, -0.037] |
| qwen36-35b | T3 | 0.658 | 0.662 | 0.622 | +0.004 [-0.037, +0.044] | -0.040 [-0.088, +0.005] | -0.036 [-0.085, +0.009] |
| qwen36-35b | T4 | 0.663 | 0.653 | 0.543 | -0.010 [-0.038, +0.019] | -0.110 [-0.151, -0.072] | -0.120 [-0.157, -0.085] |
| gemma4-12b‡ | S1 | 0.521 | 0.500 | 0.456 | -0.021 [-0.044, +0.001] | -0.044 [-0.078, -0.010] | -0.065 [-0.098, -0.032] |
| gemma4-12b‡ | S2 | 0.663 | 0.663 | 0.549 | +0.000 [-0.022, +0.023] | -0.114 [-0.155, -0.075] | -0.114 [-0.157, -0.072] |
| gemma4-12b‡ | T3 | 0.676 | 0.652 | 0.630 | -0.024 [-0.055, +0.006] | -0.023 [-0.068, +0.019] | -0.046 [-0.099, +0.001] |
| gemma4-12b‡ | T4 | 0.660 | 0.677 | 0.529 | +0.016 [-0.003, +0.036] | -0.147 [-0.187, -0.110] | -0.131 [-0.170, -0.094] |
| qwen35-9b | S1 | 0.550 | 0.508 | 0.488 | -0.042 [-0.065, -0.019] | -0.020 [-0.046, +0.007] | -0.062 [-0.092, -0.031] |
| qwen35-9b | S2 | 0.673 | 0.676 | 0.654 | +0.004 [-0.016, +0.023] | -0.022 [-0.043, -0.003] | -0.018 [-0.038, +0.000] |
| qwen35-9b | T3 | 0.643 | 0.637 | 0.613 | -0.006 [-0.036, +0.025] | -0.024 [-0.075, +0.029] | -0.029 [-0.076, +0.020] |
| qwen35-9b | T4 | 0.649 | 0.593 | 0.543 | -0.056 [-0.078, -0.034] | -0.049 [-0.084, -0.018] | -0.105 [-0.137, -0.076] |
| qwen35-4b | S1 | 0.488 | 0.447 | 0.421 | -0.041 [-0.065, -0.018] | -0.026 [-0.055, +0.003] | -0.067 [-0.098, -0.038] |
| qwen35-4b | S2 | 0.643 | 0.617 | 0.617 | -0.026 [-0.059, +0.005] | -0.000 [-0.029, +0.031] | -0.026 [-0.059, +0.007] |
| qwen35-4b | T3 | 0.647 | 0.666 | 0.584 | +0.019 [-0.019, +0.059] | -0.082 [-0.122, -0.043] | -0.062 [-0.115, -0.014] |
| qwen35-4b | T4 | 0.623 | 0.572 | 0.492 | -0.051 [-0.084, -0.017] | -0.081 [-0.110, -0.053] | -0.132 [-0.172, -0.092] |
| internvl35-1tile | S1 | 0.375 | 0.359 | 0.357 | -0.016 [-0.047, +0.014] | -0.003 [-0.028, +0.024] | -0.019 [-0.051, +0.013] |
| internvl35-1tile | S2 | 0.632 | 0.634 | 0.639 | +0.002 [-0.020, +0.024] | +0.005 [-0.017, +0.027] | +0.007 [-0.015, +0.029] |
| internvl35-1tile | T3 | 0.604 | 0.593 | 0.589 | -0.011 [-0.046, +0.024] | -0.005 [-0.035, +0.027] | -0.015 [-0.051, +0.021] |
| internvl35-1tile | T4 | 0.459 | 0.434 | 0.443 | -0.024 [-0.058, +0.009] | +0.009 [-0.032, +0.048] | -0.016 [-0.060, +0.028] |
| llavaov2-8b | S1 | 0.409 | 0.420 | 0.382 | +0.011 [-0.013, +0.035] | -0.039 [-0.070, -0.008] | -0.028 [-0.059, +0.003] |
| llavaov2-8b | S2 | 0.640 | 0.650 | 0.640 | +0.010 [-0.014, +0.035] | -0.009 [-0.034, +0.015] | +0.000 [-0.022, +0.024] |
| llavaov2-8b | T3 | 0.618 | 0.605 | 0.590 | -0.014 [-0.044, +0.018] | -0.014 [-0.049, +0.020] | -0.028 [-0.066, +0.009] |
| llavaov2-8b | T4 | 0.445 | 0.456 | 0.428 | +0.011 [-0.032, +0.055] | -0.028 [-0.067, +0.011] | -0.017 [-0.062, +0.029] |

## 總表：所有題型 × 模型（tmpl_zh 主條件，EffCov@5；S1、S2 來自階段 3 的 img）

| 模型 | S1 | S2 | T3 | T4 | 4 題型平均 |
|---|---|---|---|---|---|
| qwen38-27b‡ | 0.581 | 0.664 | 0.665 | 0.673 | 0.646 |
| qwen36-35b | 0.534 | 0.668 | 0.648 | 0.660 | 0.628 |
| gemma4-12b‡ | 0.532 | 0.665 | 0.659 | 0.661 | 0.629 |
| qwen35-9b | 0.553 | 0.674 | 0.649 | 0.632 | 0.627 |
| qwen35-4b | 0.489 | 0.656 | 0.646 | 0.607 | 0.599 |
| internvl35-1tile | 0.375 | 0.641 | 0.607 | 0.454 | 0.519 |
| llavaov2-8b | 0.401 | 0.650 | 0.602 | 0.435 | 0.522 |
| siglip2-top5 | 0.448 | 0.661 | 0.556 | 0.079 | 0.436 |
| siglip2-mmr-std | 0.488 | 0.672 | 0.578 | 0.131 | 0.467 |
| siglip2-mmr-free† | 0.511 | 0.740 | 0.616 | 0.224 | 0.523 |
| random | 0.327 | 0.389 | 0.431 | 0.351 | 0.375 |
| oracle | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## 總表：Align@5

| 模型 | S1 | S2 | T3 | T4 |
|---|---|---|---|---|
| qwen38-27b‡ | 0.805 | 0.914 | 0.811 | 0.898 |
| qwen36-35b | 0.733 | 0.920 | 0.782 | 0.859 |
| gemma4-12b‡ | 0.694 | 0.897 | 0.770 | 0.865 |
| qwen35-9b | 0.743 | 0.893 | 0.758 | 0.798 |
| qwen35-4b | 0.646 | 0.873 | 0.763 | 0.709 |
| internvl35-1tile | 0.424 | 0.810 | 0.677 | 0.504 |
| llavaov2-8b | 0.469 | 0.831 | 0.692 | 0.459 |
| siglip2-top5 | 0.563 | 0.861 | 0.547 | 0.067 |
| siglip2-mmr-std | 0.559 | 0.798 | 0.531 | 0.106 |
| siglip2-mmr-free† | 0.574 | 0.796 | 0.544 | 0.174 |

## 完成題數（模型 × 措辭 × 題型 的已完成 / 應有；tmpl_zh 為 3 順序）

- qwen38-27b tmpl_zh S1: o0=108/108, o1=108/108, o2=108/108
- qwen38-27b tmpl_en S1: o0=108
- qwen38-27b syn_en S1: o0=108
- qwen38-27b tmpl_zh S2: o0=108/108, o1=108/108, o2=108/108
- qwen38-27b tmpl_en S2: o0=108
- qwen38-27b syn_en S2: o0=108
- qwen38-27b tmpl_zh T3: o0=64/64, o1=64/64, o2=64/64
- qwen38-27b tmpl_en T3: o0=64
- qwen38-27b syn_en T3: o0=64
- qwen38-27b tmpl_zh T4: o0=108/108, o1=108/108, o2=108/108
- qwen38-27b tmpl_en T4: o0=108
- qwen38-27b syn_en T4: o0=108
- qwen36-35b tmpl_zh S1: o0=108/108, o1=108/108, o2=108/108
- qwen36-35b tmpl_en S1: o0=108
- qwen36-35b syn_en S1: o0=108
- qwen36-35b tmpl_zh S2: o0=108/108, o1=108/108, o2=108/108
- qwen36-35b tmpl_en S2: o0=108
- qwen36-35b syn_en S2: o0=108
- qwen36-35b tmpl_zh T3: o0=64/64, o1=64/64, o2=64/64
- qwen36-35b tmpl_en T3: o0=64
- qwen36-35b syn_en T3: o0=64
- qwen36-35b tmpl_zh T4: o0=108/108, o1=108/108, o2=108/108
- qwen36-35b tmpl_en T4: o0=108
- qwen36-35b syn_en T4: o0=108
- gemma4-12b tmpl_zh S1: o0=108/108, o1=108/108, o2=108/108
- gemma4-12b tmpl_en S1: o0=108
- gemma4-12b syn_en S1: o0=108
- gemma4-12b tmpl_zh S2: o0=108/108, o1=108/108, o2=108/108
- gemma4-12b tmpl_en S2: o0=108
- gemma4-12b syn_en S2: o0=108
- gemma4-12b tmpl_zh T3: o0=64/64, o1=64/64, o2=64/64
- gemma4-12b tmpl_en T3: o0=64
- gemma4-12b syn_en T3: o0=64
- gemma4-12b tmpl_zh T4: o0=108/108, o1=108/108, o2=108/108
- gemma4-12b tmpl_en T4: o0=108
- gemma4-12b syn_en T4: o0=108
- qwen35-9b tmpl_zh S1: o0=108/108, o1=108/108, o2=108/108
- qwen35-9b tmpl_en S1: o0=108
- qwen35-9b syn_en S1: o0=108
- qwen35-9b tmpl_zh S2: o0=108/108, o1=108/108, o2=108/108
- qwen35-9b tmpl_en S2: o0=108
- qwen35-9b syn_en S2: o0=108
- qwen35-9b tmpl_zh T3: o0=64/64, o1=64/64, o2=64/64
- qwen35-9b tmpl_en T3: o0=64
- qwen35-9b syn_en T3: o0=64
- qwen35-9b tmpl_zh T4: o0=108/108, o1=108/108, o2=108/108
- qwen35-9b tmpl_en T4: o0=108
- qwen35-9b syn_en T4: o0=108
- qwen35-4b tmpl_zh S1: o0=108/108, o1=108/108, o2=108/108
- qwen35-4b tmpl_en S1: o0=108
- qwen35-4b syn_en S1: o0=108
- qwen35-4b tmpl_zh S2: o0=108/108, o1=108/108, o2=108/108
- qwen35-4b tmpl_en S2: o0=108
- qwen35-4b syn_en S2: o0=108
- qwen35-4b tmpl_zh T3: o0=64/64, o1=64/64, o2=64/64
- qwen35-4b tmpl_en T3: o0=64
- qwen35-4b syn_en T3: o0=64
- qwen35-4b tmpl_zh T4: o0=108/108, o1=108/108, o2=108/108
- qwen35-4b tmpl_en T4: o0=108
- qwen35-4b syn_en T4: o0=108
- internvl35-1tile tmpl_zh S1: o0=108/108, o1=108/108, o2=108/108
- internvl35-1tile tmpl_en S1: o0=108
- internvl35-1tile syn_en S1: o0=108
- internvl35-1tile tmpl_zh S2: o0=108/108, o1=108/108, o2=108/108
- internvl35-1tile tmpl_en S2: o0=108
- internvl35-1tile syn_en S2: o0=108
- internvl35-1tile tmpl_zh T3: o0=64/64, o1=64/64, o2=64/64
- internvl35-1tile tmpl_en T3: o0=64
- internvl35-1tile syn_en T3: o0=64
- internvl35-1tile tmpl_zh T4: o0=108/108, o1=108/108, o2=108/108
- internvl35-1tile tmpl_en T4: o0=108
- internvl35-1tile syn_en T4: o0=108
- llavaov2-8b tmpl_zh S1: o0=108/108, o1=108/108, o2=108/108
- llavaov2-8b tmpl_en S1: o0=108
- llavaov2-8b syn_en S1: o0=108
- llavaov2-8b tmpl_zh S2: o0=108/108, o1=108/108, o2=108/108
- llavaov2-8b tmpl_en S2: o0=108
- llavaov2-8b syn_en S2: o0=108
- llavaov2-8b tmpl_zh T3: o0=64/64, o1=64/64, o2=64/64
- llavaov2-8b tmpl_en T3: o0=64
- llavaov2-8b syn_en T3: o0=64
- llavaov2-8b tmpl_zh T4: o0=108/108, o1=108/108, o2=108/108
- llavaov2-8b tmpl_en T4: o0=108
- llavaov2-8b syn_en T4: o0=108


## 3. 合成 query（syn_en）品質

- 共 388 題；LLM 通過自動檢查 388 題、用 tmpl_en 後備 0 題。通過者的嘗試次數分布：{1: 380, 2: 7, 3: 1}。
- 被檢查擋下的原因（所有嘗試合計）：{"把品項限制成其他單一品項 ['table']": 9}。
- 平均字數：S1 9.3、S2 8.2、T3 8.5、T4 8.7。

### 附錄：隨機抽 30 題的改寫（給 Skyler 看品質）

| qid | 題型 | 模板句（改寫輸入） | syn_en | 來源 |
|---|---|---|---|---|
| item_0193-S1 | S1 | Find products in the same style as the reference image. | items with the same look as the one in the picture | llm |
| item_0278-T4 | T4 | Find products in the same style as the reference image, but not chandeliers / pendant lights. | need products that look like this, not chandeliers or pendant lights | llm |
| item_0359-S1 | S1 | Find products in the same style as the reference image. | looking for more stuff with the same look as this | llm |
| item_0359-T3-c03 | T3 | Find chairs in the same style as the reference image, whose color is black. | black chairs like this one | llm |
| item_0482-T4 | T4 | Find products in the same style as the reference image, but not lamps (table or floor lamps). | looking for stuff like this but not lamps | llm |
| item_0536-S1 | S1 | Find products in the same style as the reference image. | anything similar in style to this? | llm |
| item_0834-T3-c19 | T3 | Find lamps (table or floor lamps) in the same style as the reference image, whose material is metal. | metal lamps like the one in this photo | llm |
| item_0965-T4 | T4 | Find products in the same style as the reference image, but not chandeliers / pendant lights. | something like this photo but not chandeliers or pendant lights | llm |
| item_0990-S1 | S1 | Find products in the same style as the reference image. | need something that matches the look of this photo | llm |
| item_1033-S1 | S1 | Find products in the same style as the reference image. | products that go with the look of this photo | llm |
| item_1067-S2 | S2 | Find tables in the same style as the reference image. | tables like the one in this photo | llm |
| item_1071-S2 | S2 | Find lamps (table or floor lamps) in the same style as the reference image. | lamps like this, either table or floor | llm |
| item_1103-S2 | S2 | Find chandeliers / pendant lights in the same style as the reference image. | chandeliers or pendant lights like the one in this photo | llm |
| item_1196-T4 | T4 | Find products in the same style as the reference image, but not chairs. | looking for the same look as this, no chairs though | llm |
| item_1244-T4 | T4 | Find products in the same style as the reference image, but not lamps (table or floor lamps). | similar look to the one in the photo, no lamps please | llm |
| item_1285-S2 | S2 | Find chairs in the same style as the reference image. | chairs like the one in this picture | llm |
| item_1446-T4 | T4 | Find products in the same style as the reference image, but not lamps (table or floor lamps). | items that match this photo, anything but lamps | llm |
| item_1663-S2 | S2 | Find lamps (table or floor lamps) in the same style as the reference image. | lamps like this one in the picture | llm |
| item_1671-S2 | S2 | Find lamps (table or floor lamps) in the same style as the reference image. | table lamps or floor lamps like the one in this picture | llm |
| item_1719-T4 | T4 | Find products in the same style as the reference image, but not chandeliers / pendant lights. | looking for stuff like this, not chandeliers or pendant lights | llm |
| item_1729-T4 | T4 | Find products in the same style as the reference image, but not tables. | things like this, but not tables | llm |
| item_1734-T4 | T4 | Find products in the same style as the reference image, but not chairs. | similar to this but not chairs | llm |
| item_1851-T4 | T4 | Find products in the same style as the reference image, but not lamps (table or floor lamps). | anything that looks like this picture other than lamps | llm |
| item_2173-T4 | T4 | Find products in the same style as the reference image, but not tables. | want stuff like this, just not tables | llm |
| item_2220-S1 | S1 | Find products in the same style as the reference image. | want more products that look like what's in this picture | llm |
| item_2235-S2 | S2 | Find tables in the same style as the reference image. | tables that match this one in the picture | llm |
| item_2418-S1 | S1 | Find products in the same style as the reference image. | show me other pieces like the one in the picture | llm |
| item_2472-S1 | S1 | Find products in the same style as the reference image. | find things that match the look of the one in this picture | llm |
| item_2522-T4 | T4 | Find products in the same style as the reference image, but not lamps (table or floor lamps). | like the one in the picture, other than lamps | llm |
| item_2747-S2 | S2 | Find tables in the same style as the reference image. | tables like the one in this picture | llm |

## 4. 限制

- query 圖的風格沒有人工確認（只靠三方一致 + Claude 高信心）；題數小（T3 64 題、T4 108 題），T3 每個組合只有 2–3 題，格子層級的差異不可信。
- ③「n_d ≥ 2 即自由維度」教授尚未確認；許多 T3 題的自由維度只剩 2 種值（見 build_report4.json 的 n_d 分布），EffCov 的鑑別力有限。
- gemma4-12b‡、qwen38-27b‡ 同時是標註者與受測者。
- siglip2-mmr-free† 使用標註屬性（特權資訊），不是公平基準線；結論以 siglip2-top5、siglip2-mmr-std 為對照。
- 解析度沿用階段 3 的偏離：Qwen 系列 max_pixels = 307200、LLaVA-OV2 圖縮到 560，其他 900（否則 41 張圖會超過 16384 tokens）。
- 標題中的風格線索字（beach、steampunk、cottage、barn、antique…）依規則未刪；T3 / T4 的標題已改為反覆刪到不再變，但 S1 / S2 仍是階段 3 的單次刪除標題（為了可配對），其中 item_0773 "Mid Modern Century" 殘留 "Mid Century"。
- T3 的「顏色 / 材質」限制值以三位標註者多數決為準，標註本身有雜訊；T4、T3 的合格集合來自標註，不是人工確認。
- syn_en 由 Claude Sonnet 5.5 改寫（偏離 RUNBOOK 的本地 Qwen3.8-27B），不同於真人；改寫只看模板句、不看圖，措辭風格偏單一（見附錄 30 題）。tmpl_zh 的 S1 / S2 用階段 3 的結果（同 prompt、同題）。

## 5. 需要 Skyler 決定的事

1. T3 可出題組合集中在少數屬性值（例如 wood、natural wood、metallic）；要不要擴大標註讓 T3 組合更多元（需要更多合格商品）。
2. T3 / T4 的「陷阱」是否就是你要的難度？SigLIP2 純相似度在 T4 的 Trap 很高，代表 T4 主要測「讀懂不要」；若想測更細的否定，可再加陷阱種類。
3. 合成 query 目前只有 Claude 一種改寫者（原訂 Qwen3.8-27B 因等不到 GPU 改用）；要不要再加人工改寫一小批或本地模型改寫作對照。
4. 標註者 = 受測者（gemma4-12b‡、qwen38-27b‡）的問題，長期是否換掉其中一位標註者、或用人工確認的子集另算（延續階段 3 審查建議）。
5. 教授對 ③ 的意見回來後是否重新出題（延續階段 3）。

## 6. 自我驗收

第 7 項列出的 `stage3/OPUS_REVIEW.md` 是主控 Opus 在階段 4 開始前後寫的審查報告（01:48，非本階段 agent 所改）。

```
1 重跑 score4.py 後 scores4.json / scores4.md 不變: True
2 重跑 build_questions4.py 後 questions4.json 不變: True
3 重產報告與現有報告一致（數字全由 JSON 產生）: True
4 完成題數 qwen38-27b tmpl_zh|S1: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen38-27b tmpl_zh|S2: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen38-27b tmpl_zh|T3: o0=64/64, o1=64/64, o2=64/64
4 完成題數 qwen38-27b tmpl_zh|T4: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen38-27b wording|S1: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen38-27b wording|S2: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen38-27b wording|T3: tmpl_zh=64, tmpl_en=64, syn_en=64
4 完成題數 qwen38-27b wording|T4: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen36-35b tmpl_zh|S1: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen36-35b tmpl_zh|S2: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen36-35b tmpl_zh|T3: o0=64/64, o1=64/64, o2=64/64
4 完成題數 qwen36-35b tmpl_zh|T4: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen36-35b wording|S1: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen36-35b wording|S2: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen36-35b wording|T3: tmpl_zh=64, tmpl_en=64, syn_en=64
4 完成題數 qwen36-35b wording|T4: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 gemma4-12b tmpl_zh|S1: o0=108/108, o1=108/108, o2=108/108
4 完成題數 gemma4-12b tmpl_zh|S2: o0=108/108, o1=108/108, o2=108/108
4 完成題數 gemma4-12b tmpl_zh|T3: o0=64/64, o1=64/64, o2=64/64
4 完成題數 gemma4-12b tmpl_zh|T4: o0=108/108, o1=108/108, o2=108/108
4 完成題數 gemma4-12b wording|S1: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 gemma4-12b wording|S2: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 gemma4-12b wording|T3: tmpl_zh=64, tmpl_en=64, syn_en=64
4 完成題數 gemma4-12b wording|T4: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen35-9b tmpl_zh|S1: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen35-9b tmpl_zh|S2: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen35-9b tmpl_zh|T3: o0=64/64, o1=64/64, o2=64/64
4 完成題數 qwen35-9b tmpl_zh|T4: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen35-9b wording|S1: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen35-9b wording|S2: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen35-9b wording|T3: tmpl_zh=64, tmpl_en=64, syn_en=64
4 完成題數 qwen35-9b wording|T4: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen35-4b tmpl_zh|S1: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen35-4b tmpl_zh|S2: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen35-4b tmpl_zh|T3: o0=64/64, o1=64/64, o2=64/64
4 完成題數 qwen35-4b tmpl_zh|T4: o0=108/108, o1=108/108, o2=108/108
4 完成題數 qwen35-4b wording|S1: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen35-4b wording|S2: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 qwen35-4b wording|T3: tmpl_zh=64, tmpl_en=64, syn_en=64
4 完成題數 qwen35-4b wording|T4: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 internvl35-1tile tmpl_zh|S1: o0=108/108, o1=108/108, o2=108/108
4 完成題數 internvl35-1tile tmpl_zh|S2: o0=108/108, o1=108/108, o2=108/108
4 完成題數 internvl35-1tile tmpl_zh|T3: o0=64/64, o1=64/64, o2=64/64
4 完成題數 internvl35-1tile tmpl_zh|T4: o0=108/108, o1=108/108, o2=108/108
4 完成題數 internvl35-1tile wording|S1: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 internvl35-1tile wording|S2: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 internvl35-1tile wording|T3: tmpl_zh=64, tmpl_en=64, syn_en=64
4 完成題數 internvl35-1tile wording|T4: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 llavaov2-8b tmpl_zh|S1: o0=108/108, o1=108/108, o2=108/108
4 完成題數 llavaov2-8b tmpl_zh|S2: o0=108/108, o1=108/108, o2=108/108
4 完成題數 llavaov2-8b tmpl_zh|T3: o0=64/64, o1=64/64, o2=64/64
4 完成題數 llavaov2-8b tmpl_zh|T4: o0=108/108, o1=108/108, o2=108/108
4 完成題數 llavaov2-8b wording|S1: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 llavaov2-8b wording|S2: tmpl_zh=108, tmpl_en=108, syn_en=108
4 完成題數 llavaov2-8b wording|T3: tmpl_zh=64, tmpl_en=64, syn_en=64
4 完成題數 llavaov2-8b wording|T4: tmpl_zh=108, tmpl_en=108, syn_en=108
5 殘留 -devset4 vLLM 數: 0（應為 0）
6 stage1 sha256 與 before 相同: True []
7 受保護資料夾 / stage2 / stage3 在階段 4 開始後被修改的檔案（應為空）: ['/mnt/raid0/home/skyler/vlm-diverse-retrieval/devset_v0/stage3/OPUS_REVIEW.md']
8 query_texts.json：388 題；使用 tmpl_en 後備 0 題
```
