# 答案卷 第六輪 — 讓 AI 導演「用得好」的效果層（S-70..S-77；獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-6.md（S-70..S-77）、spec-5.md（P2→P3 路線、S-57 音效、S-62 預覽、S-64 品質閘門）、spec-4.md（導演情境、S-37 分鏡表、S-38 lint）、
wow/fx/process.md（品質閘門、功能旗標）、第五輪 wow/fx/acceptance-5.md（共通規則、SONG64、閃白偵測、RSS、PROBE）、
scripts/fx/core.py（`register(...)` 目前只存 `status/params/doc/source/history`）、
`fx_render.py --list --json --experimental` 目前輸出（出題者 2026-11-05 於 p0-delivery 分支查得）：
`{"effects":{name:{status,params{k:{default,type,doc}},doc,source,history}},"transitions":{…}}`；
stable = 效果 6（flash_white、grade、halation、beat_bounce、zoom_punch、cutout_card）＋轉場 4（crossfade、whip_pan、hex_shutter、flash_cut），共 **10 項**；
其餘（shake、rgb_split、radial_blur、vignette、light_leak…；shape_wipe、push…）為 experimental。

每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條），並附理由。
新 CLI 名以建造者文件為準；本卷用 spec 用語：`--list --json`、`--cards`、`fx_calibrate`、`recipes/`、`fx_lint`、`fx_candidates`（S-75）、`fx_query`。改名須在 references/fx.md 寫明對應。

## 共通規則（第一～五輪全部沿用，另加）
- 第五輪共通規則全部沿用（技能 venv、`VIDEO_GIF_FFMPEG`、「報錯」定義＝非 0／無 traceback／不建 `--out`／牆鐘 < 3 s、不得改 examples/、不得改本答案卷、離線、付費哨兵 = 0、**量測不信任建造者**）。
- **stable 集合**＝驗收當下 `fx_render.py --list --json`（不加 `--experimental`）列出的全部效果＋轉場；以下「每個 stable 項」都對這個集合 100% 檢查，不抽樣。
- **出題者量法 MEAS**（全部以 numpy＋cv2 自寫，不呼叫建造者的量測函式；碼由驗收者撰寫、放 wow/fx/acceptance6_meas.py，建造者不得修改、不得讓產品碼 import 它）：
  - Y ＝ BT.709 luma `0.2126R+0.7152G+0.0722B`，sRGB 0..255；RGBA 先以直通 alpha 合成到文件化背景（未文件化則 #808080）。
  - `dY` ＝ 效果輸出與無效果參考的同格 mean|ΔY|；`area8` ＝ |ΔY| > 8 的像素比例。
  - `ssim_loss` ＝ 1 − SSIM（luma、11×11 高斯 σ=1.5、C1=(0.01·255)²、C2=(0.03·255)²、整張平均）。
  - `disp` ＝ cv2.calcOpticalFlowFarneback(ref, out, None, 0.5, 4, 21, 3, 5, 1.1, 0) 的平均位移量（px，720p）。
  - `flash_area` ＝ WCAG 相對亮度（sRGB 線性化）L，像素「閃轉換」＝ |ΔL| ≥ 0.10 且 min(L) < 0.80 的比例。
  - `red_flash` ＝ 線性化 R/(R+G+B) ≥ 0.8 且 |Δ((R−G−B)·320)|（負值歸 0）> 20 的像素比例（WCAG 2.x 飽和紅定義）。
  - **WCAG 閃爍計數**：逐格 flash_area ≥ **0.111**（1024×768 上 341×256 等效，視為大面積）且方向與上一個大面積轉換相反 → 計一個轉換；一次「閃」＝一對相反轉換；任意 1 s 滑動窗閃數 > 3 → 違反 WCAG 2.3.1（一般閃或紅閃任一）。
  - `center_sharp` ＝ 中央 200×200 區 Laplacian 變異數比（輸出／參考）；`sharp4` ＝ 縮到 1/4 後整張 Laplacian 變異數比（去掉逐像素雜訊的影響）。
- **正式素材**＝本卷「合成素材」表，由測試程式產生，不入庫真實影片。
- **不退步**：第一～五輪舊計畫 `--formats png` frames sha256 逐格相同；`--list --json` 既有鍵（status、params、doc、source、history）保留不改型別（新卡片欄位只能「加」）。

