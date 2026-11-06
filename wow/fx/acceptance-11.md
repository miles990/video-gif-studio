# 答案卷 第十一輪 — 一句話變完整導演提案（吸收 blank-page）：brief 擴寫、參考取得與授權、brief→分鏡→計畫、brief lint、修改語法、before／after 評估、署名（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-11.md（S-130..S-136）；來源技能本地副本 `C:\Users\User\src\vgs-fx-private\third_party\blank-page\`（README.md、LICENSE、skills/blank-page/SKILL.md、references/finding-references.md、vocabulary.md、examples.md、patterns.md、scripts/find_refs.py）；
wow/fx/spec-7.md（S-90..S-94 分鏡）、spec-9.md（`vgs` 統一 CLI、S-113 版本、S-116 評測基準）、process.md（兩軸閘門）；沿用 acceptance-7.md、acceptance-9.md 的共通規則與 acceptance-amendments.md 的 P-WIN／P-USER 模板。出題者 2026-11-05 寫定。

出題者查得現況（HEAD b1cbca2）：已有 `scripts/storyboard.py`、`storyboard_lint.py`、`animatic.py`、`taste_report.py`、`taste_target.py`、`taste_pick.py`、`beat_layers.py`（`downbeats_ms`、段落）、`fx_render.py`、`fx_recipes.py`；
`references/storyboard.schema.json`（每鏡 `size`、`motion` 列舉＝S-60 具名運鏡 ∪ static/handheld、`intent`、`recipe`、`perceived`、`why`、`serves_core`、`rule_break`）；`recipes/` 14 個 stable 配方；
`THIRD_PARTY.md` 已存在（Penner 等）。**尚不存在**：任何 `vgs` 入口（spec-9 未建）、brief 相關程式、blank-page 署名段落。
→ 若 spec-9 的 `vgs` 尚未建好，S-130 可先以 `scripts/brief.py`（或建造者命名）提供，**但必須**在 references/ 寫明 `vgs brief` 的對應，且一旦 `vgs` 存在就必須走 `vgs brief`（JSON 進出、ERR 信封照 acceptance-9）。

每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條），附理由。
CLI／欄位名以建造者文件為準；本卷用 spec 用語（`vgs brief`、`brief.json`、`aesthetic`、`beats[]`、`is_turn`、`refs[]`、`handle`、`role`、`use`、`cited_by`、`source`、`forks[]`、`mode`、`brief_lint`、`delta`），改名須在 references/ 寫明對應。

## 共通規則（第一～十輪全部沿用，另加）
- 技能 venv、ffmpeg 經 `VIDEO_GIF_FFMPEG`、不得改 examples/、不得改本答案卷、付費哨兵計數 = 0（`vgs brief` 本身不得呼叫付費模型；擴寫的「文字」由呼叫它的 agent 寫，程式負責骨架、取材、對拍、lint、轉換）。
- **兩層驗收**：
  - **骨架層（程式、決定性）**：模式分類、取材順序、節拍時間格與拍點對齊、refs 紀錄、lint、delta 解析、brief→分鏡→計畫轉換。同輸入跑兩次 JSON（除 `meta`）逐位元相同。
  - **文字層（agent 寫）**：美學命名、節拍敘述、轉折點子、分岔。以 lint（每份都必須過或附豁免）＋「看完整成品」＋S-135 評估驗收。測試以**錄好的文字夾具**跑骨架層；live 跑只在「看完整成品」與 S-135。
- **brief.json 為準、prompt 文字由它生成**：人看的 brief（fenced 文字，blank-page 形狀）與 `brief.json` 必須一致：出題者腳本比對節拍數、每拍引用的 handle、refs 數與用途、分岔數；不一致＝S-130 不過。
- **NETGUARD**：照 acceptance-9（`sitecustomize.py` 記錄 socket／getaddrinfo；psutil 監看子孫行程）。本卷另加 **NET-BLOCK** 模式：同一守衛改為「記錄後拋 `OSError`」，模擬完全離線。
- **網路提供者可替換**：are.na／Pinterest／Sketchfab 取材必須經一個可替換的提供者介面；測試用**錄製匣（cassette）**回放，不連網。live 網路只在建造者選擇時、且記錄每次請求。
- **字數計法（C 類，可校準）**：英文以空白分詞；CJK 每個漢字／假名算 1 字，夾在其中的拉丁詞算 1 字。上限：新 brief 英文 ~150 詞／中文 ~300 字（以 `refs:` 以上計）；修改（delta／看圖回饋）英文 ~50 詞／中文 ~100 字。**硬失敗** = 超過上限 20%；介於上限與 +20% 之間報 warning。建造者可改值，但須寫在 thresholds（C 類）並附校準紀錄，不得只為讓夾具過而改。
- **±1 格** = 輸出 fps 一格（30 fps → 33.33 ms）。拍點時間由出題者以合成音樂的已知答案判定，不信任建造者的拍點值。
- **報錯**：照 acceptance-9（非 0 結束碼、無 Traceback、`--json` 時 stdout 為單一 JSON、ERR 信封含 `code`／`location`／`suggestion`）。

