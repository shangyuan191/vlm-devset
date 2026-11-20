# 階段 1 分析（自動產生：`python3 -I devset_v0/stage1/analyze.py`）

樣本 900 件（30 格 × 30）。標註狀態：Claude Opus 5.5 成功 900、失敗 0、未標 0；Qwen3.8-27B-FP8 成功 900、失敗 0、未標 0；gemma-4-12b-it 成功 886、失敗 14、未標 0

## 表 1：30 格

欄位：(a) 多數決風格 = 格子風格；(b) 三位風格完全一致；(c) 三位一致 = 格子風格且無人信心 1；(c2) = (c) 且三位品項都 = 規則品項；(d) 命中總數 × (c)，括號是 95% 區間（Wilson，n=30）；(e) 多數決品項 ≠ 規則品項。標註失敗的商品在 (b)(c) 算「不一致」。

| 格子 | 命中總數 | 去重後 | (a) 關鍵字準確率 | (b) 三方一致 | (c) 可當合格 | (c) 95% 區間 | (c2) | (d) 推估可用量（命中） | (d) 去重後 | (e) 品項不符 | 建議 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mid_century × chair | 3,427 | 2,546 | 63% | 63% | 47%（14/30） | 30%–64% | 47% | 1,599（1,036–2,188） | 1,188（770–1,626） | 3% | 保留 |
| mid_century × table | 1,129 | 975 | 70% | 60% | 47%（14/30） | 30%–64% | 40% | 527（341–721） | 455（295–623） | 3% | 保留 |
| mid_century × lamp | 505 | 449 | 47% | 57% | 37%（11/30） | 22%–54% | 37% | 185（110–275） | 165（98–245） | 0% | 保留 |
| mid_century × chandelier_pendant | 577 | 515 | 77% | 83% | 63%（19/30） | 46%–78% | 47% | 365（263–451） | 326（234–402） | 0% | 保留 |
| mid_century × wall_art | 487 | 408 | 37% | 43% | 17%（5/30） | 7%–34% | 13% | 81（36–163） | 68（30–137） | 3% | 可留但貴（合格率 < 20%，要標很多件） |
| industrial × chair | 219 | 178 | 57% | 63% | 50%（15/30） | 33%–67% | 43% | 110（73–146） | 89（59–119） | 7% | 保留 |
| industrial × table | 1,774 | 1,549 | 77% | 77% | 63%（19/30） | 46%–78% | 47% | 1,124（807–1,386） | 981（705–1,210） | 13% | 保留 |
| industrial × lamp | 1,044 | 902 | 70% | 57% | 50%（15/30） | 33%–67% | 47% | 522（346–698） | 451（299–603） | 0% | 保留 |
| industrial × chandelier_pendant | 2,193 | 1,946 | 63% | 70% | 47%（14/30） | 30%–64% | 43% | 1,023（663–1,400） | 908（588–1,243） | 7% | 保留 |
| industrial × wall_art | 192 | 164 | 37% | 33% | 20%（6/30） | 10%–37% | 17% | 38（18–72） | 33（16–61） | 10% | 勉強（量少：估計 13–26 件，或 95% 下界不到 13 件） |
| farmhouse_rustic × chair | 947 | 809 | 13% | 40% | 7%（2/30） | 2%–21% | 7% | 63（17–202） | 54（15–173） | 3% | 可留但貴（合格率 < 20%，要標很多件） |
| farmhouse_rustic × table | 3,711 | 3,223 | 43% | 63% | 27%（8/30） | 14%–44% | 20% | 990（526–1,649） | 859（457–1,433） | 20% | 保留 |
| farmhouse_rustic × lamp | 1,244 | 1,072 | 17% | 60% | 7%（2/30） | 2%–21% | 7% | 83（23–265） | 71（20–229） | 7% | 可留但貴（合格率 < 20%，要標很多件） |
| farmhouse_rustic × chandelier_pendant | 3,596 | 3,288 | 30% | 57% | 23%（7/30） | 12%–41% | 23% | 839（424–1,472） | 767（388–1,346） | 3% | 保留 |
| farmhouse_rustic × wall_art | 9,096 | 8,177 | 60% | 63% | 50%（15/30） | 33%–67% | 47% | 4,548（3,016–6,080） | 4,088（2,711–5,466） | 3% | 保留 |
| boho × chair | 115 | 93 | 77% | 63% | 50%（15/30） | 33%–67% | 50% | 58（38–77） | 46（31–62） | 3% | 保留 |
| boho × table | 88 | 78 | 10% | 53% | 10%（3/30） | 3%–26% | 3% | 9（3–23） | 8（3–20） | 37% | 建議拿掉（合格商品估計不到 13 件） |
| boho × lamp | 194 | 172 | 23% | 60% | 20%（6/30） | 10%–37% | 10% | 39（18–72） | 34（16–64） | 3% | 勉強（量少：估計 13–26 件，或 95% 下界不到 13 件） |
| boho × chandelier_pendant | 195 | 172 | 73% | 67% | 63%（19/30） | 46%–78% | 57% | 124（89–152） | 109（78–134） | 0% | 保留 |
| boho × wall_art | 6,768 | 5,212 | 80% | 83% | 67%（20/30） | 49%–81% | 53% | 4,512（3,301–5,466） | 3,475（2,542–4,210） | 13% | 保留 |
| coastal × chair | 177 | 163 | 33% | 47% | 23%（7/30） | 12%–41% | 20% | 41（21–72） | 38（19–67） | 7% | 保留 |
| coastal × table | 201 | 177 | 27% | 37% | 13%（4/30） | 5%–30% | 10% | 27（11–60） | 24（9–53） | 13% | 勉強（量少：估計 13–26 件，或 95% 下界不到 13 件） |
| coastal × lamp | 443 | 377 | 50% | 40% | 23%（7/30） | 12%–41% | 23% | 103（52–181） | 88（44–154） | 3% | 保留 |
| coastal × chandelier_pendant | 88 | 78 | 23% | 50% | 13%（4/30） | 5%–30% | 13% | 12（5–26） | 10（4–23） | 3% | 建議拿掉（合格商品估計不到 13 件） |
| coastal × wall_art | 2,718 | 2,492 | 83% | 60% | 53%（16/30） | 36%–70% | 47% | 1,450（982–1,896） | 1,329（901–1,739） | 7% | 保留 |
| traditional × chair | 1,195 | 1,023 | 37% | 43% | 27%（8/30） | 14%–44% | 27% | 319（169–531） | 273（145–455） | 7% | 保留 |
| traditional × table | 1,546 | 1,282 | 53% | 67% | 40%（12/30） | 25%–58% | 37% | 618（380–892） | 513（315–739） | 23% | 保留 |
| traditional × lamp | 2,081 | 1,734 | 53% | 60% | 40%（12/30） | 25%–58% | 40% | 832（512–1,200） | 694（426–1,000） | 0% | 保留 |
| traditional × chandelier_pendant | 1,819 | 1,566 | 50% | 57% | 40%（12/30） | 25%–58% | 40% | 728（447–1,049） | 626（385–903） | 7% | 保留 |
| traditional × wall_art | 1,570 | 1,405 | 7% | 63% | 7%（2/30） | 2%–21% | 7% | 105（29–335） | 94（26–300） | 3% | 可留但貴（合格率 < 20%，要標很多件） |

