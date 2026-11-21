# DECISIONS（開發集 v0，無人值守 agent 自己做的判斷）

每一條：判斷 → 理由。

## 階段 0
1. **來源只用 home、lighting、patio、handmade 四個子集（subset 版，不是 complete）**。dining 子集在 C1 用另一套品項規則（餐具類），不會產生這 5 個品項。四個檔的列數和 C1「總量」表一致（`stage0/scan_summary.json`）。
2. **品項規則改成「類別路徑白名單」（v1），不再用標題關鍵字補抓**（`stage0/s0_build_pool.py` 的 `PATH_RULES`）。理由：檢查 C1 規則在有風格字詞的商品上的類別路徑後，標題補抓的幾乎都是誤抓（table：裝飾托盤、假南瓜、胡桃鉗、乾燥花、桌布；lamp：油燈、夜燈、鹽燈、戶外柱燈；wall art：捕夢網、花圈、掛飾；chair：椅墊、懶骨頭）。
   - chair：客廳 / 餐廳 / 辦公椅、戶外椅（餐椅、躺椅、Adirondack、搖椅）、吊椅（Hammock Chairs）。**不收**：電競椅、兒童椅、懶骨頭、摺疊椅、導演椅、劇院座椅、Gliders。
   - table：茶几、邊桌、玄關桌（Sofa & Console Tables，C1 規則本來就把它歸 table，沒有被當成沙發）、套桌、餐桌、戶外桌。**不收**：吧台櫃、摺疊桌、TV 托盤、繪圖桌、野餐桌、兒童桌、桌面 / 桌腳零件。
   - lamp：**只收 Table Lamps、Floor Lamps**（RUNBOOK 寫明桌燈、落地燈）。不收 Desk Lamps（多為功能性 LED 檯燈）、Lamp Sets、夜燈、鹽燈、油燈、戶外燈。
   - chandelier/pendant：Chandeliers、Pendant Lights、Island Lights、戶外 Pendant。**不收 Close To Ceiling Lights（吸頂燈 / 半吸頂）、軌道燈、撞球桌燈**——RUNBOOK 寫的是「吊燈」，吸頂燈外形不同。這讓格子命中數比 C1 少很多（例如 industrial 吊燈 C1 定義 6,936 → 2,193）。
   - wall art：海報、畫、照片、混合媒材、**掛毯（Tapestries）、壁掛雕塑（Wall Sculptures）**（沿用 C1 的範圍）。不收牆貼、壁飾雜項（Wall Pediments 等）、兒童房壁飾。
3. **標題排除字**（`TITLE_EXCLUDE`）：chair 排除按摩 / 電動起身 / 加熱（C4 示範 #1）、吧台凳、桌椅組、椅墊椅套；table 排除含 chair / stool / bench 的成套商品與桌布桌腳等配件；燈具排除 replacement、燈罩單賣、配件；wall art 排除 decal / sticker。
4. **格子 = 6 個目標風格中「剛好命中 1 個」**（標題或 details 的 Style 欄，C1 的 STYLE_REGEX，farmhouse 與 rustic 合併）。同時命中兩個目標風格的（例如 rustic industrial）不進任何格子（共 8,040 件，吊燈最多 3,192），因為它的「格子風格」不明確，會把關鍵字準確率算亂。所以**命中總數比 C1 / C4 的數字小**（C1 是多風格重複計、且含標題補抓）。命中非目標風格字詞（modern、vintage…）不影響。
5. **只用有 MAIN 主圖的商品**；優先 hi_res，沒有才用 large（下載清單中 hi_res 7,657、large 758）。
6. **去重複順序**：先對每格全部命中商品做「同 store + 標題 Jaccard ≥ 0.8」去重（得到「去重後數量」，不必下載圖），再依 seed 0 的隨機順序取前 300 件；另外多下載 40 件當遞補，下載失敗或 pHash 重複時依序補上，讓入池數盡量維持 300。隨機順序 = `random.Random('0-<風格>-<品項>').shuffle(依 parent_asin 排序的清單)`。去重是跨格的（同一家店的同款若出現在兩格，只留先處理的那格）。沒有 store 的商品（63 件）不做標題去重，只靠 pHash。
7. **標題去重時去掉的字**：顏色詞、尺寸詞、數字（清單在 `s0_build_pool.py` 的 `COLOR`、`SIZE`）。
9. **pHash 門檻 = Hamming 距離 ≤ 4（64 bit）**，自己用 PIL + numpy 實作（R/.venv 沒有 imagehash）。共去掉 107 件（距離 0：65、2：18、4：24；`stage0/phash_dups.json`）。看了 30 對（`logs/phash_check_*.jpg`）：大多是同款不同色或同一張圖重複上架（boho lamp 一格就有 26 件是同一款彩色投影燈）；距離 4 的 10 對中有 2 對其實是不同商品（白底上輪廓相似）。誤刪只是少一件商品，漏掉同款會讓模型靠同款刷多樣性，所以寧可偏嚴。
10. **下載**：8,415 件全部成功（0 失敗），共 1.09 GB（上限 5 GB）。入池 7,522 件；沒用到的遞補圖留在 `devset_images/`（不在 pool.jsonl 內）。