## 合成素材與夾具（全由測試程式以 numpy／PIL／ffmpeg lavfi 產生；不入庫真實影片、不入庫任何網路參考圖）
| 代號 | 內容 | 已知答案／用途 |
|---|---|---|
| **BL-1..BL-5** | blank-page README 的 5 句原文（payments api／10,000 users／pricing glass／notes search／calendar settings；逐字，引號內） | 模式＝brief；BL-3 為 loop 背景（「subtle」「behind the plan cards」）；BL-5 已含轉化動詞 `snaps into`；BL-1 已含 `comes back as` |
| BL-6 | 「我咖啡店新菜單 10 秒直式，溫暖」 | 模式＝brief；duration 10 s、9:16；「溫暖」是 fence（不是美學名）→ 美學行須為它的**子項**且具名 |
| BL-7 | README 的 `a 5 second launch video for my app` | 無 fence；缺真實 app → brief 上方一行說明缺什麼、用什麼替身 |
| BL-8 | README 的 `5 second clip for my coffee shop's new menu, warm and cozy` | 與 BL-6 同題英文版；兩者美學可不同但都必須單一且具名 |
| **PROJ-CAFE** | 5 段合成素材（各 4 s、1080×1920、30 fps）：C1 棕色圓盤（杯）＋上升雜訊（蒸氣）；C2 米色矩形＋黑色條紋（菜單板）；C3 膚色移動塊（手）；C4 暖橘漸層（窗光）；C5 深綠矩形＋白字「OPEN」（店面）。附鏡頭卡（spec-4 S-36 格式；若未建則以建造者等價 JSON） | 取材時 u 類 handle 應優先填：整體（C4 或 C1）、色盤（C4）、材質（C2）、構圖（C1）、細節（C5 字） |
| TASTE-W | `taste-user.json` 夾具：偏好 暖色、低事件密度、`soft_hit` 族、字幕含蓄 | 美學與配方選擇須反映（見 S-130.6） |
| REFSTAT | S-86 `taste_target` 夾具：ASL 1.25 s、CV 0.35 | 分鏡鏡長須貼近（S-132.5） |
| **M-DROP** | 10.000 s、120 BPM、4/4；kick 每拍、downbeat 每 2.000 s；0–6 s 粉紅噪 −28 LUFS＋kick −24；**drop 於 6.000 s**（全頻段能量 +12 dB、低頻占比 ×3）；6–10 s 維持 | downbeats = 0, 2, 4, 6, 8 s；drop = 6.000 s |
| M-DROP-5 | 同 M-DROP 但 5.000 s、drop 於 2.000 s | 5 s 片用 |
| **LIB-LOCAL** | 本機參考庫：12 張靜態（各附 sidecar：`source_url`、`licence`、`author`、`aesthetic_tag`）、6 段 gif/mp4（`motion_tag`：peel、morph、zoom_out、push、stagger、wipe） | 離線退路用（S-131.6） |
| **CAS-ARENA** | are.na 錄製匣：`channels "warm film"` 等 6 個查詢的回應＋縮圖 | S-131 回放 |
| CAS-SKF | Sketchfab 錄製匣：`coffee cup` 9 筆，含 CC0×2、CC-BY-4.0×3、CC-BY-SA×1、CC-BY-NC×2、CC-BY-ND×1 | S-131.4 授權判定 |
| **D-1..D-6** | 修改句（見 S-134 表） | delta 解析 |
| IF-1 | 3×3 聯絡單（由 PROJ-CAFE 第一版算繪產生，每格印時間戳）＋文字「第 5 格太暗、第 8 格字太小」 | 看圖回饋 |
| B-1 | 「同一個菜單，做 3 個不同的版本，轉折都不一樣」 | batch |
| SQ-1 | 「在 3 秒的地方，菜單翻頁之後跳出價格標，6 秒前結束」 | sequence |
| HK-1／HK-2 | 「把 v3 匯出成 mp4 給 IG，檔名 cafe_menu_final」／"check the render" | housekeeping |

---

## S-130 brief_expand（`vgs brief`）—— 必要（理由：spec 的驚豔時刻「只打一句就回一份專業提案」直接就是它；其他 S 都吃它的輸出）

**命令形狀**（名稱以建造者文件為準）：
```
vgs brief --draft "<一句話>" [--project <dir>] [--music <wav>] [--platform ig_reels] [--ref <參考片>] [--taste <taste-user.json>] [--offline] --json
vgs brief --draft "<修改句>" --project <dir> --previous v3 --json          # delta／看圖回饋
vgs brief --draft "<修改句>" --image <contact.png> --project <dir> --json   # 看圖回饋
vgs brief lint <brief.json|brief.md> --json
vgs schema brief
```

