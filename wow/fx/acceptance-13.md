# 答案卷 第十三輪 — 接上 GPT-Image-2.6：影像路由、分鏡關鍵格、身分參考庫、原生 GIF、透明資產、Markup 局部修改、SVG、多版本挑選、用量與來源（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-13.md（S-150..S-158）；spec-7.md（S-90..S-94 分鏡、S-92 動態分鏡的剪影卡）；spec-11.md（S-134 修改語法 delta／看圖回饋、S-130 分岔）；process.md（兩軸閘門：技術決定去留、好看由使用者；trunk-based、experimental 旗標）；
沿用 acceptance-11.md 的共通規則（技能 venv、`VIDEO_GIF_FFMPEG`、不改 examples/、ERR 信封、NETGUARD／NET-BLOCK、錄製匣、±1 格、指紋檢查）。出題者 2026-11-06 寫定。

出題者查得現況（HEAD b185890）：已有 `scripts/animatic.py`（`card()` 依 `size` 畫剪影卡）、`storyboard.py`、`storyboard_lint.py`、`gif_pipeline.py`、`qa_media.py`（`--loop` 接縫位置＋速度檢查）、`background_remove.py`（rembg 逐格遮罩）、`sprite_export.py`、`apply_mask_edits.py`、`brief_edit.py`（spec-11 delta）、`references/transparency.md`（「不得由棋盤格外觀推論透明」）。
Codex 的內建影像工具（`~/.codex/skills/.system/imagegen`）：預設走內建 `image_gen`（不需 `OPENAI_API_KEY`）；CLI／API 路線（`scripts/image_gen.py`）**只在使用者明示時**使用。內建工具**沒有**公開的遮罩、張數、模型、尺寸參數保證；編輯限於已在對話中可見的圖。
**出題時路線探測仍在跑**（`imagegen-probe/probe-alpha|probe-gif|probe-ref`）。因此本卷所有條件都寫成「兩條路線都適用」：路線支援某功能 → 驗原生結果；不支援 → 驗退路；**兩者都必須在能力表裡如實記錄是哪一條**。不得把未實測的功能寫成可用。

每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條），附理由。
CLI／欄位名以建造者文件為準；本卷用 spec 用語（`image_route`、`imagegen.py`、`capabilities.json`、`gen-manifest.json`、`cache_key`、`refset`、`keyframes/`、`markup`、`variants`），改名須在 references/ 寫明對應。若 spec-9 `vgs` 已存在，必須以 `vgs image …` 子命令提供（JSON 進出、ERR 信封）。

---

## 共通規則（第一～十二輪全部沿用，另加）