## 表 2：依風格、依品項彙總

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

各標註者自己標的風格 = 格子風格的比例：Claude Opus 5.5 49%、Qwen3.8-27B-FP8 48%、gemma-4-12b-it 47%

## 表 3：各維度一致性

只用三位都有合法標註的 886 件。

| 維度 | Fleiss κ | 三方一致 | Claude–Qwen | Claude–Gemma | Qwen–Gemma | 信心 1/2/3：Claude | Qwen | Gemma |
|---|---|---|---|---|---|---|---|---|
| style | 0.67 | 59% | 68% | 68% | 75% | 129/480/291 | 0/399/501 | 0/58/828 |
| category | 0.92 | 91% | 94% | 93% | 94% | 6/69/825 | 0/5/895 | 0/19/867 |
| color | 0.71 | 64% | 76% | 69% | 79% | 69/393/438 | 0/48/852 | 1/48/837 |
| material | 0.78 | 74% | 80% | 78% | 88% | 72/220/608 | 0/111/789 | 3/173/710 |
| shape | 0.73 | 73% | 86% | 78% | 79% | 39/318/543 | 0/110/790 | 0/143/743 |

最常見的風格分歧配對（同一件商品被不同標註者分別選了這兩個風格的件數）：

- mixed/none ↔ modern minimalist：43
- mid-century modern ↔ modern minimalist：28
- mixed/none ↔ traditional：24
- farmhouse/rustic ↔ traditional：23
- mid-century modern ↔ mixed/none：22
- farmhouse/rustic ↔ mixed/none：22
- mixed/none ↔ other：20
- industrial ↔ modern minimalist：18
- bohemian ↔ other：16
- coastal ↔ farmhouse/rustic：16

