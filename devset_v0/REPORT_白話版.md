# 開發集 v0：階段 0（建商品池）＋ 階段 1（抽樣三方標註）報告（白話版）

> 給 Skyler 醒來看。所有數字都由 `make_report.py` 從 `stage0/cell_counts.json`、`stage0/build_stats.json`、`results/stage1_analysis.json` 讀出來填（重算指令在第 8 節）。我做的判斷在 `DECISIONS.md`（26 條，每條有理由），時間線在 `PROGRESS.md`。
> 沒有開始階段 2，沒有出題，沒有跑選品實驗。

---

## 0. 先講結論

1. **商品池建好了**：7,522 件（30 格），主圖 8,415 張全部下載成功（1.09 GB）。30 格的關鍵字命中總數合計 49,339 件，同店同款去重後 42,225 件。（`stage0/cell_counts.json`）
2. **標題寫的風格只有一半可信。** 900 件抽樣中，三位標註者多數決的風格 = 標題關鍵字風格的只有 **48%**。三位自己分開看也差不多（Claude 49%、Qwen 48%、Gemma 47%），所以這不是某一個模型的問題。格子之間差很多：最高的是 coastal × wall art 83%、boho × wall art 80%、mid-century × 吊燈 77%；最低的是 traditional × wall art 7%、boho × table 10%、farmhouse/rustic × chair 13%。
3. **能直接當「合格答案」的約三分之一。** 三位風格一致、等於格子風格、而且沒有人給信心 1 的比例是 **35%**；再要求三位的品項也和規則一致是 **31%**。比 C3 試標時估的 56% 低很多（那次是三個 Claude，這次是三個不同模型，而且樣本來自關鍵字而不是人工挑過的商品）。
4. **30 格裡 21 格可以放心保留，2 格建議拿掉**（boho × table、coastal × 吊燈），另外 3 格量太少、4 格合格率太低（要標很多件才湊得齊）。清單在第 6 節。
5. **標註者一致性：品項很好，風格中等。** Fleiss κ：category 0.92、material 0.78、shape 0.73、color 0.71、style 0.67。風格的分歧最常發生在「有風格 vs 沒有明確風格（mixed/none、modern minimalist）」之間，而不是 C3 擔心的 coastal ↔ boho。
6. **Claude 很便宜：900 件 $8.29，每件 $0.0092**（加上批量檢查共 $8.71，遠低於 $30 上限）。階段 2 若每格要湊 13 件合格商品，還要新標約 1,071 件（約 $10，0.7–1.0 個五小時額度）；每格 26 件（2 題不重複）約 2,651 件（約 $24）；把整個商品池標完約 6,622 件（約 $61，4.1–6.1 個額度）。
7. **一個新問題要你決定：情境二的「材質多樣性」可能湊不出來。** 同一格的合格商品，材質常常只有一種（桌子幾乎都是 wood、吊燈幾乎都是 metal、掛畫都是 paper/canvas）。main table 草稿要求每個自由維度至少 4 種值，照目前的資料，很多格的 material 做不到（第 6.3 節）。

---

## 1. 名詞小字典

| 名詞 | 白話意思 |
|---|---|
| 格子 | 一個「風格 × 品項」組合，例如 boho × chair。共 6 × 5 = 30 格 |
| 關鍵字風格 | 商品標題或 details 的 Style 欄出現的風格字詞（例如標題有 "Boho"）。這只是線索，不是答案 |
| 命中總數 | 某一格裡，關鍵字與品項規則都符合、而且有主圖的商品數。之後算「可用量」的分母 |
| 商品池（pool） | 每格最多隨機留 300 件、下載好主圖的商品。階段 2 的標註從這裡拿 |
| pHash（感知雜湊） | 把圖縮得很小之後算出的 64 位元指紋；兩張圖看起來幾乎一樣時指紋也幾乎一樣。用來抓「同款重複上架」 |
| Jaccard | 兩個標題共同的字 ÷ 兩個標題合起來的字。≥ 0.8 代表標題幾乎一樣 |
| 三方標註 | 同一張圖給 Claude Opus 5.5、Qwen3.8-27B、gemma-4-12b 三個模型各標一次 |
| 多數決 | 三位中至少兩位選同一個值 |
| 信心 1–3 | 標註者對自己答案的把握：3 很確定、2 大致確定、1 不確定 |
| Fleiss κ（kappa） | 多位標註者「扣掉碰巧一致之後」的一致程度。0.6–0.8 算相當一致，0.8 以上算幾乎完全一致 |
| 95% 信賴區間 | 因為每格只抽 30 件，量到的比例有誤差；這個區間是「真正的比例大概落在哪裡」。這裡用 Wilson 區間（小樣本常用的算法）。**n = 30 時區間很寬（常常是 ±17 個百分點）** |
| 五小時額度 | Claude 訂閱方案每五小時可用的量。這裡用「1 個額度 ≈ 10–15 美元」換算，**這是經驗值，不是實測** |