- **花費閘門（最高優先，任何一條違反＝整卷不過）**：
  - 付費 API 路線（gpt-image-2.6-flare／sunburst、`scripts/image_gen.py`、任何 `api.openai.com` 請求）**只能**在同時具備 (a) `--approve-spend <estimate_id>`（或建造者等價旗標）且 id 對得上**本次**預估、(b) 使用者在對話中明示同意 時執行。測試以 (a) 驗；(b) 由出題者與使用者確認紀錄。
  - **訂閱路線**（`codex exec` ＋ `image_generation`）是預設；呼叫子行程時**必須把 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_ORG*` 從子行程環境移除**（除非 API 已核准），並記錄 `codex login status` 的模式（ChatGPT 帳號／API key）。若 codex 本身是以 API key 登入 → 視同付費路線，未核准就拒絕（`E_ROUTE_BILLED`）。理由：Codex 用 API key 登入時，「訂閱路線」其實在扣 API 費。
  - 訂閱路線的每次 live 生成也算「生成額度」：本卷驗收的 live 生成總張數上限 **60 張**（含 holdout），超過須先問使用者。
- **兩層驗收**：
  - **離線層（決定性、CI 可跑）**：以 **FAKE-CODEX**（PATH 前置的假 `codex` 執行檔：記錄 argv、env、stdin，依錄製匣回傳圖片與訊息，計數呼叫次數）與 **FAKE-API**（localhost 哨兵 HTTP 伺服器；`OPENAI_BASE_URL` 指向它；計數請求數）跑。所有路由、快取、manifest、守衛、QA、退路的測試都在這層。
  - **live 層**：只在「看完整成品」、能力探測、與標明「live」的條目跑；每次 live 結果存證（圖、manifest、codex 紀錄路徑）。
- **NETGUARD**：照 acceptance-9／-11（`sitecustomize.py` 記 socket／getaddrinfo；psutil 監看子孫行程）。本卷另加 **API-SENTINEL**：在 hosts 層把 `api.openai.com` 解析到 FAKE-API（或攔截 getaddrinfo），任何對它的連線都被計數。未核准時計數必須 = 0（包含建造者程式本身與其所有子行程，**但不包含** codex 子行程自身對 ChatGPT 後端的連線——那是訂閱路線本體；出題者以 FAKE-CODEX 隔離此差異）。
- **能力表**：`capabilities.json`（每路線一列）欄位：`route`、`probed_at`、`evidence`（紀錄路徑）、`model_reported`（工具回報的字串或 `null`，**不得猜**）、`features`：{`native_gif`, `references_max`, `transparent_native`, `markup_edit`, `mask_edit`, `svg_native`, `n_per_call`, `aspects`, `max_size`, `quality_tiers`} 各為 `true|false|"untested"`＋證據。功能值必須來自實測（探測紀錄）或官方文件連結；第三方整理（eesel、OpenArt、TestingCatalog）只能寫成 `"claimed"`，不能寫 `true`。每個 S 的輸出 manifest 必須帶 `feature_used`（原生）或 `fallback`（退路名稱），且與能力表一致（能力表寫 false 卻宣稱原生＝不過）。
- **單位**：像素差以 8-bit 0–255；ΔE 用 CIEDE2000；長寬比誤差 = |w/h − 目標| / 目標。
- **報錯**：照 acceptance-9（非 0 結束碼、無 Traceback、`--json` stdout 單一 JSON、ERR 含 `code`／`location`／`suggestion`）。
- **trunk-based**：每個 S 一個切片；全套測試＋doctor 綠就以 `experimental` 合回 main；**本卷驗收通過前**，影像生成路徑預設不啟用（計畫須 `--experimental` 或 `"experimental": true`）。

## 合成素材與夾具（全部由測試程式以 numpy／PIL／ffmpeg lavfi 產生，或為錄製匣；不入庫任何 live 生成圖以外的網路圖）

| 代號 | 內容 | 已知答案／用途 |
|---|---|---|
| **SB-6** | storyboard.json：6 鏡、9:16、1080×1920、景別依序 EWS, WS, MS, CU, ECU, MS；主體「戴黃圍巾的紅髮咖啡師 Mia」＋道具「綠杯」；color_script 3 段（冷藍 #3A5A80 → 暖橘 #E08A3C → 奶白 #F2E8D8）；每鏡 `why`、`motion` 合法 | 關鍵格 6 張；景別單調遞增檢查用 |
| **REF-A** | 參考庫 A：Mia 的 8 張參考（live 預先生成一次後凍結入私有夾具目錄；離線層用合成替身 **REF-A-SYN**：程式畫的吉祥物，紅色圓頭、黃色圍巾帶、左臉頰藍色星形標記、綠杯） | 身分正樣本 |
| **REF-B** | 參考庫 B：另一角色（黑短髮、藍圍巾、無星標）8 張；合成替身 REF-B-SYN（藍方頭、紫圍巾、右臉三角標） | 負對照（已知不同） |
| **CAS-IMG** | FAKE-CODEX 錄製匣：每個請求 → 回傳圖檔＋文字回覆；含正常、錯誤長寬比（1024×1536）、無 alpha（RGB）、棋盤格畫進 RGB、配額錯誤訊息、逾時、整張重畫（markup 外溢）等情境 | 離線層 |
| **GIF-LOOP** | 合成 GIF：48 格、每格 40 ms、352×352（16 的倍數）、背景透明（binary），紅球繞圓一圈；第 48 格→第 1 格位移 = 一般步長 | 接縫 PASS |
| **GIF-SEAM** | 同上但最後 6 格被截掉（球停在 315°，跳回 0°） | 接縫 FAIL；修補後 PASS |
| **GIF-DISP** | 12 格、混用 disposal 1／2／3、部分格只覆蓋局部矩形、可變延遲（20, 40, 100, 2000 ms） | 解碼正確性 |
| **STK-RGBA** | 合成貼紙：800×800 RGBA，圓角星形，2 px 抗鋸齒邊、內部 α=255、外部 α=0，透明比例 0.55 | alpha 正對照 |
| **STK-CHECK** | 同形狀但背景是 16 px 灰白棋盤格（#FFFFFF／#CCCCCC）畫在 RGB、無 alpha 或 α 全 255 | 假透明（必須擋） |
| **STK-HALO** | STK-RGBA 但邊緣 3 px 混入白色背景色（未去溢色） | 白邊（必須擋） |
| **MK-BASE** | 1080×1920 關鍵格（SB-6 第 2 鏡，live 一張凍結＋合成替身：桌面上綠杯在已知 bbox (380,1100,320×360)） | markup 輸入 |
| **MK-NOTE** | 與 MK-BASE 同尺寸透明註記層：紅圈圈住杯子＋手寫箭頭 | markup 區域；外溢判定 |
| **SVG-OK** | 片名卡 SVG：路徑化文字「晨光咖啡」、3 條描邊路徑、線性漸層、viewBox 1080×1920 | 正樣本 |
| **SVG-BAD-1..7** | 分別含：`<script>`；`onload=`；`<foreignObject>`；`xlink:href="https://…"`；`<image href="data:image/png;base64,…">`；`style="background:url(http://…)"`／`@import`；`<!DOCTYPE … <!ENTITY …>` | 安全檢查必須逐一擋 |
| **FX-PRICE** | 價目表夾具（版本、日期、每張價格依 flare/sunburst × 品質 × 尺寸） | 預估費用 |

---

## S-150 影像路由（`image_route`）—— 必要（理由：其餘每個 S 都經過它；花錯錢或偷走 API 是唯一不可逆的錯誤）

**命令形狀**：
```
imagegen.py generate --prompt "<文字>" [--refs refset.json] [--size 1080x1920|--aspect 9:16] [--quality draft|final] [--n 1..8] \
    [--route codex|api|grok|auto] [--transparent] [--format png|gif|svg] [--approve-spend <estimate_id>] --out <dir> --json