## 表 4：每格多數決風格的分布（看關鍵字錯的時候被標成什麼）

| 格子 | 多數決風格分布 |
|---|---|
| mid_century × chair | mid-century modern 19、modern minimalist 4、scandinavian 3、traditional 2、(無多數) 1、glam 1 |
| mid_century × table | mid-century modern 21、scandinavian 4、modern minimalist 3、traditional 1、(無多數) 1 |
| mid_century × lamp | mid-century modern 14、modern minimalist 10、(無多數) 3、glam 2、coastal 1 |
| mid_century × chandelier_pendant | mid-century modern 23、modern minimalist 4、traditional 1、scandinavian 1、glam 1 |
| mid_century × wall_art | mid-century modern 11、other 9、modern minimalist 4、traditional 3、coastal 2、bohemian 1 |
| industrial × chair | industrial 17、modern minimalist 3、(無多數) 3、mid-century modern 2、mixed/none 1、glam 1、farmhouse/rustic 1、traditional 1、bohemian 1 |
| industrial × table | industrial 23、(無多數) 2、modern minimalist 2、scandinavian 1、glam 1、traditional 1 |
| industrial × lamp | industrial 21、modern minimalist 4、(無多數) 2、mid-century modern 2、glam 1 |
| industrial × chandelier_pendant | industrial 19、mid-century modern 5、(無多數) 3、traditional 1、farmhouse/rustic 1、modern minimalist 1 |
| industrial × wall_art | industrial 11、other 8、(無多數) 4、mixed/none 3、modern minimalist 2、traditional 1、scandinavian 1 |
| farmhouse_rustic × chair | traditional 14、mixed/none 5、farmhouse/rustic 4、mid-century modern 3、(無多數) 2、modern minimalist 2 |
| farmhouse_rustic × table | farmhouse/rustic 13、industrial 9、traditional 2、modern minimalist 2、mid-century modern 2、bohemian 1、other 1 |
| farmhouse_rustic × lamp | traditional 7、industrial 6、farmhouse/rustic 5、modern minimalist 4、(無多數) 3、glam 2、other 2、bohemian 1 |
| farmhouse_rustic × chandelier_pendant | industrial 12、farmhouse/rustic 9、modern minimalist 4、glam 2、bohemian 1、traditional 1、(無多數) 1 |
| farmhouse_rustic × wall_art | farmhouse/rustic 18、other 5、traditional 4、bohemian 1、glam 1、coastal 1 |
| boho × chair | bohemian 23、mid-century modern 3、glam 1、(無多數) 1、scandinavian 1、mixed/none 1 |
| boho × table | scandinavian 9、modern minimalist 3、glam 3、bohemian 3、industrial 3、mid-century modern 3、farmhouse/rustic 2、coastal 1、traditional 1、(無多數) 1、other 1 |
| boho × lamp | other 17、bohemian 7、(無多數) 2、glam 2、scandinavian 1、traditional 1 |
| boho × chandelier_pendant | bohemian 22、glam 2、traditional 1、farmhouse/rustic 1、mid-century modern 1、industrial 1、(無多數) 1、other 1 |
| boho × wall_art | bohemian 24、other 4、modern minimalist 1、farmhouse/rustic 1 |
| coastal × chair | coastal 10、(無多數) 6、farmhouse/rustic 5、bohemian 2、scandinavian 2、mixed/none 2、other 1、traditional 1、modern minimalist 1 |
| coastal × table | farmhouse/rustic 10、coastal 8、(無多數) 2、bohemian 2、modern minimalist 2、scandinavian 2、mixed/none 1、other 1、traditional 1、mid-century modern 1 |
| coastal × lamp | coastal 15、(無多數) 5、industrial 4、other 2、glam 2、modern minimalist 1、bohemian 1 |
| coastal × chandelier_pendant | coastal 7、glam 5、farmhouse/rustic 4、(無多數) 3、traditional 3、bohemian 3、industrial 3、modern minimalist 2 |
| coastal × wall_art | coastal 25、other 2、farmhouse/rustic 1、traditional 1、mid-century modern 1 |
| traditional × chair | traditional 11、modern minimalist 7、mixed/none 4、farmhouse/rustic 3、industrial 2、mid-century modern 1、(無多數) 1、glam 1 |
| traditional × table | traditional 16、(無多數) 4、farmhouse/rustic 4、glam 3、modern minimalist 3 |
| traditional × lamp | traditional 16、(無多數) 4、glam 3、modern minimalist 3、other 2、mid-century modern 1、coastal 1 |
| traditional × chandelier_pendant | traditional 15、industrial 5、(無多數) 3、modern minimalist 2、farmhouse/rustic 1、coastal 1、other 1、mixed/none 1、glam 1 |
| traditional × wall_art | other 20、bohemian 4、traditional 2、mixed/none 1、coastal 1、modern minimalist 1、(無多數) 1 |