## 合成素材（第一～五輪照用；以下新增）
| 代號 | 內容 | 用途 |
|---|---|---|
| STD-P | 1280×720 不透明「實拍感」標準板（seed 6）：背景對角漸層 Y≈60→190（R×1.05、B×0.9）＋ 32 px 棋盤 ±20 ＋ 高斯雜訊 σ=6；中央半徑 160 圓形主體 (225,190,160)＋圓心上方 80×20 深色條；左下 12 根白色細條（20 px 間距，模擬字／高頻）；右上 200×120 高光塊 (255,240,200) | 校準、可見度、配方 |
| STD-HK | STD-P×0.15＋(215,200,170)：高調（平均 Y≈221） | 可見度在亮畫面 |
| STD-A | 1280×720 RGBA：STD-P 的主體圓＋柔邊 alpha（外圍 alpha=0，透明處 RGB 填亂數垃圾）＋同形狀主體 sidecar | needs=subject／alpha、cutout_card |
| STD-MOV | STD-P 每格水平平移 4 px（反射邊），2 s、30 fps；拍點 120 BPM 首拍 0 ms | 預覽、轉場、配方算繪 |
| SONG64S | 第五輪 SONG64（64 s、120 BPM、4/4、每小節 2000 ms）＋ sections（含 `energy` 0–1）：intro 0–8 s (0.20)、verse 8–16 s (0.40)、build 16–24 s (0.60)、**drop 24–40 s (0.95)**、breathe 40–48 s (0.30)、drop2 48–60 s (0.90)、outro 60–64 s (0.15) | 預算、查詢、關鍵時刻 |
| FL-4 | STD-MOV 上 2 s 內每 250 ms 一次 `flash_white amount=1.0`（1 格；即 4 閃／秒、全畫面） | WCAG 正例 |
| FL-1 | STD-MOV 上 t=1000 ms 一次 `flash_white amount=0.6`（2 格衰減） | 品味閃白，反例 |
| FL-DB | SONG64S 全片只在 downbeat（每 2 s）`flash_white amount=0.5` | 0.5 閃／秒，反例 |

---

### S-70 效果卡 —— 必要（理由：spec 第一性原則；沒有卡，agent 只能背函數名，審查三的問題會重演）
1. **欄位完整**：`fx_render.py --list --json` 每個 stable 項都有卡，至少含 `intent`、`energy`、`needs`、`good_for`、`avoid_for`、`duration_ms`、`pairs_with_sfx`、`conflicts`、`cost_ms_per_frame@720p`（鍵名可文件化改寫）、`gate`、`preview`。覆蓋率 = 有完整卡的 stable 項 ÷ stable 項 = **100%**。**必要**
2. **schema 驗證**：建造者提供 JSON Schema（draft 2020-12，路徑文件化，例 `references/fx-card.schema.json`）；出題者在拋棄式 venv 以 `jsonschema` 驗證 `--list --json` 的每張卡 → 0 錯誤。schema 本身須：`intent` 為 enum（詞彙表在 fx.md）、`energy` number 0..1、`duration_ms` 為 `[min,max]` 且 min < max、`needs` 為 enum 子集（subject／motion／alpha／text）、必填欄 `required`、`additionalProperties` 有明確立場。**必要**
3. **無空話**：所有字串欄位不得為空、不得匹配 `(?i)^(todo|tbd|n/?a|none|-|\.\.\.|xxx|lorem.*|placeholder|待補)$`；`good_for`、`avoid_for` 各 ≥ 1 項；任兩張卡的 `good_for` 不得完全相同；`avoid_for` 與 `good_for` 不得有相同項。**必要**（理由：「欄位是空話」是 spec 列的未抵達樣子）
4. **intent 分布不退化**：以每項的主 intent（陣列則取第一個）計，**任一 intent 佔 stable 項 ≤ 40%**（目前 10 項 → ≤ 4 項），且相異 intent 數 ≥ 4；`energy` 在 stable 項的標準差 ≥ 0.15（不是全部 0.5）。**必要**
5. **energy 與量測一致**：卡上 `energy` 與 S-71 的預設參數 `perceived` 的 Spearman ≥ 0.6（stable 效果；轉場若無 perceived 則免）。**加分**（理由：手填能量對不上量測時，導演會被誤導；但量測本身才是主依據）
6. **成本是實測**：出題者以 STD-P 720p、預熱 3 格後取 20 格中位數重量每個 stable 項單格毫秒，與卡上值相差 ≤ 35% 或 ≤ 3 ms（取寬）；卡附量測機器／日期。**必要**（理由：`--max-cost` 查詢靠它）
7. **gate 對得上紀錄**：`gate` 的分數、日期、紀錄路徑與 S-64 閘門紀錄 100% 一致；分數 ≥ 4（stable 定義）；紀錄 commit 存在於 git。沒有閘門紀錄的項目不得是 stable。**必要**
8. **preview 存在且會動**：每張卡 `preview` 的 2 s 小片（1.9–2.1 s）與縮圖都存在；小片內任兩格最大 dY ≥ 4（靜態類效果須以前後對照／滑動分割等方式讓預覽「動」）；預覽本身過 S-73（不得「看不見」、不得違反 WCAG）。**必要**
9. **conflicts 被用到**：卡上宣告的 `conflicts` 配對，在同一拍出現時 fx_lint 報錯（例 flash_cut＋flash_white 同格）；出題者抽 3 對 → 3/3 報錯。**必要**
10. **plugin 一致**：`--fx-dir` 載入的外掛效果若有卡，同樣出現在 `--list --json`／`--cards`，並受同一 schema 驗證。**必要**
11. `--cards OUT.html`：一頁 HTML 目錄（見文末「看完整成品」）。**加分**（理由：一般人一眼看懂有什麼可用＝驚豔；agent 不靠它）