---

## 2. 階段 0：建商品池

### 2.1 為什麼做
階段 2 要對商品做三方標註，得先有一批「候選商品 + 圖」。這一步不花 Claude 額度：只用本機的 Amazon Reviews 2023 子集和規則。

### 2.2 怎麼做（`stage0/` 的四支腳本，依序）

| 步驟 | 腳本 | 做什麼 |
|---|---|---|
| 1 | `s0_scan.py` | 掃 home、lighting、patio、handmade 四個子集（共 2,240,071 筆），用 C1 的規則原樣挑出 5 個品項的候選 |
| 2 | `s0_build_pool.py` | 套用修正後的品項規則 → 算 30 格命中數 → 同店同款去重 → 每格依 seed 0 的隨機順序取前 300 件（多下載 40 件當遞補） |
| 3 | `s0_download.py` | 下載主圖（平行 8、最多重試 3 次） |
| 4 | `s0_finalize.py` | 算 sha256 和 pHash、去掉近似重複、寫出 `pool.jsonl` 和 `cell_counts.json` |

真實例子（`pool.jsonl` 的一筆）：`B01I4VVXRU`「HD Couture Bohemian Velvet Chair, Marine Blue」→ 類別路徑 Furniture > Living Room Furniture > Chairs → 品項 chair；標題有 Bohemian → 關鍵字風格 boho → 進 boho × chair 這一格。（這張後來被三位標成 glam / traditional / glam：一張深藍絲絨釘扣椅，標題寫 Bohemian 但看起來不是。）

### 2.3 我改了品項規則（重要，命中數因此比 C1 / C4 小）

C1 的規則是「類別路徑沒命中就看標題有沒有 chair / table / lamp」。我檢查後發現標題補抓的幾乎都是誤抓：table 抓到裝飾托盤、假南瓜、胡桃鉗、桌布；lamp 抓到油燈、夜燈、鹽燈；wall art 抓到捕夢網、花圈。所以改成：

- **只用類別路徑白名單**決定品項（清單在 `s0_build_pool.py` 的 `PATH_RULES`、DECISIONS 第 2 條）。
- lamp 只收桌燈、落地燈；吊燈**不收吸頂燈**（RUNBOOK 寫的是吊燈）；chair 不收電競椅、兒童椅、懶骨頭。
- 標題排除字：按摩椅 / 電動起身椅（C4 提到的誤抓）、桌椅組、吧台凳、配件。C4 擔心的「sofa table 被當成沙發」在 C1 規則裡其實沒有發生（它本來就被歸到 table）。
- **同時命中兩個目標風格的商品不進任何格子**（例如 "rustic industrial"，共 8,040 件），因為不知道該算哪一格。

結果命中數比你之前看到的小很多，例如：

| 格子 | C1 定義下的命中數 | 這次（v1 規則、只算單一目標風格） |
|---|---|---|
| industrial × 吊燈 | 6,942 | 2,193 |
| boho × table | 595 | 88 |
| coastal × 吊燈 | 301 | 88 |
| boho × wall art | 8,976 | 6,768 |
| mid-century × chair | 3,897 | 3,427 |

（左欄是我用 C1 規則在同一批資料上重算的，farmhouse 和 rustic 已合併；`stage0/build_stats.json` 的 `c1_cell_hits_same_def`。）C4 說「30 格都 ≥ 202」，在新規則下**不成立**：boho × table 只有 88、coastal × 吊燈 88、boho × chair 115。

### 2.4 結果

- 下載清單 8,415 件，成功 8,415、失敗 0。圖片共 1.09 GB（上限 5 GB）。
- 同店同款（標題去重）在 30 格共去掉 7,114 件（14%）；pHash 再去掉 107 件。
- 入池 7,522 件。21 格滿 300 件；不滿的 9 格是：industrial × chair 176、industrial × wall art 161、boho × chair 88、boho × table 77、boho × lamp 146、boho × 吊燈 171、coastal × chair 153、coastal × table 173、coastal × 吊燈 77。
- 每格的命中數、去重後數量在第 4 節的大表。

### 2.5 代表什麼
- boho 和 coastal 的家具（椅、桌、吊燈）在 Amazon 上本來就少，關鍵字命中只有一兩百件。這兩個風格主要靠 wall art 撐量。
- pHash 的門檻（距離 ≤ 4）偏嚴：我看了 30 對被判重複的圖，大多是同款不同色，但距離 4 的 10 對裡有 2 對其實是不同商品。誤刪只是少一件，影響很小（`logs/phash_check_*.jpg`）。