### 模式分類
1. 下表每列分類正確（**20/20**，不容錯；理由：分錯模式＝整個輸出形狀錯，正是 patterns.md 的 17%「糾正誤讀」）。輸出 `mode` ∈ {brief, batch, delta, image_feedback, sequence, housekeeping}，並附 `mode_reason`（觸發的訊號字）。**必要**

| 輸入 | 期望 mode |
|---|---|
| BL-1..BL-8（8 句） | brief |
| B-1；"create 4 variations of the menu reveal" | batch |
| D-1..D-6（見 S-134）；「拿掉最後的字卡」 | delta |
| IF-1（`--image` 聯絡單＋文字） | image_feedback |
| SQ-1；"at 7s, after the cup exits, add a steam wipe" | sequence |
| HK-1；HK-2 | housekeeping |

2. **housekeeping 不擴寫**：HK-1 原樣保留意圖，只補精確格式／目標（例：`export v3 → cafe_menu_final.mp4, 1080×1920, H.264, IG Reels 規格`）；**不產生**美學、節拍、refs；NETGUARD 0 外連；不呼叫取材。HK-2 對應到 `vgs qa`（或等價）而不是 brief。**必要**
3. **delta／看圖回饋跳過取材**：除非修改句帶入新的外觀或動作（例「改成 riso 風」），NETGUARD 0 外連、不改 refs。**必要**

### brief 形狀（以 BL-1..BL-8 與 PROJ-CAFE＋M-DROP 跑；文字層用錄好夾具＋live 各一次）
4. **一個美學、命名**：`aesthetic` 恰 1 個非空字串，出現在 prompt 第一行；有 fence（BL-1 `stripe’s style`、BL-3 `apple’s website`、BL-5 `clean and minimal`、BL-6「溫暖」、BL-8 `warm and cozy`）時，美學是該詞的**子項**（例 `in stripe-gradient dark`、「晨光底片暖調」），不得換成別的美學、不得是品牌截圖；無 fence（BL-2、BL-4、BL-7）時須具名（不得是「現代」「簡約」「溫暖」這類單一形容詞）。出題者以清單檢查：美學字串不得只由下列泛詞組成：modern, clean, minimal, simple, warm, cozy, cool, sleek, professional, 現代, 簡約, 溫暖, 質感, 高級, 專業。**必要**
5. **5＋3 參考、各有用途、各被引用**：`refs` 含 a1–a5（role 依序 look／palette／material／composition／detail）與 m1–m3（main mechanic／turn／exit 或 camera；無合格 exit 時 m3 可改餵另一拍並在 camera 行用文字寫運鏡）；每個 ref 有非空 `use`（寫明「哪一拍、取什麼」，≥ 6 字／4 詞，不得是 "reference"、"inspiration"、「參考」）；每個 handle 至少被一拍的文字**行內引用**（出題者以正則掃節拍文字比對 `cited_by`）；被 `(the turn)` 標的 motion handle 恰 1 個，且就是 `is_turn` 那一拍引用的。缺 ref 時以 `[? visual ref]`／`[? motion ref]` 佔位並附已試的查詢，**不得**捏造 URL。**必要**
6. **用使用者的東西做錨（取材順序）**：有 `--project`、`--taste`、`--ref` 時，每個 ref 帶 `source` ∈ {user, taste, refstat, local_lib, web}。PROJ-CAFE＋TASTE-W：
   - 能由使用者素材填的槽（look／palette／material／composition／detail 中至少 4 個，見夾具已知答案）必須用 `source: user`（u 類 handle 指到鏡頭與時間）；
   - web 請求數（錄製匣命中計數）**= 空槽數**，不得為已填槽再搜；
   - TASTE-W 的偏好反映在輸出：至少 2 項可驗（例：選用配方屬 `soft_hit`／`breathe`／`warm_memory` 族而非 `impact`；分鏡事件密度 ≤ 品味檔上限；美學行為暖色系子項）。
   - 只有 BL-6（無 project、無 taste）時才可全部來自 web／local_lib。**必要**