## 階段 1
11. **RUNBOOK 3.3 在 16:58 更新**（精簡呼叫、768 px 縮圖、每批 20 張、5 張重標檢查）。我照新版做。原本我打算加一個 `single_item` 欄位（C1 / D 文件建議的「主圖是否只有單一商品」），但新版 RUNBOOK 明列了輸出欄位（不含它），所以**拿掉**；階段 2 要挑 query 圖時再決定要不要加。
12. **準則 v1 的微調**（`stage1/guideline_v1.md`）：
    - category 加 `chandelier/pendant`、`other lighting`（吸頂燈、壁燈等）、`wall art`；v0 的 `stool/ottoman` 等保留。
    - material 加 `paper/canvas`（v0 沒有適合掛畫的選項）。
    - 燈具規則：`lamp` 的顏色 / 材質 / 形狀看燈座燈身不看燈罩；`chandelier/pendant` 看燈體主要結構，單頭吊燈看燈罩（它沒有燈座）；多部件商品的形狀看「整組的外圍輪廓」。
    - 相近風格用「依序套用的決定規則」而不是只給描述：MCM / 北歐 / 極簡看木色深淺與有無復古細節；coastal / boho 看有無海洋元素或藍白配色；**只有素面藤編、沒有其他線索 → bohemian（信心 ≤ 2）**（C3 試標中三位都這樣標，定成規則可提高一致性，但這是人為約定，請 Skyler 確認）；「黑鐵架 + 木板」→ industrial（信心 ≤ 2）。
    - 新增「掛畫怎麼看風格」一節（看內容、配色、外框），因為 30 格中有 6 格是 wall art，v0 完全沒寫。