---

## 3. 階段 1：怎麼標

### 3.1 為什麼做
C4 留下一個沒量過的數字：「標題寫某風格的商品，看起來真的是那個風格的比例」。沒有它就不知道每格能出幾題、階段 2 要標多少件。

### 3.2 怎麼做

- **準則 v1**（`stage1/guideline_v1.md`）：以 v0 為基礎，補了 C3 列的問題：燈具看燈座燈身不看燈罩（單頭吊燈沒有燈座，所以看燈罩）、多頭吊燈看整組的外圍輪廓、相近風格改用「依序套用的決定規則」、新增「掛畫怎麼看風格」。style 有 11 個選項（6 個目標 + modern minimalist、scandinavian、glam、other、mixed/none）。細節在 DECISIONS 第 12 條。
- **抽樣**（`stage1/make_sample.py`）：30 格各抽 30 件 = 900 件，打亂後編號 item_0001–0900。標註者只看到圖和編號，看不到標題、ASIN、格子。
- **三位標註者拿到完全一樣的東西**：同一段 system prompt（準則全文 + 輸出要求）、同一張縮到長邊 768 px 的圖。
  - Claude Opus 5.5：照 RUNBOOK 的精簡呼叫，一次 20 張，共 45 批（`annotate_claude.py`）。
  - Qwen3.8-27B-FP8、gemma-4-12b-it：本機 vLLM，一次 1 張，temperature 0（`annotate_local.py`、`serve_devset.sh`）。

真實輸入輸出例子（item_0450，「World Interiors Furniture Artezia Adjustable Metal Side Table」，一張鑄鐵腳的圓邊桌，格子是 industrial × table）：三位都輸出 `"style": "industrial", "category": "table", "color": "black"`。

### 3.3 執行狀況

| 標註者 | 成功 / 失敗 | 每件成本 | 備註 |
|---|---|---|---|
| Claude Opus 5.5 | 900 / 0 | $0.0092、約 1.8 秒 | 0 次重送；中途碰到一次五小時上限，重置後續跑 |
| Qwen3.8-27B-FP8 | 900 / 0 | 8.7 秒（共 131 分鐘） | 兩張 5090 |
| gemma-4-12b-it | 886 / 14 | 3.7 秒（共 56 分鐘） | 失敗的 14 件都是用了選項外的詞（ceramic、resin、tropical…），重試一次仍相同 |

- Gemma 失敗的 14 件，在「三方一致」和「可當合格」中都算成不一致（保守）；算 κ 時只用三位都成功的 886 件。
- **批量品質小檢查**（RUNBOOK 要求）：前 100 件抽 40 件改用每批 5 張重標，和每批 20 張比，style 90%、category 100%、color 95%、material 98%、shape 98% 一致。style 高於 85% 的門檻，所以維持每批 20 張。style 不一致的 4 件都牽涉 mixed/none（對上某個風格或 other），而且信心都 ≤ 2。**這也代表 Claude 自己重標一次，風格就有約 10% 會變。**

---

## 4. 結果：30 格（`results/stage1_analysis.md` 表 1）

欄位說明：
- (a) 關鍵字準確率 = 多數決風格等於格子風格的比例。
- (b) 三方一致 = 三位風格完全相同（不管是不是格子風格）。
- (c) 可當合格 = 三位一致、等於格子風格、而且沒有人給信心 1。
- (c2) = (c) 再加上三位的品項都等於規則品項。情境二需要風格和品項都對，所以**估可用量時我用 (c2)**。
- 推估合格商品數 = 去重後數量 × (c2)。括號是用 (c2) 的 95% 下界算的保守值。**每格只有 30 件，這些數字誤差很大，只能看量級。**