7. **編號節拍＋轉折**：`beats[]` 依序編號、每拍＝主體＋動作＋它揭露／變成什麼；恰有 ≥ 1 拍 `is_turn: true`，其文字含揭露／換媒材／拉遠／變成類動作（不是「進場、動、停住」）。BL-1（`comes back as`）、BL-5（`snaps into`）：草稿裡的轉化動詞**就是**轉折，該拍是最大拍（時長最長或 `perceived` 最高），且全文沒有第二個轉化隱喻（`is_turn` 恰 1 拍；其他拍不得含 reveal／morph／turns into／becomes／變成／化為 等轉化詞）。**必要**
8. **轉折時間與結尾停留**（每拍有 `t_start`、`t_end` 秒）：令 D＝片長。轉折拍 `t_end > 0.32·D`（5 s → > 1.6 s，blank-page 原規則等比放大）；結尾停留（最後一個有動作的拍結束到片尾）< 1.0 s；≤ 5 s 的片只有一個主想法（`is_turn` 恰 1）；D > 5 s 時轉折數 ≤ ⌈D/5⌉。**必要**
9. **對齊音樂**：給 `--music M-DROP` 時，轉折拍 `t_start` = drop 6.000 s（±1 格）；其餘拍的邊界落在 downbeat（±1 格）或在 `beats[].anchor` 寫明它對的是哪個拍／段落；BL-6＋M-DROP 的 10 s 片轉折不得落在 0–3.2 s。M-DROP-5 的 5 s 片轉折於 2.000 s（±1 格）且 `t_end > 1.6 s`。出題者用合成音樂的已知答案判定。**必要**
10. **分岔 ≤ 3、只問真正的選擇**：`forks[]` ≤ 3，每項有 `choice_made` 與 `alternative`；**不得**問 duration、loop、aspect、檔名、fps、解析度（例行項目直接給預設）。出題者掃分岔文字：含上述任一詞（或「秒」「直式／橫式」「幾秒」）＝不過。prompt 內 `[? ...]` 數 ≤ 3（ref 佔位 `[? visual ref]`／`[? motion ref]`／`[? download]` 另計，不佔創意分岔額度，但須在 fill-ins 列出已試查詢）。**必要**
11. **字數**：BL-1..BL-8 的 prompt（`refs:` 以上）在上限內（見共通規則）；超過時先刪可選行（realism、params、重述預設的 frame 行），**不得**刪節拍或轉折（夾具 L-LONG 驗證，見 S-133）。**必要**
12. **輸出只有三樣**：fenced prompt、fill-ins（≤ 3 分岔）、一行參考聯絡單位置；缺真實物件時（BL-7 沒有 app、BL-6 沒有菜單照片／logo）在 prompt 上方**一行**說明缺什麼與替身。不得有技巧教學、建議段落、問候。出題者計：fence 外文字 ≤ 8 行（含 fill-ins）。**必要**
13. **畫面是電影格**：brief 或其分鏡宣告主角在轉折拍的畫面高佔比 ≥ 40%、最小字級 ≥ 24 px @ 短邊 1080；BL-3（背景、要含蓄）主角規則以「無主角／背景」標記豁免（見 S-133 豁免）。**必要**
14. 美學行沿用使用者原字（「溫暖」「warm and cozy」出現在美學的父詞或 fence 欄）；中文草稿輸出中文 prompt（refs 欄位可英文）。**加分**（理由：作者的聲音被保留，使用者會覺得「這是我的想法變好」而不是被換掉）
15. 小寫、祈使句、無贅詞的 blank-page 語氣逐字模仿。**無感**（理由：使用者看不出語氣規範；中文 prompt 本來就沒有大小寫）
16. 骨架層（不含網路）在開發機 ≤ 3 s。**加分**

---

## S-131 參考取得（選用、有授權紀錄）—— 必要（授權與「不入成品」部分）／加分（are.na 取材品質部分）
（理由：參考取得本身 spec 標選用；但一旦下載任何東西，授權紀錄與不入成品是法律風險，必須做到）
1. **每個下載的參考有紀錄**：sidecar 或 `refs[]` 欄位含 `source_url`（實際檔案 URL）、`page_url`、`channel`（are.na 時）、`author`（可得時）、`licence`（字串；不知道寫 `"unknown"`，**不得留空或猜**）、`retrieved_at`、`sha256`、`role`、`use`。以 CAS-ARENA 回放，出題者逐筆比對錄製匣內容。**必要**
2. **存放位置不入庫**：參考檔放在專案資料夾的 refs 子目錄（或 `.context/refs/<topic>/`），`git ls-files` 不得出現任何參考檔或 sidecar；若預設位置在 repo 內，`.gitignore` 必須涵蓋。**必要**
3. **參考只讀、不入成品（指紋檢查）**：由 S-132 算繪 PROJ-CAFE＋BL-6 的成片，出題者對每格（30 fps 全格）與每個參考（靜態圖、motion ref 每 0.25 s 一格）做：
   - 全畫面 pHash（64-bit）漢明距離 ≥ 12；
   - ORB 特徵＋RANSAC 單應：內點數 < 25（偵測縮放嵌入、裁切、調色版）；
   - **正對照**（建造者測試須含，出題者也跑）：(a) 把 a1 直接當一鏡 1 s 插入、(b) 把 a3 縮 40% 疊在角落、(c) a2 調色 +20% 飽和後全畫面 → 三者都必須被抓；**負對照**：未出現的 LIB-LOCAL 圖不得誤報。
   - 另：`plan.json`／render 輸入清單中不得出現任何 `role` 為參考（非 asset）的檔案路徑或 sha256。**必要**