## 成本

- Claude（claude-opus-5-5）：主標註 46 次呼叫（其中 1 次碰到用量上限、0 次是重送），成功 900 件，共 $8.29，**每件 $0.0092**；每件 tokens：{'input': 0.1, 'cache_write': 639.3, 'cache_read': 302.6, 'output': 201.8, 'thinking': 100.7}；每件 1.7687 秒。批量檢查另花 $0.42；全部呼叫合計 $8.71。
- 批量檢查（每批 20 vs 每批 5，40 件）一致率：{'style': 0.9, 'category': 1.0, 'color': 0.95, 'material': 0.975, 'shape': 0.975}
- Qwen3.8-27B-FP8：900 件、成功 900、重試過 0；每件 8.71 秒（共 131 分鐘）；每件輸入約 4290.3 tokens。失敗原因：無
- gemma-4-12b-it：900 件、成功 886、重試過 14；每件 3.73 秒（共 56 分鐘）；每件輸入約 4254.1 tokens。失敗原因：{"ValueError: material='ceramic' not in options": 8, "ValueError: material='resin' not in options": 3, "ValueError: style='pop art' not in options": 1, "ValueError: style='tropical' not in options": 1, "ValueError: color='red' not in options": 1}

## 階段 2 推估

用 (c2)（風格合格且品項正確）的點估計；每格最多標到「去重後數量」。1 個五小時額度 ≈ $10–15（經驗值）。

| 方案 | 還要新標幾件 | Claude 美元 | 五小時額度數 | Qwen 小時 | Gemma 小時 | 做不到的格子（c2 = 0） | 商品不夠的格子 |
|---|---|---|---|---|---|---|---|
| A_每格13件合格（同格題目共用） | 1,071 | $10 | 0.7–1.0 | 2.6 | 1.1 | — | boho|table、coastal|chandelier_pendant |
| B_每格26件合格（2題不重複） | 2,651 | $24 | 1.6–2.4 | 6.4 | 2.7 | — | boho|table、boho|lamp、coastal|table、coastal|chandelier_pendant |
| C_標完整個商品池（格子部分） | 6,622 | $61 | 4.1–6.1 | 16.0 | 6.9 | — | — |