13. **抽樣**：每格 30 件（seed 0），30 格都抽滿 → 900 件。全部打亂後編號 item_0001–0900（id 與檔名不透露格子），連續 20 個 id 一批 → 45 批，每批跨格混合。
14. **三位標註者的輸入完全相同**：同一個 system prompt（準則全文 + RUNBOOK 指定的輸出要求句）、同一張 768 px 縮圖（`stage1/img768/`）、同樣的使用者訊息格式（`item_id: <id>` + 圖 + 「依準則標註以上每一件，只輸出 JSON lines。」）。差別只有：Claude 一次 20 張，本地模型一次 1 張；Qwen 另外在 server 端有 max_pixels 409600（會再縮到約 640 px）。
15. **本地模型一次只標 1 張**：和 11-16 的 Style Acc 呼叫一樣單圖最單純，不會錯位；`--limit-mm-per-prompt` 設 2。
16. **Claude 成本檢查點（21:56 UTC）**：前 100 件 $1.006 → 每件 $0.0101 → 900 件推估 **$9.06 ≤ $30，繼續**。比 RUNBOOK 預估的每件 $0.003–0.006 高，原因是 Opus 5.5 預設會思考（每批約 1,800–2,600 thinking tokens，占輸出約一半），而且每批的 20 張圖（約 11–12k tokens）都是新寫入快取。我沒有關掉思考：RUNBOOK 指定的指令沒有這個參數，而且階段 2 要沿用同一個設定。
17. **批量品質小檢查**：前 100 件抽 40 件（seed 固定）用每批 5 張重標，和每批 20 張比：style 90%、category 100%、color 95%、material 97.5%、shape 97.5% 一致。style ≥ 85%，**維持每批 20 張**。4 件 style 不一致都是 mixed/none ↔ 某風格或 other，而且信心都 ≤ 2（屬於 Claude 自己的重測雜訊，不是批量造成的錯位）。重標成本 $0.42（每件 $0.0105，和每批 20 張幾乎一樣，因為 system prompt 有快取）。
18. **碰到用量上限的那次呼叫**（batch 4 第一次，17:1x UTC）記在 claude_calls.jsonl（`limited: true`、$0），沒有寫入任何 failed；重置後重跑。

## 分析與報告
19. **Gemma 的 14 件失敗（用了選項外的詞：ceramic、resin、tropical、pop art、red）照 RUNBOOK 記為失敗，不替它猜對應的選項**。這些商品在 (b)(c) 算成「不一致 / 不合格」（保守）；多數決用另外兩位；κ 與兩兩一致率只用三位都成功的 886 件。
20. **多了一欄 (c2) = (c) 且三位品項都 = 規則品項**。情境二需要風格和品項都對，所以階段 2 的件數推估與格子建議用 (c2)；RUNBOOK 指定的 (c)、(d) 仍照原定義報告。
21. **(d) 同時報兩個分母**：命中總數（RUNBOOK 指定）和「同店同款去重後數量」。後者才是實際能拿來標的商品數，格子建議用後者。95% 區間用 Wilson。
22. **階段 2 的三個方案**：A 每格 13 件合格（12 個合格 + 1 張 query 圖，同格題目共用）、B 每格 26 件（2 題不重複）、C 標完商品池。依據：main table 草稿 4.2（每題 12 個合格）、RUNBOOK（情境一、二各 50 題 → 30 格平均每格約 1.7 題）。每格件數 = 目標 ÷ (c2) 的點估計，上限是該格去重後數量。
23. **格子建議的規則**（`analyze.py`）：去重後數量 × (c2) ≥ 26、其 95% 下界 ≥ 13、且 (c2) ≥ 20% → 保留；(c2) < 20% → 可留但貴；估計 13–26 或下界 < 13 → 勉強；< 13 → 建議拿掉。門檻是我訂的，只是幫 Skyler 排序，不是定論。
24. **人工抽查樣本**：每格 2 件，優先順序 = 三方風格各不相同 → 2 比 1 或有標註失敗 → 一致但有人信心 1 → 一致；同級內用固定 seed 隨機。結果 60 件全是不一致的（40 件三方各不相同）。這批不能用來估整體正確率（報告第 7 節有寫）。
25. **報告由 `make_report.py` 從 JSON 產生**，數字不手打；`verify.py` 檢查重跑一致、表格與 JSON 一致、沒有殘留 server、沒有動到受保護資料夾。
26. **我犯的一個操作錯誤**：等 Claude 批次時，等待迴圈的 `pgrep -f` 比對到自己而不會結束；我用 `pkill -f "until ! pgrep"`（沒有限定範圍）去停，對其他使用者的 16 個程序回報 Operation not permitted（沒有殺掉），自己的兩個等待迴圈被停掉。如果 Skyler 當時有別的 shell 在跑含這段字的迴圈，可能也被停了。標註程序、watch.sh 沒受影響（之後檢查都在 / 已正常結束）。