4. **可用資產與授權**（CAS-SKF）：資產（`assets:`）只可用 CC0、CC-BY（含版本）、以及使用者明示擁有的檔案；CC-BY 自動寫入成片的署名清單（credits.json 或 delivery 文件：作者、標題、授權、URL）。CC-BY-SA 標 warning 並在 fill-ins 說明分享要求；**NC、ND、Sketchfab Standard／Editorial、unknown** 一律**不得入成品**：brief 可在 fill-ins 列為「授權不符、未使用」，計畫轉換（S-132）與 `fx_render --validate` 遇到必須以 ERR（例 `E_LICENCE`）拒絕，`location` 指到該資產。出題者以 CAS-SKF 的 9 筆逐一判定。**必要**
5. **取材順序與 fence**：照 blank-page「are.na 頻道 → Pinterest → 原站」；有 fence 時查詢詞＝fence 詞（或其解碼字），5 張靜態來自同一美學（`aesthetic_tag`／channel 相同或為同一 umbrella 子頻道）；**motion 不受 fence 限制**。出題者以 CAS-ARENA 回放檢查查詢序列。**加分**（理由：取材品質直接影響第一版好不好看，但要看 S-135 才知道值不值）
6. **離線退路**：NET-BLOCK 下以 BL-6＋PROJ-CAFE＋TASTE-W 跑：成功輸出合法 brief（lint 通過），refs 只來自 user／taste／refstat／local_lib；空槽以 `[? visual ref]` 佔位；`meta` 寫 `offline: true`、已嘗試的提供者與失敗原因；牆鐘 ≤ 10 s（不得卡在 DNS 逾時）；brief 中沒有任何 URL 不是來自使用者或 LIB-LOCAL sidecar。`--offline` 旗標與 NET-BLOCK 結果相同（除 `meta`）。**必要**
7. 影片參考有聯絡單（3×3、印時間與片長；長片 16／25 格），m 類 `use` 的時間範圍（例 `0.0–1.6 s`）可在聯絡單上對到。**加分**
8. Pinterest 只靠 agent 網頁搜尋、不爬取；遵守網站條款（不繞登入、不大量下載：每 brief 下載 ≤ 30 檔）。**必要**（理由：條款風險）

---

## S-132 brief → 分鏡 → 計畫 —— 必要（理由：spec「比 blank-page 更好」的核心：節拍可算繪、可量測，不只是文字 prompt）
**命令形狀**：`vgs brief to-storyboard brief.json --out storyboard.json`、`vgs plan storyboard.json --out plan.json`（或 `storyboard.py`／`fx_render.py` 等價）。
1. **round trip 合法**：BL-1..BL-8（各配 PROJ-CAFE 或剪影卡）與 B-1、SQ-1 的 brief.json → storyboard.json 通過 `references/storyboard.schema.json`（`jsonschema` 驗證）→ `storyboard_lint` 0 個未豁免錯誤 → plan 通過 `fx_render --validate`（或 `vgs plan --validate`）→ animatic 可產出。10/10 成功。**必要**
2. **只用 stable**：storyboard 每鏡 `recipe` ∈ `recipes/*.json` 中 `status: stable` 者（目前 14 個）；`motion` ∈ schema 列舉（S-60 具名運鏡 ∪ static／handheld）；轉場只用 stable 轉場。出現 experimental 必須 brief 明示 `experimental: true` 且計畫帶旗標，否則轉換以 ERR 拒絕。**必要**
3. **節拍→鏡頭映射可追**：每拍對到 ≥ 1 鏡（storyboard 鏡有 `beat` 或 `beats` 欄指回）；轉折拍對應的鏡 `intent` 為 reveal／drop／hit 類（`reveal_subject`、`hero_glow`、`drop`、`impact`… 由建造者表列）且其 `perceived` 為全片最高（或並列最高）；鏡頭時間 = 節拍時間（±1 格）。**必要**
4. **ref 用途落到分鏡欄位**：a2（palette）→ `color_script`；a4（composition）→ 對應鏡 `composition`；a3（material）→ 對應鏡 `lighting` 或質感配方參數；a5（detail）→ 對應鏡 `why` 或元素欄；m1／m2／m3 → 對應鏡 `motion` 或 `transition`。出題者對 BL-6 檢查 8 個 handle 全部可在 storyboard 找到引用（handle 字串或 `ref` 欄）。**必要**
5. **品味目標**：有 REFSTAT 時，storyboard 鏡長 ASL 在目標 ±20%、CV 在 ±0.15；無則依 TASTE-W 密度。**必要**
6. **對拍保持**：M-DROP 下轉換後的 plan 正式算繪（proxy 即可），出題者從輸出檔量轉折鏡頭的首個顯著變化格（亮度／運動躍升）落在 6.000 s ±1 格。**必要**
7. **一鏡一運動**：轉換不得把 m 類 ref 拆成同鏡兩運動；若某拍需要兩個運動，必須拆成兩鏡並在 `why` 寫明。**必要**
8. 轉折拍若引用的 m2 機制沒有對應 stable 配方／運鏡，轉換以 warning 報「機制無對應，改用 <最接近的 stable>」並記在 storyboard `why`，不得默默換掉。**必要**（理由：spec「擷取機制不是形容詞」——機制被靜悄悄換成別的就是 patterns.md 的「editorial page-drag 被做成 slide-in」）
9. animatic（S-92）直接由 brief 產生一支剪影卡預覽，印節拍號與 ref handle。**加分**（理由：使用者 say yes 之前就看得到節奏）