| 格子 | 命中總數 | 去重後 | (a) 關鍵字準確率 | (b) 三方一致 | (c) 可當合格 | (c2) 加上品項也對 | 推估合格商品數（去重後 × c2；括號 = 95% 下界） | 建議 |
|---|---|---|---|---|---|---|---|---|
| mid-century × chair | 3,427 | 2,546 | 63% | 63% | 47%（14/30） | 47%（14/30） | 1,188（770） | 保留 |
| mid-century × table | 1,129 | 975 | 70% | 60% | 47%（14/30） | 40%（12/30） | 390（240） | 保留 |
| mid-century × lamp | 505 | 449 | 47% | 57% | 37%（11/30） | 37%（11/30） | 165（98） | 保留 |
| mid-century × 吊燈 | 577 | 515 | 77% | 83% | 63%（19/30） | 47%（14/30） | 240（156） | 保留 |
| mid-century × wall art | 487 | 408 | 37% | 43% | 17%（5/30） | 13%（4/30） | 54（22） | 可留但貴（合格率 < 20%，要標很多件） |
| industrial × chair | 219 | 178 | 57% | 63% | 50%（15/30） | 43%（13/30） | 77（49） | 保留 |
| industrial × table | 1,774 | 1,549 | 77% | 77% | 63%（19/30） | 47%（14/30） | 723（468） | 保留 |
| industrial × lamp | 1,044 | 902 | 70% | 57% | 50%（15/30） | 47%（14/30） | 421（273） | 保留 |
| industrial × 吊燈 | 2,193 | 1,946 | 63% | 70% | 47%（14/30） | 43%（13/30） | 843（533） | 保留 |
| industrial × wall art | 192 | 164 | 37% | 33% | 20%（6/30） | 17%（5/30） | 27（12） | 勉強（量少：估計 13–26 件，或 95% 下界不到 13 件） |
| farmhouse/rustic × chair | 947 | 809 | 13% | 40% | 7%（2/30） | 7%（2/30） | 54（15） | 可留但貴（合格率 < 20%，要標很多件） |
| farmhouse/rustic × table | 3,711 | 3,223 | 43% | 63% | 27%（8/30） | 20%（6/30） | 645（306） | 保留 |
| farmhouse/rustic × lamp | 1,244 | 1,072 | 17% | 60% | 7%（2/30） | 7%（2/30） | 71（20） | 可留但貴（合格率 < 20%，要標很多件） |
| farmhouse/rustic × 吊燈 | 3,596 | 3,288 | 30% | 57% | 23%（7/30） | 23%（7/30） | 767（388） | 保留 |
| farmhouse/rustic × wall art | 9,096 | 8,177 | 60% | 63% | 50%（15/30） | 47%（14/30） | 3,816（2,472） | 保留 |
| boho × chair | 115 | 93 | 77% | 63% | 50%（15/30） | 50%（15/30） | 46（31） | 保留 |
| boho × table | 88 | 78 | 10% | 53% | 10%（3/30） | 3%（1/30） | 3（0） | 建議拿掉（合格商品估計不到 13 件） |
| boho × lamp | 194 | 172 | 23% | 60% | 20%（6/30） | 10%（3/30） | 17（6） | 勉強（量少：估計 13–26 件，或 95% 下界不到 13 件） |
| boho × 吊燈 | 195 | 172 | 73% | 67% | 63%（19/30） | 57%（17/30） | 97（67） | 保留 |
| boho × wall art | 6,768 | 5,212 | 80% | 83% | 67%（20/30） | 53%（16/30） | 2,780（1,884） | 保留 |
| coastal × chair | 177 | 163 | 33% | 47% | 23%（7/30） | 20%（6/30） | 33（15） | 保留 |
| coastal × table | 201 | 177 | 27% | 37% | 13%（4/30） | 10%（3/30） | 18（6） | 勉強（量少：估計 13–26 件，或 95% 下界不到 13 件） |
| coastal × lamp | 443 | 377 | 50% | 40% | 23%（7/30） | 23%（7/30） | 88（44） | 保留 |
| coastal × 吊燈 | 88 | 78 | 23% | 50% | 13%（4/30） | 13%（4/30） | 10（4） | 建議拿掉（合格商品估計不到 13 件） |
| coastal × wall art | 2,718 | 2,492 | 83% | 60% | 53%（16/30） | 47%（14/30） | 1,163（753） | 保留 |
| traditional × chair | 1,195 | 1,023 | 37% | 43% | 27%（8/30） | 27%（8/30） | 273（145） | 保留 |
| traditional × table | 1,546 | 1,282 | 53% | 67% | 40%（12/30） | 37%（11/30） | 470（280） | 保留 |
| traditional × lamp | 2,081 | 1,734 | 53% | 60% | 40%（12/30） | 40%（12/30） | 694（426） | 保留 |
| traditional × 吊燈 | 1,819 | 1,566 | 50% | 57% | 40%（12/30） | 40%（12/30） | 626（385） | 保留 |
| traditional × wall art | 1,570 | 1,405 | 7% | 63% | 7%（2/30） | 7%（2/30） | 94（26） | 可留但貴（合格率 < 20%，要標很多件） |

RUNBOOK 指定的 (d)「命中總數 × (c)」與 95% 區間、(e) 品項不符比例，在 `results/stage1_analysis.md` 表 1 有完整欄位；全體的 (e) 是 7%，最高的是 boho × table 37%、traditional × table 23%、farmhouse/rustic × table 20%。