### S-71 觀感強度校準 —— 必要（理由：同一個 amount 在不同效果看起來差十倍，導演無法下「剛好」的指令）
1. **方法固定**：fx.md 寫明 `perceived` 的公式＝以 MEAS 四類原始量（逐格亮度變化、SSIM 結構差、位移、閃爍面積）組合；建造者可加權、取最大或其他，但須寫明常數、正規化與量測格（暫態效果取峰值格或文件化窗）。校準表入庫（路徑文件化，含每效果 amount 網格、原始量、perceived、素材 id、日期、commit）。**必要**
2. **原始量獨立重算**：出題者以 MEAS 對 STD-P 重算校準表中每列的四個原始量，與表中值相差 ≤ 5%（相對）或 ≤ 0.01／0.2 px（絕對，取寬）；套用文件公式後 perceived 相差 ≤ 0.02。**必要**（理由：量測不信任建造者）
3. **可重現 ±5%**：刪除校準快取後重跑 `fx_calibrate`（兩次，`PYTHONHASHSEED` 0 與 123）→ 每個 perceived 兩次相差 ≤ 5%（相對，或 ≤ 0.01 絕對取寬）。**必要**
4. **單調**：每個 stable 效果主強度鈕（amount 或文件化的主參數）取 11 點等距網格 → perceived 非遞減（容差 0.01）；perceived(鈕=0 或恆等) ≤ 0.02；網格最大值 perceived ≥ 0.10（不是一條平線）。**必要**
5. **與肉眼一致（保留題）**：出題者持有 6 個（效果, 參數）在 STD-P 上的**參考排序**（由出題者以 MEAS 量測＋目視定出，建造者看不到）。系統對這 6 項給出的 perceived 排序與參考排序的 **Kendall τ ≥ 0.6**（15 對中不一致 ≤ 3 對）。若其中某效果被 S-64 刪除，以剩餘 5 項計，τ ≥ 0.6（10 對中不一致 ≤ 2 對）。**必要**（理由：「perceived 與肉眼不符」是 spec 列的未抵達樣子）
6. **跨效果可比**：每個 stable 效果以反查（perceived → 參數）各算 perceived=0.3 與 0.7 的單格；出題者以 MEAS 量：所有 0.7 單格的 MEAS 組合值 > 所有 0.3 單格的比例 ≥ 80%（跨效果配對）；同效果 0.7 > 0.3 為 100%。無法到達 0.7 的效果須在校準表標 `max_perceived` 並由反查報錯，不得默默截斷。**必要**
7. **新效果自動校準**：在 `--fx-dir` 放入一個附卡的新效果（例：整張乘以 (1−0.5·amount) 的 `dim`）→ 依文件指令（或首次 `--list`）自動補進校準表，無需手改；其 perceived 單調且 τ 測試的量法同樣適用。**必要**
8. 校準在第二種素材（STD-HK）也存一份；同效果兩素材的 perceived 差距寫進卡（例 halation 在亮畫面更強）。**加分**（理由：專業使用者會驚豔；一般使用者無感）
9. 轉場也有 perceived（p 掃 0..1 的峰值）。**無感**（理由：轉場強度主要由時長決定，導演不靠它）