---

## S-133 brief lint —— 必要（理由：spec 把 blank-page 的經驗規則變成可量測的 lint；沒有 lint，形狀規則只是口號）
**命令**：`vgs brief lint <brief> --json`；每條違規輸出 `{rule, severity, location, message, fix}`：`location` 指到第幾拍／哪個 handle／哪一行，`fix` 是具體動作（例「a4 未被任何拍引用：刪除，或在第 2 拍寫 `on a4's centered frame`」），不是「請注意」。
1. 正反例夾具（出題者給規格，建造者實作於 tests）——**每列正例必報、反例 0 誤報**：**必要**

| 夾具 | 內容 | 期望 |
|---|---|---|
| L-2AES | 第一行 `in vaporwave and swiss style` | 報 one_aesthetic；L-1AES（只有 vaporwave）不報 |
| L-REFUNUSED | a4 無任何拍引用 | 報 ref_unused 於 a4 |
| L-NOUSE | m2 `use` 為空或「參考」 | 報 ref_no_use 於 m2 |
| L-TWOROLE | 同一檔案同時當 look 與 motion 且只列一次 | 報 one_ref_one_job（同檔兩角色須列兩次各自限定） |
| L-NOTURN | 節拍只有進場、動、停住 | 報 no_turn |
| L-EARLYTURN | 5 s 片轉折結束於 1.2 s | 報 turn_too_early；1.8 s 不報 |
| L-HOLD | 結尾停留 1.4 s | 報 end_hold；0.8 s 不報 |
| L-2IDEA | 5 s 片兩個 `is_turn` | 報 one_idea |
| L-HERO | 轉折拍主角高佔比 30% | 報 hero_size；45% 不報 |
| L-TEXT | 最小字 18 px @1080 | 報 min_text；24 px 不報；1080×1920 與 1920×1080 皆以短邊 1080 換算 |
| L-FORK4 | 4 個 `[? ]` 創意分岔 | 報 forks_max |
| L-ROUTINE | 分岔問「要 5 秒還是 10 秒」 | 報 routine_fork |
| L-LONG | 中文 brief 400 字 | 報 word_cap（error）；330 字報 warning；290 字不報 |
| L-DLONG | delta 80 詞 | 報 word_cap_edit |
| L-ADJ | 節拍「編輯感換頁」無機制描述（無 from／reveal／底下 等機制詞） | 報 mechanism_not_adjective（warning） |
| L-NOURL | web 來源的 ref 缺 `source_url` 或 `licence` | 報 ref_provenance |
| L-NC | assets 含 CC-BY-NC | 報 licence（error） |

2. **豁免**：沿用 storyboard 的 `rule_break` 形狀（`{rule, why}`）。L-HOLD＋`rule_break: {rule: "end_hold", why: "客戶要求 logo 停 1.5 s 供辨識"}` → 報為 `exempted`（不是 error），輸出保留理由；`why` 空字串或 < 6 字 → 仍是 error。**不可豁免**：licence、ref_provenance、refs 入成品、schema 錯誤（豁免這些 → lint 回 error `exemption_not_allowed`）。**必要**
3. lint 對同一 brief 的 md 與 json 兩種輸入結果相同。**必要**
4. 數值（40%、24 px、1 s、1.6 s／0.32·D、150／50、≤3、5＋3）寫在 thresholds registry，類別 **C**（來源：blank-page 作者的經驗規則，MIT 原文），註明「不是外部標準」。**必要**
5. lint 對 BL-1..BL-8 的 live 產出全部 0 個未豁免 error。**必要**
6. 單份 brief lint ≤ 200 ms。**加分**

---

## S-134 修改語法（delta／看圖回饋）—— 必要（理由：spec 驚豔時刻「說第二拍慢一點、保留顏色，就只改那一拍」）
1. **delta 解析成結構**：每行一筆 `{target:{shot|beat|element}, change, magnitude, direction:{axis, sense}, phase, keep[]}`。以 PROJ-CAFE 第一版（v1，含 storyboard 與 plan）為前文：**必要**

| 代號 | 輸入 | 期望解析（核心欄） |
|---|---|---|
| D-1 | 「第二拍慢一點、保留顏色」 | target＝beat 2（及其鏡 id）；change＝speed；direction＝slower；magnitude 缺 → 填預設（例 0.8×）並在輸出標 `[? 0.8x]`；keep ⊇ {color／color_script／LUT} |
| D-2 | "make the final pan 3x faster at top speed" | target＝最後一個 `motion: pan` 的鏡；magnitude＝3×；phase＝top speed（峰速，不是平均）；keep 預設「其餘不變」 |
| D-3 | 「把轉折提前到 drop，其他不動」 | target＝`is_turn` 拍；change＝time；對齊 drop（有音樂時解析成具體秒數）；keep＝all others |
| D-4 | 「拿掉最後的字卡」 | change＝remove；target＝最後一個 title／card 元素 |
| D-5 | 「第三鏡往右推 30 度」 | target＝shot 3；change＝rotation 或 pan；magnitude＝30°；direction＝{axis: yaw, sense: 畫面右}（不得只存「右」） |
| D-6 | "make it faster" | 若 v1 有多個速度量（剪輯節奏、運鏡速度）→ 輸出 1 個 `[? ]` 問哪個量，不得猜；並給預設倍率 |