### 依風格、依品項彙總

| 分組 | n | (a) | (b) | (c) | (c2) | (e) |
|---|---|---|---|---|---|---|
| mid_century | 150 | 59% | 61% | 42% | 37% | 2% |
| industrial | 150 | 61% | 60% | 46% | 39% | 7% |
| farmhouse_rustic | 150 | 33% | 57% | 23% | 21% | 7% |
| boho | 150 | 53% | 65% | 42% | 35% | 11% |
| coastal | 150 | 43% | 47% | 25% | 23% | 7% |
| traditional | 150 | 40% | 58% | 31% | 30% | 8% |
| chair | 180 | 47% | 53% | 34% | 32% | 5% |
| table | 180 | 47% | 59% | 33% | 26% | 18% |
| lamp | 180 | 43% | 56% | 29% | 27% | 2% |
| chandelier_pendant | 180 | 53% | 64% | 42% | 37% | 3% |
| wall_art | 180 | 51% | 58% | 36% | 31% | 7% |
| 全部 | 900 | 48% | 58% | 35% | 31% | 7% |

### 關鍵字錯的時候，商品其實是什麼（`stage1_analysis.md` 表 4）

- **farmhouse/rustic × chair（13%）**：多數決分布是 traditional 14、mixed/none 5、farmhouse/rustic 4、mid-century modern 3。這些被標成 traditional 的椅子，標題多是皮革釘扣單椅、躺椅、法式鄉村餐椅（例如 "Stone & Beam Appleton Farmhouse Leather Recliner"）。
- **farmhouse/rustic × 吊燈、lamp**：很多被標成 industrial（黑鐵 + 裸燈泡）。「rustic industrial」這類商品即使標題只寫 farmhouse，外觀也是工業風。
- **traditional × wall art（7%）**：other 20、bohemian 4、traditional 2。被標成 other 的 20 件裡，約一半是「Traditional Japanese / Chinese」的亞洲畫作或動漫掛軸，其餘是動物、照片等各種題材；"traditional" 在掛畫上不是指傳統古典風。**這一格的關鍵字基本上沒用。**
- **boho × table（10%）**、**boho × lamp（23%）**：boho 桌子最多被標成 scandinavian（9 件），其餘分散在 8 種以上；boho 燈有 17 件被標成 other，其中大多是土耳其 / 摩洛哥馬賽克燈和 Tiffany 彩繪玻璃燈（準則把這兩種歸在 other）。**如果你認為馬賽克燈算 boho，改準則就能救回這一格。**
- **mid-century × lamp**：10 件被標成 modern minimalist。標題的 "Mid Century Modern" 常常只是「現代」的意思。

### 代表什麼
- 關鍵字只能當「去哪裡找候選」的線索，不能當答案；而且不同格子的可信度差 10 倍（7% 到 83%）。
- 三方一致率（b）在各風格間差不多（47%–65%），但 (c) 差很多，因為很多「一致」是一致地說「這不是格子風格」。
- 品項規則大致可靠（不符 7%），但 table 偏高（18%）：多數決品項不是 table 的 33 件中，20 件被標成 cabinet/storage（帶抽屜或櫃門的邊桌、玄關桌），6 件 stool/ottoman，4 件 shelf。

---

## 5. 結果：各維度的一致性（`stage1_analysis.md` 表 3）

| 維度 | Fleiss κ | 三方一致 | Claude–Qwen | Claude–Gemma | Qwen–Gemma | 信心 1/2/3：Claude | Qwen | Gemma |
|---|---|---|---|---|---|---|---|---|
| style | 0.67 | 59% | 68% | 68% | 75% | 129/480/291 | 0/399/501 | 0/58/828 |
| category | 0.92 | 91% | 94% | 93% | 94% | 6/69/825 | 0/5/895 | 0/19/867 |
| color | 0.71 | 64% | 76% | 69% | 79% | 69/393/438 | 0/48/852 | 1/48/837 |
| material | 0.78 | 74% | 80% | 78% | 88% | 72/220/608 | 0/111/789 | 3/173/710 |
| shape | 0.73 | 73% | 86% | 78% | 79% | 39/318/543 | 0/110/790 | 0/143/743 |

最常見的風格分歧配對（同一件商品被不同標註者分別選了這兩個風格）：mixed/none ↔ modern minimalist：43 件；mid-century modern ↔ modern minimalist：28 件；mixed/none ↔ traditional：24 件；farmhouse/rustic ↔ traditional：23 件；mid-century modern ↔ mixed/none：22 件；farmhouse/rustic ↔ mixed/none：22 件。