### S-72 意圖配方 —— 必要（理由：導演用「意圖」思考；沒有配方就只能逐個效果拼）
1. **數量與命名**：首批 12–16 個（出題者數 `recipes/` 下 stable 配方）；至少含 spec 點名的 7 個（impact、reveal_subject、breathe、build、drop、title_pop、freeze_card）；某元件（例 shake、radial_blur、vignette、text）未過閘門時，配方須以 stable 元件替代並在配方 `notes` 寫明替代，不得引用 experimental。**必要**
2. **JSON schema**：配方 schema 文件化並以 jsonschema 驗證 0 錯誤；欄位至少：`name`、`intent`、`layers[]`（每層 `ref`、`kind`(effect／transition／sfx)、`params`、`offset_ms` 或 `offset_beats`、`duration_ms`、`envelope`／`keyframes`）、`sfx`、`perceived_target`、`gate`。**必要**
3. **只引用 stable**：出題者以腳本掃全部配方的 `ref` → 100% 在 stable 集合；`fx_render --validate` 對每個配方 0 錯誤。**必要**
4. **有時間形狀**：每個配方至少 1 層有 envelope 或 keyframes（不是常數參數）；≥ 50% 配方有 ≥ 2 層且層間起點不同（offset 差 ≥ 1 格）；`build` 配方的強度沿拍遞增（出題者量 4 拍峰值 MEAS 組合值嚴格遞增）；`breathe` 配方 perceived 峰值 ≤ 0.25。**必要**（理由：「配方只是效果清單沒有時間形狀」是 spec 列的未抵達樣子）
5. **音效配對**：每個配方有 `sfx`（或明確 `"sfx": null` 並附理由，至多 3 個配方如此，例 breathe）；算繪 STD-MOV＋音軌後，出題者以 onset 偵測量：sfx 起音與該配方主視覺事件（MEAS 峰值格）差 ≤ 1 格（30 fps，33.3 ms），riser 類以「結束點」對事件。依 S-57 來源優先序（使用者夾 > Kenney > 程序合成），離線無素材時程序合成仍有聲音。**必要**
6. **每個配方都可算繪且可見**：每個 stable 配方套在 STD-MOV（t=1000 ms）算繪 mp4 → 非 0 退出 = 0；S-73 檢查結果無「看不見」、無「刺眼／毀畫面」、WCAG 0 違反。**必要**
7. **配方也過品質閘門**：每個 stable 配方有閘門紀錄（同 process.md：兩位跨廠商評審、取低分 ≥ 4）。**必要**
8. **使用者庫**：使用者目錄（文件化路徑）下的配方 JSON 被載入、同 schema 驗證；與內建同名 → 覆寫警告（同 FX override 機制）。**加分**
9. 配方可在計畫中以 `{"recipe":"impact","at_beat":16,"perceived":0.6}` 一行叫用，`perceived` 縮放各層。**必要**（理由：agent 實際用法）

### S-73 可見度與刺眼度自動檢查 —— 必要（理由：審查三抓到的三個問題都是「沒人量」；WCAG 是安全底線）
以下全部對**算繪後輸出檔**量（建造者檢查器寫 manifest＋qa 報告；出題者另以 MEAS 對同檔重量，判定須一致）。
1. **看不見（正例）**：STD-MOV 上 `light_leak {amount:0.13, seed:3}`（審查三所見 demo2 用法，wow/fx/demo2/plan.json）持續 4 拍 → 該事件標「看不見」警告。出題者實測 STD-P：dY 4.03、area8 0.238、ssim_loss 0.001（參考）。另 `grade {temp:0.05}`（dY 1.8）→「看不見」。**必要**
2. **看得見（反例）**：`light_leak {amount:0.8, seed:3}`（出題者實測 dY 20.7）、`halation` 預設、`zoom_punch` 預設在拍上 → 都**不得**標「看不見」。**必要**（理由：全部判看不見的檢查器等於沒有）
3. **毀畫面（正例）**：`radial_blur {amount:1.0, distance:0.22, samples:12}`（舊預設；出題者實測 STD-P：ssim_loss 0.495、center_sharp 0.018）持續 ≥ 4 格 → 標「毀畫面」錯誤。**必要**
4. **不毀畫面（反例）**：`zoom_punch` 預設（1.07）、`whip_pan` 轉場（本來就糊，屬轉場窗內）→ 不得標「毀畫面」；檢查器須區分「轉場窗內刻意模糊」與「整格破壞」，規則寫進 fx.md。**必要**
5. **WCAG 正例**：FL-4（4 閃／秒全畫面）→「刺眼」錯誤，訊息含「WCAG 2.3.1」、時間窗與閃數；擋交付（qa_media 非 0 或 `--allow-flash` 類旗標才放行，旗標寫明風險）。**必要**
6. **WCAG 反例**：FL-1（單次品味閃白）與 FL-DB（0.5 閃／秒）→ 不標刺眼、不擋交付。**必要**
7. **計畫層預檢**：FL-4 的計畫在算繪前 `fx_lint`／`--validate` 即報 WCAG 錯誤（以拍點時間推算），不必等算繪。**加分**
8. manifest 每個事件有 `visibility: {perceived_measured, status: ok|invisible|harsh|destructive, wcag_flashes_max_per_s}`；qa 報告列出所有非 ok 事件與修法建議（例「amount 提到 ≥ X」）。**必要**
9. 檢查器耗時 ≤ 算繪牆鐘的 25%（STD-MOV 10 s 片）。**無感**（理由：使用者不會察覺，只要不拖慢）