每格需要標的總件數（方案 A / B；括號 = 用 (c2) 的 95% 下界算）與合格商品在自由維度上的不同值數：

| 格子 | (c2) | A 總件數 | B 總件數 | 去重後數量 | 合格商品的不同值數（color / material / shape） |
|---|---|---|---|---|---|
| mid_century × chair | 14/30 | 28（44） | 56（87） | 2,546 | 8 / 4 / 2 |
| mid_century × table | 12/30 | 33（53） | 65（106） | 975 | 3 / 1 / 3 |
| mid_century × lamp | 11/30 | 36（60） | 71（119） | 449 | 2 / 1 / 4 |
| mid_century × chandelier_pendant | 14/30 | 28（44） | 56（87） | 515 | 2 / 2 / 3 |
| mid_century × wall_art | 4/30 | 98（245） | 196（490） | 408 | 1 / 1 / 1 |
| industrial × chair | 13/30 | 31（48） | 61（95） | 178 | 4 / 1 / 2 |
| industrial × table | 14/30 | 28（44） | 56（87） | 1,549 | 3 / 2 / 2 |
| industrial × lamp | 14/30 | 28（44） | 56（87） | 902 | 2 / 1 / 5 |
| industrial × chandelier_pendant | 13/30 | 31（48） | 61（95） | 1,946 | 2 / 1 / 4 |
| industrial × wall_art | 5/30 | 78（178） | 156（355） | 164 | 3 / 1 / 1 |
| farmhouse_rustic × chair | 2/30 | 195（704） | 390（1408） | 809 | 2 / 1 / 2 |
| farmhouse_rustic × table | 6/30 | 65（137） | 130（274） | 3,223 | 4 / 1 / 1 |
| farmhouse_rustic × lamp | 2/30 | 195（704） | 390（1408） | 1,072 | 2 / 1 / 2 |
| farmhouse_rustic × chandelier_pendant | 7/30 | 56（111） | 112（221） | 3,288 | 3 / 1 / 4 |
| farmhouse_rustic × wall_art | 14/30 | 28（44） | 56（87） | 8,177 | 5 / 3 / 2 |
| boho × chair | 15/30 | 26（40） | 52（79） | 93 | 6 / 2 / 3 |
| boho × table | 1/30 | 391（2201） | 781（4401） | 78 | 1 / 1 / 1 |
| boho × lamp | 3/30 | 130（376） | 260（752） | 172 | 2 / 2 / 2 |
| boho × chandelier_pendant | 17/30 | 23（34） | 46（67） | 172 | 6 / 1 / 3 |
| boho × wall_art | 16/30 | 25（36） | 49（72） | 5,212 | 2 / 2 / 2 |
| coastal × chair | 6/30 | 65（137） | 130（274） | 163 | 3 / 4 / 2 |
| coastal × table | 3/30 | 130（376） | 260（752） | 177 | 2 / 2 / 1 |
| coastal × lamp | 7/30 | 56（111） | 112（221） | 377 | 5 / 6 / 4 |
| coastal × chandelier_pendant | 4/30 | 98（245） | 196（490） | 78 | 2 / 2 / 2 |
| coastal × wall_art | 14/30 | 28（44） | 56（87） | 2,492 | 6 / 3 / 3 |
| traditional × chair | 8/30 | 49（92） | 98（184） | 1,023 | 6 / 4 / 2 |
| traditional × table | 11/30 | 36（60） | 71（119） | 1,282 | 3 / 1 / 2 |
| traditional × lamp | 12/30 | 33（53） | 65（106） | 1,734 | 3 / 3 / 2 |
| traditional × chandelier_pendant | 12/30 | 33（53） | 65（106） | 1,566 | 3 / 1 / 2 |
| traditional × wall_art | 2/30 | 195（704） | 390（1408） | 1,405 | 1 / 1 / 1 |

人工抽查樣本：`stage1/review_sample.json`，60 件（{'三方風格各不相同': 40, '風格 2 比 1 或有標註失敗': 20}）。