### 代表什麼
- **category κ = 0.92**，和 C3 試標的 1.00 接近，品項可以放心用「規則 + 模型確認」。
- **style κ = 0.67**，比 C3 試標（三個 Claude，0.77）低。這是預期的：不同模型的偏誤不同，這個數字比較接近真實的不確定程度。
- 分歧主要在「有沒有風格」的邊界（mixed/none、modern minimalist 對上各種風格），其次是 mid-century ↔ modern minimalist、farmhouse ↔ traditional。**coastal ↔ bohemian 沒有進前十**，準則 v1 的決定規則看來有用。
- **「沒有人給信心 1」這個條件實際上只有 Claude 在把關**：Qwen 和 Gemma 幾乎從不給 1（Qwen style 信心 1 有 0 件、Gemma 0 件；Claude 129 件）。Gemma 有 93% 的 style 給 3，它的信心沒有鑑別力。
- color 的 κ（0.71）比 C3 試標（0.86）低，Claude–Gemma 只有 69%。Claude 和 Gemma 顏色不同的商品中，最多的是 brown ↔ natural wood（58 件），其次是 black ↔ metallic、beige/cream ↔ white（各 16 件）：都是相鄰選項的界線問題，準則可以再寫清楚（例如深色木紋算哪個）。

---

## 6. 成本、階段 2 推估、格子建議

### 6.1 實測成本（`results/stage1_analysis.json` 的 `claude_cost`、`local_cost`）

- **Claude Opus 5.5**：主標註 46 次呼叫（1 次碰到用量上限，花費 $0），900 件共 **$8.29**，每件 **$0.0092**。每件平均 tokens：寫入快取 639、讀快取 303、輸出 202（其中思考 101）。批量檢查另花 $0.42。**Claude 標註總花費 $8.71**（上限 $30）。
  - 比 RUNBOOK 預估的每件 $0.003–0.006 高，因為 Opus 5.5 預設會思考（輸出約一半是思考）。我沒有關掉它（DECISIONS 第 16 條）。
- **Qwen3.8-27B**：每件 8.7 秒；**gemma-4-12b**：每件 3.7 秒。兩個都各佔兩張 5090。每件輸入約 4,300 tokens，其中準則文字佔大部分（每次都重送整份準則）。
- 等卡：兩個模型 17:01 UTC 開始排隊，Gemma 18:09 做完、Qwen 20:22 做完，都沒有超過 4 小時。

### 6.2 階段 2 要標多少件

算法：每格需要的標註件數 = 目標合格件數 ÷ (c2)，最多標到該格的「去重後數量」；扣掉已經標的 30 件。Claude 美元 = 件數 × $0.0092。題數規劃依 main table 草稿第 4.2 節（每題 12 個合格商品）和 RUNBOOK（開發集情境一、二各 50 題 → 30 格平均每格約 1.7 題情境二）。

| 方案 | 還要新標幾件 | Claude 美元 | 五小時額度數 | Qwen 小時 | Gemma 小時 | 做不到的格子（c2 = 0） | 商品不夠的格子 |
|---|---|---|---|---|---|---|---|
| A_每格13件合格（同格題目共用） | 1,071 | $10 | 0.7–1.0 | 2.6 | 1.1 | — | boho|table、coastal|chandelier_pendant |
| B_每格26件合格（2題不重複） | 2,651 | $24 | 1.6–2.4 | 6.4 | 2.7 | — | boho|table、boho|lamp、coastal|table、coastal|chandelier_pendant |
| C_標完整個商品池（格子部分） | 6,622 | $61 | 4.1–6.1 | 16.0 | 6.9 | — | — |

- **方案 A**（每格 13 件 = 12 個合格 + 1 張 query 圖；同一格的幾題共用同一批合格商品）是最低需求。
- **方案 B**（每格 26 件，可以出 2 題而且合格商品不重複）比較符合 C4「不同題不要重複用同一批」的建議。
- **方案 C** 是把商品池的格子部分全部標完，之後出題最有彈性。
- 情境一（同風格跨品項）用的是同一批合格商品（同風格 5 格合起來），不需要另外標。困難干擾項（同品項、不同風格、高信心）也來自其他格的合格商品。
- **這些都是點估計**。(c2) 用 95% 下界算的話，件數大約是 1.6–3 倍（每格的數字在 `stage1_analysis.md` 最後一張表）。

### 6.3 材質多樣性的問題（要你決定）

main table 草稿要求情境二的合格商品在每個自由維度（color、material、shape）都至少有 4 種值。我看了每格目前 (c2) 合格商品的多數決屬性有幾種不同值（`stage1_analysis.md` 最後一張表）。合格商品 ≥ 10 件、但材質只有 1 種的格子有 8 格：mid-century × table、mid-century × lamp、industrial × chair、industrial × lamp、industrial × 吊燈、boho × 吊燈、traditional × table、traditional × 吊燈。