imagegen.py estimate <同上參數> --json          # 只預估，不生成
imagegen.py probe [--route codex|api] --json     # 更新 capabilities.json
imagegen.py usage [--since 2026-11-01] --json
```
1. **預設路線 = codex**：不帶 `--route` 時 manifest `route: "codex"`；FAKE-CODEX 呼叫次數 = 1；FAKE-API 請求 = 0；codex 子行程 env 中**沒有** `OPENAI_API_KEY`（出題者以 FAKE-CODEX 記錄的 env 驗；母行程 env 先設假 key `sk-test-SENTINEL`）。**必要**
2. **API 路線未核准 → 拒絕且零請求**：`--route api` 不帶 `--approve-spend` → 非 0、`E_APPROVAL_REQUIRED`，ERR 內附預估（張數、單價、總額、價目表版本日期）與「如何核准」；API-SENTINEL 計數 = 0；`--approve-spend` 帶錯 id（別次預估、或參數改過後的舊 id）→ `E_APPROVAL_MISMATCH`，計數 = 0。帶正確 id → FAKE-API 恰 1 次請求、請求的 model／size／quality／n 與預估一致。**必要**
3. **auto 不會升級到付費**：`--route auto` 在 codex 失敗（CAS-IMG 逾時／不可用）時只能退到 Grok（若可用且已授權）或停止並報告；**不得**自動改走 API。FAKE-API 計數 = 0；manifest 寫 `fallback_chain` 實際嘗試的順序與失敗原因。**必要**
4. **codex 以 API key 登入時視為付費**：FAKE-CODEX 的 `login status` 回 "Logged in using an API key" → 未核准時 `E_ROUTE_BILLED`、0 次生成。**必要**
5. **快取**：`cache_key` = sha256(route, model 要求值, prompt 正規化後文字, 參數 {size, aspect, quality, n, transparent, format, seed 若有}, 參考圖 sha256 有序列表, 註記層 sha)。同一請求第二次：FAKE-CODEX／FAKE-API 呼叫 **0 次**、`cache_hit: true`、輸出檔 sha256 與第一次相同、牆鐘 ≤ 1 s。改任一欄（含換一張參考圖、只改參考順序、只改 quality）→ 必須 miss。快取路徑不入 git（`git ls-files` 無）。`--no-cache` 強制重生成並在 manifest 註明。**必要**
6. **prompt 正規化不過度**：只合併空白與 Unicode NFC；大小寫、標點、中英文字不同 → 不同 key（理由：「cafe」與「Café」可能出不同圖）。**必要**
7. **失敗不寫快取**：生成失敗、回傳 0 張、或 QA 判定壞圖（S-151.2 長寬比錯且無法修）→ 不寫入快取，下次同請求會重試。**必要**
8. **配額／重試**：CAS-IMG 配額錯誤 → 最多 2 次退避重試（間隔 ≥ 5 s、總等待 ≤ 60 s）後停止，`E_QUOTA`，manifest 記錄；不得無限重試、不得換付費路線。**必要**
9. **能力探測**：`probe` 產生 `capabilities.json`（見共通規則）；出題者比對探測紀錄（`imagegen-probe/*.log` 與建造者新跑的）：每個 `true` 都有證據檔；第三方說法只能是 `"claimed"`。**必要**
10. 路由決策可解釋：`--json` 輸出 `route_reason`（例「預設：訂閱；需要 GIF 原生，但 codex native_gif=false → 退路：frames→gif_pipeline」）。**加分**（理由：使用者一眼知道為什麼沒花錢、也知道少了什麼）

---

## S-151 分鏡關鍵格與動態分鏡 —— 必要（理由：spec 驚豔時刻第一句；把剪影卡換成真關鍵格是使用者看得到的最大變化）

**命令形狀**：`storyboard.py keyframes SB-6.json --refs refset.json [--quality draft] --out kf/ --json`；`animatic.py SB-6.json --keyframes kf/ --music <wav> --out animatic.mp4`。
1. **每鏡一張、對得上**：SB-6 產 6 張；`storyboard.json` 每鏡寫 `keyframe: {path, sha256, gen_manifest}`；提示詞由分鏡欄位組出（景別、構圖、色彩段、光線、主體、動作、參考 handle；沿用 S-93），出題者檢查 6 個 prompt 都含該鏡 `size` 的語彙（例「extreme wide」／「大遠景」）與該色彩段。**必要**
2. **9:16 與尺寸**：每張最終關鍵格長寬比誤差 ≤ 0.5%、短邊 ≥ 1080（draft 允許 ≥ 720 但 manifest 標 draft）。路線回傳別的比例（CAS-IMG 1024×1536）→ 依構圖做裁切或外延（outpaint／延伸背景），**不得非等比縮放**：manifest `reframe: {op, scale_x, scale_y, crop}` 且 `scale_x == scale_y`（±0.1%）；出題者以圓形測試物（合成替身中的杯口）長短軸比 ≤ 1.02 驗。主體在裁切後完整（主體遮罩接觸畫面邊緣的像素 ≤ 0.5%，ECU 除外）。**必要**
3. **景別有被遵守**：以主體遮罩（人物分割或 rembg；合成替身用已知顏色）量主體高佔畫面高的比例 h：
   - 單調性：EWS < WS < MS < CU ≤ ECU（SB-6 的 5 種景別 Spearman = 1.0；第 6 鏡 MS 與第 3 鏡 MS 的 h 差 ≤ 0.15）；
   - 絕對帶（C 類可校準，但不得只為過夾具改）：EWS h ≤ 0.20、WS 0.20–0.55、MS 0.45–0.85（主體被畫面下緣截在腰附近）、CU 臉／主物件寬 ≥ 畫面寬 0.45、ECU 細節（杯口或眼）寬 ≥ 畫面寬 0.6；
   - 不合 → 自動重生成該鏡至多 1 次（算額度）或標 `size_mismatch` 並在 animatic 標示，**不得**靜默接受。**必要**
4. **色彩段**：每張關鍵格的主色（k-means k=5 前 3 名）至少 1 個與該鏡 color_script 色票 ΔE2000 ≤ 15；6 張整體亮度／色溫順序符合 color_script（冷→暖→奶白的 b* 平均值單調不減）。**必要**
5. **取代剪影卡**：animatic 中每鏡的第一格（動作套用前）與該鏡關鍵格 ORB＋RANSAC 內點 ≥ 40（或 pHash ≤ 10），且與 `card()` 對同鏡的剪影卡 pHash ≥ 18；缺關鍵格的鏡（生成失敗）仍用剪影卡、畫面標「無關鍵格」、manifest 列出——**不得**整支 animatic 失敗。**必要**
6. **原本的分鏡檢查仍成立**：`storyboard_lint` 未豁免錯誤數與無關鍵格時相同；animatic 的 taste_report 可跑；鏡長、拍點對齊與 spec-7 S-92 相同（±1 格）。**必要**
7. **草稿→成品升級**：`--quality draft` 與 `final` 的映射寫在能力表（API：flare-low／sunburst-high；訂閱：若工具不給品質參數 → 寫 `quality_control: "prompt_only"`）；升級只重生成被選中的鏡（其他鏡 sha 不變）。**必要**
8. **只改一鏡**：改 SB-6 第 4 鏡的 `size`（CU→MS）再跑 → 只有第 4 鏡重生成（FAKE-CODEX 呼叫 +1，其餘 5 鏡快取命中）。**必要**
9. 每張關鍵格右下角在 animatic 中顯示景別／鏡號小標（可關）。**無感**（理由：剪影卡時代就有，使用者不會因此多注意）
10. 6 鏡 draft 關鍵格（訂閱路線 live）總牆鐘 ≤ 6 分鐘，並以 process scheduler 並行（不超過 codex 並行上限）。**加分**

---

## S-152 身分參考庫 —— 必要（理由：「角色一致」是驚豔時刻原話；不一致的分鏡導演不會收）

**命令形狀**：`imagegen.py refset build --name mia --images a1.png … [--role identity|costume|product|scene] --out refset.json`；generate／keyframes 帶 `--refs refset.json`。
1. **參考庫結構**：每個參考庫 ≤ 16 張（第 17 張 → `E_REFSET_LIMIT`，或依路線上限 `references_max` 更小者）；每張記 sha256、角色（identity／costume／product／scene）、來源（user／generated／web＋授權，沿用 S-131）；**實際送出的參考**逐張記在 gen-manifest（`refs_sent`），路線不收參考圖時寫 `refs_sent: []` 且 `fallback: "prompt_description"`——並在報告寫明「此路線未上傳參考圖，身分靠文字描述」（沿用 SKILL.md「描述照片≠上傳照片」）。**必要**
2. **量測工具與儀器先驗**：身分相似度用以下其一（依可得性，manifest 記錄用哪個與版本）：
   - 人臉：ArcFace 類人臉嵌入（如 InsightFace，需確認授權可用於本機評估）cos；
   - 物件／吉祥物：DINOv2 或 CLIP 影像嵌入 cos（以主體遮罩裁切後計）；
   - **退路**（無模型）：主體遮罩內 HSV 直方圖 Bhattacharyya 距離＋ORB 描述子比對（Lowe ratio 0.75）好匹配數。
   每次量測前跑**儀器先驗**：REF-A 內兩張不同姿勢（正對照）必須判同，REF-A vs REF-B（負對照）必須判不同；任一失敗＝儀器壞，不判作品。**必要**
3. **門檻（C 類，可用夾具校準後寫進 thresholds，附校準紀錄）**：
   - ArcFace：同一人 cos ≥ 0.45；負對照 ≤ 0.30；
   - DINOv2／CLIP（遮罩裁切）：同一 ≥ 0.70；負對照 ≤ 0.55；
   - 退路：Bhattacharyya ≤ 0.35 **且** ORB 好匹配 ≥ 25；負對照須 Bhattacharyya ≥ 0.50 或好匹配 < 10。
   **硬條件（不可校準掉）**：正樣本最小值 − 負對照最大值 ≥ 0.10（嵌入 cos）——分不開就是工具不可用。**必要**
4. **≥ 4 張關鍵格身分一致**：以 REF-A 生成 SB-6 中有主體的鏡（≥ 4 張，含 CU 與 WS），每張與參考庫質心的相似度都過門檻；**同時**每張與 REF-B 質心的相似度都 ≤ 負對照門檻。報告列每張數值。離線層用 REF-A-SYN（合成替身＋錄製匣），live 層用 REF-A。**必要**
5. **身分漂移處理**：任一張不過 → 該鏡重生成至多 1 次（加更多 identity 參考）；仍不過 → 標 `identity_fail`、animatic 標示、不得默默交付。**必要**
6. **跨用途共用**：同一 refset 用於關鍵格、影片首末格（Grok 路線 start/end image）、coverage（全景／中景／特寫）時，manifest 都記同一 refset sha。**必要**
7. **一個參考庫只能一個身分**：建庫時自檢——庫內兩兩相似度最小值低於負對照門檻（例混入另一角色）→ `E_REFSET_MIXED` 並指出可疑張數（holdout 會測）。**必要**
8. 身分一致性看片驗證：4 張關鍵格並排給使用者（與 REF-A 參考並列），問「是同一個角色嗎？」記錄回答。**必要**（理由：量測只是代理；spec 寫明「量測＋看片」）
9. 自動挑選參考子集（姿勢最接近目標景別者優先）。**加分**

---

## S-153 原生 GIF 動作來源 —— 必要（GIF→管線部分）／加分（與 Grok 比較的結論）
（理由：GIF 輸入管線是確定能用的工程；原生 GIF 生成是否在訂閱路線可用尚未確定，比較結論要看資料）
**命令形狀**：`imagegen.py generate --format gif --frames 2..64 --frame-ms 20..2000 --size 512x512 [--start-image x.png] …`；`gif_pipeline.py ingest in.gif --out frames/`；`qa_media.py frames/ --loop`；`sprite_export.py …`。
1. **參數驗證在花費前**：frames ∉ [2,64]、frame-ms ∉ [20,2000]、邊長非 16 的倍數 → `E_GIF_PARAMS`，0 次生成（FAKE 計數 = 0）。路線 `native_gif=false` → 報告並提供退路（多格靜態圖序列或 Grok 影片→GIF），manifest `fallback`。**必要**
2. **GIF 解碼正確**：GIF-DISP → 影格數 12、每格延遲與原檔逐格相同（ms 整數相等；瀏覽器 <20 ms 慣例另記但不改原值）、disposal 正確合成（出題者以 Pillow 參考解碼逐格比對 RGBA，最大差 = 0）。**必要**
3. **循環接縫 QA**：GIF-LOOP → `loop` PASS；GIF-SEAM → `loop` FAIL 並指出接縫格與 `seam_ratio`；提供至少一種修補（找最佳循環點裁切／交叉淡化／往返），修補後 PASS，manifest 記錄修補法與丟棄的格數。**必要**
4. **alpha 處理**：GIF 只有二值透明 → 影格 α ∈ {0,255}（不偽造半透明）；若是不透明背景 → 走既有去背（色鍵或 `background_remove.py`），標 `alpha_source: matted`；alpha QA 照 S-154 門檻。**必要**
5. **sprite 匯出**：sheet＋JSON 的每格延遲與 GIF 相同、pivot 固定、由 sheet 依 JSON 切回的每格與 frames/ 逐像素相同。**必要**
6. **與 Grok 技術軸比較（live）**：同 ≥ 3 題（角色待機、產品轉動、反應圖），記錄 {生成耗時、格數、接縫 seam_ratio、身分相似度（S-152 工具）、動作合理性（評審團瑕疵題：肢體斷裂、物件憑空出現）、額度用量}；寫入 `wow/fx/` 的比較 JSON。任一路線不可用 → 記「未跑＋原因」，不得用估計值填。**必要**（比較有紀錄）／**加分**（結論：哪類題目該走哪條）
7. 依比較結果更新路由預設（例：≤ 3 s、固定鏡頭的單一動作 → GIF 原生；有關節動作 → Grok）。**加分**

---

## S-154 透明資產 —— 必要（理由：貼紙／疊層是 GIF 工作室最常見的交付；假透明或白邊一眼就壞）

**命令形狀**：`imagegen.py generate --transparent --prompt "…貼紙…" --out st/`；`alpha_qa.py st/x.png --json`（或併入 qa_media）。
1. **真 alpha**：輸出 mode RGBA，α 不全為 255；透明比例（α=0 像素比）對貼紙 ∈ [0.15, 0.90]；畫面四邊外框 2 px 內 α=0 的比例 ≥ 99%（主體沒被切到）。STK-RGBA 過；STK-CHECK 必須被判為 `fake_transparency`。**必要**
2. **棋盤格偵測**：對 α=255 或無 alpha 的圖，檢查 RGB 中的週期性兩色格（灰／白、塊寬 8–32 px）：在背景候選區（畫面邊緣連通區域）以自相關或 FFT 峰值偵測，峰高 ≥ 0.5 且兩色差 ∈ [10, 60] → 判棋盤格。STK-CHECK 必中；真照片（含格紋桌布的合成正常圖）不得誤報（負對照）。**必要**
3. **無白邊／色邊（halo）**：分別疊在黑、白、品紅背景；在 α 0.5 等值線外 1–3 px 帶與內 1–2 px 帶，量 (a) 疊黑時外帶平均亮度 − 背景 ≤ 8；(b) 半透明像素去預乘後的 RGB 與最近 α=255 內部像素顏色 ΔE ≤ 20 的比例 ≥ 95%（不帶原背景色）。STK-HALO 必須被擋（至少一項超標）；STK-RGBA 必過。**必要**
4. **雜點**：α>0 的連通區除主體外，面積總和 ≤ 主體 0.1%；主體內部 α<255 的洞（非設計的）≤ 主體 0.5%。**必要**
5. **原生 vs 退路**：能力表 `transparent_native` 為 true → 驗原生 alpha；false 或回傳 RGB／棋盤格 → 自動退路：同 prompt 指定單色背景（與主體色距離 ΔE ≥ 30，自動選色）生成 → 色鍵或 `background_remove.py` 去背＋去溢色 → 同 1–4 門檻；manifest `alpha_source: native|matted`、退路參數。**不得**把棋盤格圖當透明交付。**必要**
6. 交付同時給 RGBA PNG 主檔與 GIF 相容版（α<128 → 透明），APNG 若有動態。**必要**（沿用 transparency.md）
7. 半透明素材（玻璃、煙）保留分級 alpha（α 介於 1–254 的像素 ≥ 5% 的主體面積），不被二值化。**加分**

---

## S-155 Markup 局部修改 —— 必要（理由：驚豔時刻後半句「只有那個杯子被改掉」）

**命令形狀**：`imagegen.py edit --image MK-BASE.png (--markup MK-NOTE.png | --region bbox|polygon|auto:"杯子") --instruction "改成拿鐵" --out ed/ --json`；delta 進入：`brief_edit.py "第二鏡的杯子改成拿鐵" --project …`。
1. **delta → 註記層**：spec-11 修改語法解析「第二鏡的杯子改成拿鐵」→ target shot 2、element 杯子；自動產生與 MK-BASE 同尺寸的註記／遮罩（偵測或使用者點選），與已知杯子 bbox IoU ≥ 0.5 且完整包住杯子（杯子像素被覆蓋 ≥ 98%）。**必要**
2. **未註記區像素差 ≈ 0**：令 R＝註記區域膨脹 m 像素（m = 短邊 2%＝22 px @1080）。R 外：平均 |Δ| ≤ 1.0、99.9 百分位 |Δ| ≤ 8、|Δ|>10 的像素比例 ≤ 0.1%；尺寸與 MK-BASE 相同（不可回傳不同尺寸還宣稱成功）。**必要**
3. **R 內真的改了**：R 內（原杯子遮罩）平均 ΔE2000 ≥ 8 或 SSIM ≤ 0.85；看片確認變成拿鐵（杯中有奶泡／拉花、杯型合理），由出題者與使用者各看一次。**必要**
4. **退路（路線沒有 markup／遮罩編輯，或原生結果外溢）**：以遮罩合成：結果 = R 外取 MK-BASE 原像素（位元相同）、R 內取編輯結果，邊緣羽化 ≤ 8 px；編輯結果若有位移／縮放，先以 ECC 或特徵配準（殘差 ≤ 1 px）再合成，manifest 記錄 `fallback: "mask_composite"`、配準參數、外溢量（合成前 R 外原始差異統計）。CAS-IMG「整張重畫」情境 → 退路後 R 外羽化帶以外 sha 與 MK-BASE 位元相同。**必要**
5. **縫隙不顯**：羽化帶內與外側的平均亮度差 ≤ 3、無可見硬邊（羽化帶梯度最大值 ≤ 1.5 × 周圍自然梯度第 95 百分位）。**必要**
6. **只動該鏡**：其他 5 鏡的關鍵格 sha 不變；animatic 只重算第 2 鏡（＋相鄰轉場）。版本記錄 v1→v2（沿用 S-113）。**必要**
7. 看圖回饋（在聯絡單上圈）直接成為註記層。**加分**

---

## S-156 SVG 向量素材 —— 必要（安全與清晰）／加分（動畫化）
（理由：SVG 是可執行內容的載體，安全是硬條件；清晰是用 SVG 的唯一理由）
**命令形狀**：`imagegen.py generate --format svg …`；`svg_safe.py in.svg --out clean.svg --json`；`svg_render.py clean.svg --sizes 512,2048,4096`；fx 層 `stroke_grow`／`mask_reveal` 吃 SVG。
1. **安全檢查**（以 defusedxml 解析；不執行任何外部載入）：SVG-BAD-1..7 每一個都被擋（拒絕或淨化後重驗為乾淨，並在報告列出被移除的節點）：`<script>`、任何 `on*` 屬性、`<foreignObject>`、`href`／`xlink:href` 非 `#` 開頭、CSS `url(` 指外部或 `@import`、任何 `<image>`（含 data: 點陣）、DOCTYPE／ENTITY、`javascript:`。SVG-OK 零誤報。所有進 fx 的 SVG 都必須先過此檢查（從管線入口測：直接把 SVG-BAD-1 餵給 fx_render → ERR）。**必要**
2. **三種解析度一樣清晰**：在短邊 512、2048、4096 光柵化（resvg 或 cairosvg，記版本）：(a) 直邊的 10–90% 過渡寬 ≤ 1.5 px（每個解析度都成立）；(b) 4096 版降到 512 與直接 512 版 SSIM ≥ 0.98；(c) 無點陣放大痕跡（4096 版邊緣過渡寬 / 512 版 ≤ 1.2，而非 ×8）。**必要**
3. **文字可攜**：`<text>` 必須轉成路徑或使用本機打包且記錄授權的字型；不得依賴系統字型（換一台沒字型的機器渲染結果相同：出題者在空字型目錄的環境渲染，SSIM ≥ 0.99）。**必要**
4. **退路**：路線無 SVG 原生 → (a) 由程式直接撰寫 SVG（Codex imagegen 技能本身建議向量用程式產生）或 (b) 點陣描摹（vtracer／potrace，記錄參數與節點數），manifest `svg_source: native|authored|traced`；三者都過 1–3。**必要**
5. **動畫化**：描邊生長（stroke-dasharray 沿路徑長）與遮罩揭露：覆蓋率隨時間單調不減、末格與靜態光柵化 SSIM ≥ 0.99、無單格閃爍（fx_gate_kit）；進 experimental 效果，兩軸閘門照 process.md。**加分**
6. 檔案大小 ≤ 200 KB（片名卡等級）且節點數記錄。**無感**（理由：使用者不看大小，除非出問題）

---

## S-157 多版本挑選 —— 必要（理由：spec「你挑一個方向」；兩軸閘門規定好看由使用者決定，這頁就是使用者決定的地方）

**命令形狀**：`imagegen.py variants --shot 2 --n 4 --refs refset.json --out var/ --json`；`variants_page.py var/ --out pick.html`；`variants_pick.py var/ --choose v3`（或頁面寫回 JSON）。
1. **n 範圍**：n ∈ [2,8]；n=1 或 n=9 → `E_VARIANTS_N`，0 次生成。路線 `n_per_call` < n → 多次呼叫，manifest 記錄呼叫數與每次張數；快取以單張為單位（同請求重跑 0 次生成）。**必要**
2. **真的不同**：兩兩感知距離：pHash ≥ 10 或 DINOv2／CLIP cos ≤ 0.95；有 brief 分岔（spec-11 `forks[]`）時，每個候選對應一個分岔方向並標 `fork_id`。**同時**有 refset 時身分仍一致（S-152 門檻）。**必要**
3. **動態預覽頁**：本機 HTML、離線可開（NETGUARD 0 外連、不載入 CDN）；每個候選以會動的預覽呈現（該鏡 animatic 片段或 Ken Burns／運鏡 2–4 s，`<video>` 或 GIF，至少 2 個不同格）——**不得只放靜態縮圖**（沿用 process.md：使用者抽查用會動的）；標示 9:16 安全區；並排比較、鍵盤 1–8 選。**必要**
4. **選擇有紀錄且生效**：選擇寫入 `picks.json`（shot、variant id、sha256、fork_id、時間、`chooser: user`）；storyboard 該鏡 `keyframe` 換成選中的 sha；未選的保留可回溯。AI 評審若給排序，標 `advisory: true`，**不得**自動代選。**必要**
5. 使用者選擇累積進品味檔（spec-7 S-87），之後預設排序參考它。**加分**

---

## S-158 用量與來源紀錄 —— 必要（理由：花費透明與 AI 來源標示是信任問題）

1. **每次生成一筆 manifest**（`gen-manifest.json`，append-only ledger 另存）：`route`、`model_reported`（工具回報；沒回報寫 `null` 並 `model_assumed` 分開寫）、`quality`、`size_requested`、`size_actual`、`aspect_actual`、`n_requested`、`n_returned`、`elapsed_s`、`prompt_sha`、`refs_sent`、`feature_used|fallback`、`cache_hit`、`c2pa_present`、`c2pa_claim_generator`（若有）、`synthid: "not_verifiable_locally"`、`cost_estimate_usd`（API）或 `subscription_images`（訂閱）、`approval_id`（API）。出題者以 jsonschema 驗每筆，FAKE 情境 10 種全部合法。**必要**
2. **C2PA 偵測是真的讀**：以 c2pa 函式庫／c2patool 讀（或至少偵測 PNG `caBX` chunk／JPEG APP11 JUMBF 並註明「僅偵測存在、未驗簽」）；有 C2PA 的夾具 → true、剝除後 → false、無法判斷 → `"unknown"`（不得預設 true）。衍生檔（裁切、去背、影格）記 `derived_from` 原始 sha 與其 C2PA 狀態；交付文件標示「含 AI 生成影像」。spec-12 S-144 可讀到此欄。**必要**
3. **API 預估與核准**：`estimate` 依 FX-PRICE（版本與日期寫在輸出）算出總額；超過 `--max-usd`（預設 0）→ 拒絕；核准紀錄（estimate_id、金額、時間）寫入 ledger；實際張數 > 預估 → 停止並報。**必要**
4. **訂閱用量**：`usage` 依日／依專案彙總張數、失敗數、快取命中數、平均耗時；與 ledger 逐筆加總一致。**必要**
5. 交付報告一行摘要：「本片 14 張 AI 影像，訂閱路線，快取省下 5 張，0 美元 API」。**加分**

---

## 看完整成品（出題者最後執行，live；獨立評審＋使用者各看一次）
用 SB-6（Mia、9:16、6 鏡）＋REF-A，跑：關鍵格 → animatic → 第 2 鏡出 4 個候選並由使用者挑 → 「第二鏡杯子換成拿鐵」→ 一張透明貼紙＋一張 SVG 片名卡進 animatic 開頭。讀者只看 animatic、6 張關鍵格聯絡單、候選頁、修改前後對照（不看程式與本卷）。

| 項目 | Kano | 理由 |
|---|---|---|
| **導演會收這套分鏡格**：讀者說「這可以當分鏡／動態分鏡交給拍攝或生成」，不是 6 張隨機好看的圖 | 必要 | spec 驚豔時刻 |
| **景別一眼分得出**：不看標籤，讀者能正確說出 6 格中哪格是大遠景、哪格是特寫（≥ 5/6 正確） | 必要 | 景別錯＝分鏡無用 |
| **9:16 構圖是為直式設計的**：主體與頭頂空間、字幕安全區都對；不是橫圖硬裁（沒有被切半的頭、沒有大片空白） | 必要 | spec「9:16 關鍵格」 |
| **同一個角色**：讀者看 4+ 張有主體的格說「是同一個人／同一隻吉祥物」——髮色、圍巾、臉部標記、杯子一致 | 必要 | 身分一致 |
| **色彩段看得出**：冷→暖→奶白的走向在 6 格中可見 | 必要 | color script |
| **品味不是 AI 平均**：讀者不會說「一看就是 AI 預設風」（光線、構圖有意圖；與 autoplan 無 refset 版並排可分辨） | 必要 | spec-7 S-82 遠離 AI 平均 |
| **剪影卡被取代後節奏仍在**：animatic 的鏡長、轉場、拍點跟剪影卡版一樣，只是畫面變真 | 必要 | 不能為了畫面毀了節奏 |
| **候選真的是不同方向**，而且在會動的預覽裡比較得出差別；挑完後 animatic 用的就是挑中的那張 | 必要 | 使用者決定好看軸 |
| **只有杯子變了**：修改前後快速切換，讀者只看得到杯子變拿鐵，背景、手、光線沒跳 | 必要 | 驚豔時刻後半 |
| **貼紙在深色與淺色背景上都沒有白邊或灰格子** | 必要 | 假透明是最常見失敗 |
| **片名卡放大看仍銳利**，字是對的中文、沒有錯字或亂碼 | 必要 | SVG 的存在理由；中文渲染是 2.x 已知弱點 |
| 讀者想直接拿關鍵格去做成片 | 加分 | 外溢價值 |
| 有讀者沒想到的構圖或光線 | 加分 | 驚豔 |
| 關鍵格角落的小標樣式 | 無感 | 不影響決策 |

## 不算通過的樣子
- 任何一次未核准的 API 請求（含 codex 以 API key 登入卻被當成訂閱）。
- 能力表寫 `true` 卻沒有證據；或把第三方整理的功能當成已驗證。
- 關鍵格是 2:3 被拉成 9:16（非等比）；或 9:16 但主體被裁掉頭。
- 身分「一致」只靠同一段文字描述，卻宣稱有上傳參考圖。
- 透明貼紙其實是棋盤格；或去背後一圈白邊。
- 杯子改了，但背景整體色偏或細節被重畫（R 外差異超標），還宣稱成功。
- SVG 帶 `<script>`／外部 href 進了 fx 管線。
- 同一請求第二次又生成了一次。
- 候選頁只有靜態縮圖，或 AI 替使用者選了。