### S-74 效果預算 —— 必要（理由：「每拍都閃」是業餘感第一名；密度上限是懷疑論報告的主要建議）
1. 預算規則文件化：依 sections `energy` 給每段 `perceived` 總量上限（每 4 s 窗）與事件密度上限（每小節）；數值寫在 fx.md 並由 fx_lint 讀同一份設定。**必要**
2. **每拍都閃（正例）**：SONG64S 在 intro（energy 0.20）與 breathe（0.30）每拍 `flash_white amount=0.6` → fx_lint 錯誤，訊息含段落名、拍範圍、規則名（「每拍都閃」）、修法（例「改為只在段落首拍」或「改 downbeat 每 2 小節」）。**必要**
3. **合理密度（反例）**：同段只在段落第一拍閃一次 → 0 錯誤；drop 段前 2 小節每拍閃（共 8 次、2 閃／秒）→ 不得是錯誤（可警告）；整個 drop 16 s 每拍閃 → 至少警告。**必要**
4. **超預算**：breathe 段每拍疊 `zoom_punch`＋`flash_white`＋`beat_bounce` → 「超預算」錯誤，報告「用量 vs 上限」數字；用量＝事件 perceived（S-71 表）之和，出題者重算 ±1e-6。**必要**
5. **預算跟校準聯動**：把某效果校準值人工乘 2（測試用暫存表）→ 同計畫用量隨之改變。**加分**
6. lint 結果寫入導演報告／分鏡表的每鏡備註。**無感**（理由：使用者只看結果）

### S-75 關鍵時刻候選 —— 加分（理由：使用者在 proxy 上挑最有感；但導演無它仍可出片）
1. `fx_candidates SONG64S-plan.json --moment drop`（drop＝24000 ms；另 `--moment hook`＝0 ms）→ 產生 **2–3 個**候選，各有：proxy mp4（短邊 ≤ 540、時間窗文件化，例事件 −2 s..+2 s）、≥ 1 張峰值格縮圖、量測 JSON（perceived 峰值、visibility status、WCAG 閃數、cost）、一頁並排（HTML 或拼圖）。**加分**
2. 候選彼此不同：配方名兩兩相異，且兩兩峰值格 MEAS dY ≥ 4（看得出差別）；全部過 S-73。**加分**
3. 選擇寫回：`--choose 2 --reason "…"`（或文件化方式）→ 分鏡表（spec-4 S-37 `storyboard.json`；未建則計畫 JSON 文件化欄位）該鏡記錄所選配方、候選集 id、理由；再算繪使用所選配方。**加分**
4. 3 個候選總牆鐘 ≤ 60 s（1080×1920 來源、proxy）。**加分**