原因很直接：同一品項的主要材質本來就集中（桌子看桌面 → wood；吊燈看燈體 → metal；掛畫 → paper/canvas）。樣本只有十幾件，多標之後值會變多，但 material 要到 4 種在很多格看起來很難。可能的做法：(1) 情境二的自由維度依品項決定（例如掛畫不算 material）；(2) 把門檻從 4 種降到 2–3 種（草稿的定義本來就是「合格候選中 ≥ 2 種值才算自由維度」）；(3) 材質改標「次要材質」。我沒有動任何設定，這需要你和教授決定。

### 6.4 格子建議

判斷規則（`analyze.py`）：用「去重後數量 × (c2)」估這一格有幾件合格商品。≥ 26 件、95% 下界 ≥ 13 件、而且 (c2) ≥ 20% → 保留；(c2) < 20% → 可留但貴；估計 13–26 件或下界不到 13 → 勉強；不到 13 件 → 建議拿掉。

- **保留**（21 格）：mid-century × chair、mid-century × table、mid-century × lamp、mid-century × 吊燈、industrial × chair、industrial × table、industrial × lamp、industrial × 吊燈、farmhouse/rustic × table、farmhouse/rustic × 吊燈、farmhouse/rustic × wall art、boho × chair、boho × 吊燈、boho × wall art、coastal × chair、coastal × lamp、coastal × wall art、traditional × chair、traditional × table、traditional × lamp、traditional × 吊燈
- **可留但貴**（4 格）：mid-century × wall art、farmhouse/rustic × chair、farmhouse/rustic × lamp、traditional × wall art
- **勉強**（3 格）：industrial × wall art、boho × lamp、coastal × table
- **建議拿掉**（2 格）：boho × table、coastal × 吊燈

補充：
- 「建議拿掉」的兩格是資料不夠，不是標註問題：商品池已經是這兩格去重後的全部商品（各 78 件左右），全標完也湊不到 13 件。
- 「可留但貴」的 traditional × wall art 我建議也拿掉或改關鍵字：(a) 只有 7%，問題出在 "traditional" 這個字在掛畫標題裡的意思不同。mid-century × wall art 的合格商品在三個自由維度都只有 1 種值（都是長方形、多色、紙），情境二很難出題。
- farmhouse/rustic × chair、× lamp 的合格率只有 7%，但去重後有 809 和 1,072 件可以標；要不要花這個錢由你決定（每格約 200–400 件、$2–4）。
- 整體來看，mid-century 和 industrial 最穩（5 格中 4 格可保留），coastal 和 boho 的家具最弱。如果想讓每個風格的品項數一致，可以考慮把品項縮成 4 個或把 coastal / boho 的弱格換成 C1 表中量較多的品項（例如 boho 的 rug、throw pillow），但那需要重新跑階段 0，我沒有做。

---

## 7. 限制

1. **每格只有 30 件**，比例的 95% 區間很寬（例如 14/30 = 47% 的區間是 30%–64%）。表裡的可用量只能看量級。
2. **三位標註者都是模型，沒有人工答案。** 三方一致不等於正確（C3 試標就看過三位一致但和人工不同的例子）。`stage1/review_sample.json` 有 60 件給你抽查（每格 2 件，優先挑三方不一致的：{'三方風格各不相同': 40, '風格 2 比 1 或有標註失敗': 20}）。要注意這 60 件是刻意挑難的，**不能用它估整體正確率**；要估「合格商品的錯誤率」得另外從 (c) 合格的商品裡隨機抽。
3. 準則裡有兩條人為約定（素面藤編 → bohemian；黑鐵架 + 木板 → industrial），會直接影響 boho、coastal、industrial、farmhouse 的數字，請確認是否同意。
4. 命中數的定義和 C1 / C4 不同（第 2.3 節），不能直接和之前的表比。
5. Qwen 在 server 端另有 max_pixels 409600，會把 768 px 的圖再縮到約 640 px；所以它看到的解析度略低於另外兩位。
6. 等待 Claude 批次時，我用了一個比對字串太寬的 `pkill -f "until ! pgrep"` 想停掉自己的等待迴圈。它對其他使用者的程序回報 Operation not permitted（沒有殺掉），但**如果你自己當時有別的 shell 正好在跑含這段字的迴圈，可能被我停掉了**。vLLM、watch.sh、標註程序都沒受影響。

---

## 8. 重算指令