2. **只重做受影響鏡頭**：D-1 套用後產生 v2（S-113 版本）：只有 beat 2 的鏡（＋相鄰轉場）重算；出題者比對 v1／v2 其他鏡頭的 frames sha256 逐格相同（`--formats png`）；`vgs diff v1 v2` 只列這些鏡；render 紀錄顯示其他鏡用快取。**必要**
3. **keep 真的保留**：D-1 後 beat 2 的鏡頭顏色與 v1 平均 ΔE2000 ≤ 1.0（出題者以輸出檔每 0.25 s 取格量）；時長變長（慢一點）且後續拍若需順延則重新對拍、仍落 downbeat ±1 格，或保持總長並在輸出說明取捨。**必要**
4. **方向必須有軸與正負**：解析後的 `direction` 不得出現 "other way"／「另一邊」「反過來」等相對詞；必須依 v1 的現況換成絕對方向（例 v1 `direction: left-to-right` → `right-to-left`）並寫明。**必要**
5. **看圖回饋**（IF-1）：每行一筆 `{frame|time, observation, quantified}`；「第 5 格」由聯絡單 metadata 對到時間（±1 格），量化觀察由出題者驗證（例「t=4.40 s：平均 Y 41，目標 ≥ 80」與出題者從 v1 量得的值差 ≤ 5%）；「第 8 格字太小」對到該時間的字幕事件與目前字級（px @1080）。只修這兩個時間點所屬的鏡。**必要**
6. 修改輸出（prompt 版）在 ~50 詞／~100 字內，修改多筆時編號、每行點名目標；`unrelated:` 標不同 comp／專案。**必要**
7. 修改回覆時列出「我理解為：…」一行，讓使用者 1 秒確認。**加分**（理由：17% 糾正誤讀主要在修改階段發生）

---

## S-135 before／after 評估 —— 必要（理由：spec 未抵達第 6 條「擴寫後的片子在盲比中沒有比直接做好」；作者只展示精選對比，我們要登記判準後量）
1. **預先登記**：題目檔（6–10 句一句話）在**跑任何一次之前** commit（檔案 sha 與 commit 時間早於第一筆結果）。題目須包含 BL-1..BL-5、BL-6，及至少 2 句建造者沒看過的（由出題者另提供，不在本卷）。**必要**
2. **兩臂公平**：同一 agent、同一模型與 effort、同素材、同音樂、同平台；A＝`vgs brief` 擴寫後做；B＝原句直接做。兩臂都走同一條算繪管線；兩臂都可用 stable 效果；評審看不到臂別（檔名隨機、位置隨機）。**必要**
3. **技術軸（決定能不能宣稱「更好」中的「無退步」）**：P-STABLE 的瑕疵題（接縫、拉絲、單格閃、黑格、時間連續、字被裁、安全區）兩臂各自通過自動檢查；A 不得在瑕疵題上顯著輸 B（反向 P-WIN 不得成立）。**必要**
4. **好看軸**：P-WIN（A＝擴寫版，B＝直接做）由評審團給**參考排序**；**決定是否宣稱「擴寫更好」的是使用者抽查**：P-USER 形式，≥ 8 對**會動的短片**（GIF／MP4，原速；不得只給靜態聯絡單），含 1 組隱藏正對照（A 對 A 的刻意破壞版）與 1 組隱藏負對照（A 對 A 換 seed），問題固定「哪一支你會直接用？」。報告使用者偏好率與 Wilson 95% 區間、評審與使用者一致率。**必要**
5. **誠實結論**：結果入導演評測基準（spec-9 S-116，若尚未建則入 `wow/fx/` 的 bench 紀錄 JSON，欄位與 S-116 相容）；若擴寫版沒有顯著較好，必須照實寫「未證明更好」，不得重抽同一版本、不得事後換題。**必要**
6. 每題附 A／B 並排 GIF 與兩份 brief（A 的擴寫 brief、B 的原句），讓使用者看得到差在哪。**加分**
7. 依結果標記哪類題目擴寫最有用（有 fence／無 fence／有轉化動詞／背景類）。**加分**

---