### S-76 導演查詢介面 —— 必要（理由：agent 用查詢選，而不是背清單；多樣性是 spec 未抵達樣子之一）
基準：`fx_query --intent hit --needs subject --max-cost 30 --section drop --json`（`--needs X`＝素材**可提供**的條件；文件化語意若相反須寫明，測試依文件語意對調）。
1. **決定性**：同參數＋同 history 兩次輸出 bytes 相同，`PYTHONHASHSEED` 0 與 123 也相同；同分以名稱字典序（或文件化規則）決勝。**必要**
2. **遵守條件**：所有結果的 `needs` ⊆ 提供的條件（未給 `--needs subject` 時 cutout_card 與任何需 subject 的配方 0 次出現）；成本（配方＝各層之和）≤ `--max-cost`；`--section drop` 時 `avoid_for` 含 drop 的 0 次出現；`--section breathe` 時結果的 perceived 預設值 ≤ 該段預算上限。出題者對 intent × section × needs 的 5×4×2 = 40 組合全掃 → 違反 0 次。**必要**
3. **理由**：每個結果附 `reason`，含 intent 符合度、閘門分數、成本、多樣性扣分四項中至少三項的**數字**（不是「適合此場景」這種空話）；`score` 依文件公式出題者重算 ±1e-6。**必要**
4. **多樣性**：以 `--history H.json`（或文件化方式）連續 12 次查詢 `--intent hit --section drop`，每次把 top-1 寫回 history → 任意連續 **N=3** 次的 top-1 互異（合格候選 ≥ 3 時）；12 次 top-1 相異數 ≥ min(4, 合格候選數)；top-3 內相異元件 ≥ 2。**必要**
5. 結果同時包含效果與配方（合格時），並標 `kind`。**加分**
6. 查詢 < 300 ms（冷啟動除外的第二次）。**無感**（理由：agent 等得起，使用者看不到）

### S-77 測試 —— 必要
- `python -m unittest discover -s tests`：failure 0；新測試覆蓋：卡片完整性與 schema（每個 stable 項，參數化）、無空話規則、intent 分布、校準可重現 ±5% 與單調、配方只引用 stable／可算繪／有時間形狀、可見度正反例（S-73 第 1–6 條全部）、預算 lint 正反例、查詢決定性／條件／多樣性。需 ffmpeg 者無 ffmpeg 時 skip 並寫理由，其他不得 skip；測試數多於第五輪結束時。
- 共通規則的舊計畫 sha 對照通過；`grep -nE "for (y|x|row|col|px) in range" scripts/fx/` 仍無逐像素迴圈。
- 保留題（出題者另持，建造者看不到）全數通過才算本輪完成；保留題失敗 → 本輪「未達成」，不得以加分項抵。

---

## 看完整成品 —— HTML 效果目錄（`--cards OUT.html`）人工檢查清單
由一位**沒看過本專案**的人（或獨立評審，未讀 spec）在桌機與 390 px 手機寬各開一次，逐項打勾；任一「必要」項不過＝本項不過。
- [ ] **10 秒看懂**（必要）：隨機抽 5 張卡，每張看 10 秒後口述「這是做什麼的、什麼時候用、什麼時候不要用」；5 張中 ≥ 4 張說得對（與卡上 intent／good_for／avoid_for 一致）。
- [ ] **預覽會動**（必要）：每張卡預覽自動播放（靜音、循環）；沒有一張是靜止圖；開頁 3 秒內首屏預覽開始動。
- [ ] **沒有看不見的預覽**（必要）：沒有一張讓觀者問「有加效果嗎？」；靜態類效果有前後對照。
- [ ] **沒有刺眼／俗氣的預覽**（必要）：無 > 3 閃／秒；無整格糊爛；觀者對任何一張說「好俗」→ 記下並對照閘門分數（閘門 ≥ 4 卻被說俗的 > 1 張＝不過）。
- [ ] **可比較強度**（必要）：每張卡有 perceived／energy 的同一把尺（例 0–1 長條），而不是各自的 amount。
- [ ] **依意圖篩選**（加分）：可按 intent／section／needs 篩；篩完數量正確。
- [ ] **可抄用**（加分）：每卡有一行可貼進計畫的 JSON（含建議 perceived），貼進去 `--validate` 0 錯誤。
- [ ] **離線、單檔或單資料夾**（必要）：不載外部網路資源（grep `https?://` 只允許出現在文字連結）；總大小 ≤ 30 MB；file:// 直接開。
- [ ] **配方也有卡**（加分）：12–16 個配方各一張，預覽含音效（點擊後播放）。
- [ ] **手機寬可讀**（加分）：390 px 寬無水平捲動、字不小於 12 px。
- [ ] experimental 項預設不顯示，`--experimental` 時明確標記（必要；理由：避免導演選到未過閘門的效果）。