```bash
cd /mnt/raid0/home/skyler/vlm-diverse-retrieval
.venv/bin/python -B devset_v0/stage0/s0_scan.py          # 掃四個子集（約 4 分鐘）
.venv/bin/python -B devset_v0/stage0/s0_build_pool.py    # 品項規則、命中數、標題去重、下載清單（約 10 秒）
.venv/bin/python -B devset_v0/stage0/s0_download.py      # 下載主圖（已有的跳過）
.venv/bin/python -B devset_v0/stage0/s0_finalize.py      # pHash 去重 → pool.jsonl、cell_counts.json
.venv/bin/python -B devset_v0/stage1/make_sample.py      # 抽樣 + 768 px 縮圖
python3 -I devset_v0/stage1/analyze.py                   # 只重算分析（幾秒）
python3 -I devset_v0/make_report.py                      # 重新產生這份報告
python3 -I devset_v0/verify.py                           # 自我驗收
```

標註本身（要花額度 / 佔 GPU，已完成的會跳過）：`python3 -I devset_v0/stage1/annotate_claude.py --batches 1-45`、`bash devset_v0/stage1/job_local.sh qwen38-27b`、`bash devset_v0/stage1/job_local.sh gemma4-12b`。

---

## 9. 需要 Skyler 決定的事

1. **格子**：是否照第 6.4 節拿掉 boho × table、coastal × 吊燈（以及我建議一起拿掉的 traditional × wall art）？「勉強」和「可留但貴」的格子要不要留？
2. **階段 2 的規模**：方案 A（約 $10）、B（約 $24）還是 C（約 $61）？我的建議是 B，並且先人工抽查 `review_sample.json` 再開始。
3. **材質多樣性**（第 6.3 節）：情境二「每個自由維度 ≥ 4 種值」在 material 上很難達成，要改門檻、改自由維度的定義，還是改材質的標法？
4. **品項規則 v1** 是否接受（特別是：吊燈不含吸頂燈、lamp 不含 desk lamp、wall art 含掛毯與壁掛雕塑、多風格關鍵字商品不進格子）？
5. **準則的兩條人為約定**（素面藤編 → bohemian；黑鐵架 + 木板 → industrial）是否同意？
6. **Claude 要不要關掉思考**：現在每件 $0.0092，輸出約一半是思考 tokens。關掉可能更便宜，但標註結果會變，階段 1 這 900 件就要重標才能和階段 2 一致。
7. **信心門檻**：Qwen、Gemma 幾乎不給信心 1，「沒有人給信心 1」實際上只靠 Claude。要不要改成別的不確定指標（例如 Claude 重標兩次是否一致）？
8. 要不要加回「主圖是否只有單一商品」欄位（挑 query 圖時需要；這次依 RUNBOOK 的欄位清單沒有標）。

## 10. 自我驗收（2026-11-17 02:5x UTC，`python3 -I devset_v0/verify.py`）

| 檢查 | 結果 |
|---|---|
| 重跑 `analyze.py` 和 `make_report.py`，`stage1_analysis.json` / `.md`、`review_sample.json`、本報告的 md5 都不變 | 通過 |
| 報告第 4 節的 30 格表，每一列的命中數、去重後、(a)(b)(c)(c2) 和 `results/stage1_analysis.json` 一致 | 通過（30 列、0 列不一致） |
| `pool.jsonl` 筆數 = `cell_counts.json` 的 n_pool；每件的圖都在；parent_asin 不重複 | 通過（7,522 件） |
| 三位標註者各有 900 筆紀錄；Claude 實際回應的模型只有 `claude-opus-5-5` | 通過 |
| 沒有殘留的自己的 vLLM（served name 含 `devset_2026-11-17`），port 8081–8089 沒有被佔用 | 通過 |
| 啟動後（11-16 15:29 UTC）`R/` 底下、`devset_v0/` 與 `data/derived/devset_images/` 以外被修改的檔案 | 0 個 |

沒有驗證的部分（如實說明）：
- 報告裡的文字說明（例如「被標成 other 的多是馬賽克燈」）是我查了對應商品的標題後寫的，沒有自動檢查。
- 標註內容本身沒有人工答案可比；我只看了 8 張圖確認「圖 ↔ 編號 ↔ 標註」沒有錯位（`logs/sanity_sheet.jpg`）。
- `R/scripts/.vllm_start.lock`（既有的空鎖檔）被我的啟動腳本以唯讀方式開啟來排隊，內容與修改時間沒有變。
- 沒下載模型、沒裝套件、沒呼叫 Gemini 或其他付費 API、沒有 git push、沒有發布 artifact；除了 RUNBOOK 3.3 的 `claude -p` 標註呼叫（54 次，共 $8.71）沒有用 subagent。