## S-136 署名與授權 —— 必要（理由：MIT 唯一的義務就是保留版權與許可聲明；做錯是法律問題，不是品味問題）
1. **THIRD_PARTY.md** 新增 blank-page 段：來源 URL（github.com/StewdioAI/blank-page）、取得日期與 commit（或本地副本日期）、作者署名（Blake Shao／Stewdio，依 README）、**LICENSE 的版權行逐字照抄**——出題者注意：本地副本 LICENSE 寫的是 `Copyright (c) 2026 Cekura, Inc.`，與 spec 的「© Blake Shao／Stewdio」不同；THIRD_PARTY **必須**照 LICENSE 原文寫版權人，作者另列；並附 MIT 許可全文。**必要**
2. **吸收段落標出處**：references/ 中吸收自 blank-page 的每一段（brief 形狀、模式表、槽位表、規則、取材流程、修改語法、語料數字 38 session／587 prompt／17%）段首或段標題標「改寫自 blank-page <檔名> §<段>（MIT）」；出題者以 SKILL.md 各段標題對照，吸收段 100% 有標。語料數字必須寫明是**作者的**語料，不是我們的量測。**必要**
3. **不複製 media 與行銷內容**：repo（`git ls-files`）中沒有任何檔案與 blank-page `media/` 11 個 gif 的 sha256 相同、也沒有相同檔名；README 的行銷句（「Midjourney」比喻、Stewdio plugin 推廣、install 段）不得出現在 repo。BL-1..BL-5 原句可作為測試題目引用（MIT 允許），但須在題目檔標出處。**必要**
4. 若 vendoring `find_refs.py`（原樣或改寫），檔頭保留來源與 MIT 聲明，並註明改了什麼；若是重寫，在 THIRD_PARTY 寫「思路來自 find_refs.py，程式為本專案重寫」。**必要**
5. 參考取得的使用者面文件寫明：are.na／Pinterest 圖片多為授權未知，只供讀不入成品。**必要**

---

## 看完整成品（brief 的成品是「一份提案」；出題者最後執行，獨立評審＋使用者各讀一次）
用 3 句：BL-6（＋PROJ-CAFE＋M-DROP）、BL-5、以及出題者臨時給的一句（建造者沒看過）。每份 brief 讀者只看 fenced prompt、fill-ins、聯絡單（不看程式、不看本卷），限時 60 秒讀完。

| 項目 | Kano | 理由 |
|---|---|---|
| **像專業導演的提案**：讀者（評審與使用者）都會說「這是一份可以交給剪輯師／動態設計師直接開工的提案」，不是一段形容詞 | 必要 | spec 驚豔時刻的原話 |
| **一眼看出它要長什麼樣**：讀完第一行就能說出美學（一個、具名），看聯絡單 5 張靜態確實是同一個美學，沒有一張「跑錯棚」 | 必要 | 混兩種美學是 spec 點名的未抵達 |
| **轉折是真的轉折**：讀者能用一句話說出「什麼變成什麼」，而且它跟主題有關（例：菜單紙捲起來變成杯中拉花），不是硬加的特效 | 必要 | 「進場、動、停住」不算完成 |
| **每張參考都看得出為什麼在那裡**：讀者隨機指 3 個 handle，都能在節拍裡找到它、說出取了什麼 | 必要 | 參考沒用途＝未抵達 |
| **只問真正的選擇**：fill-ins 每一項都是讀者會想參與的創意決定（例「轉折用翻頁還是溶解成拉花」），沒有「要 5 秒還是 10 秒」「直式還是橫式」這種例行問題；讀者可以只回 yes／no | 必要 | 「問一堆例行問題」是未抵達 |
| **它用了我的東西**：有素材時，讀者看得出提案是從自己的素材與品味出發（u 類 handle 指到自己的鏡頭），而不是一份放諸四海皆準的網路拼貼 | 必要 | 「比 blank-page 更好」的第一條 |
| **轉折落在音樂的爆點**：看 animatic／成片，轉折一出現就是 drop，沒有「早半拍」 | 必要 | 「節拍對齊音樂結構」 |
| **說 yes 就出片，說改一拍就只改那拍**：照提案出片後下 D-1，只有那一拍變、顏色沒變 | 必要 | 驚豔時刻後半段 |
| **讀起來不累**：60 秒內讀完並能複述節拍順序；沒有教學、理由、問候夾在 prompt 裡 | 必要 | 字數上限的目的 |
| 讀者會想把提案轉給同事看 | 加分 | 專業感的外溢 |
| 讀者看到某個參考或轉折時「沒想過可以這樣」 | 加分 | blank-page 的「探索你想不到的方向」 |
| 聯絡單排版美觀 | 無感 | 不影響決策 |
| prompt 裡出現「精緻」「高級感」「電影感」等無機制的形容詞當作主要描述 | 必要（不得出現） | 「擴寫只是加形容詞」是 spec 未抵達第 1 條 |

## 不算通過的樣子
- brief 很長很漂亮，但 lint 過不了或靠豁免過；豁免理由是「為了過 lint」。
- 參考看起來很美，但成片裡找得到參考圖（指紋檢查抓到），或用了 NC 資產。
- 轉折寫在 prompt 裡，但算繪後不在 drop（落差 > 1 格）。
- 「第二拍慢一點」後整支重算、顏色漂了。
- S-135 沒有登記就跑，或沒過就換題重跑；或只給使用者看靜態聯絡單。
- THIRD_PARTY 的版權行與 LICENSE 原文不符。
