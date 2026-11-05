# 答案卷 第九輪 — 導演的工作台：統一 CLI、MCP、看的原語、專案版本、語意搜尋、OTIO/FCPXML、導演評測基準（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-9.md（S-110..S-116）、wow/fx/spec-4.md（S-36 鏡頭卡、S-37 storyboard、S-42 盲評）、wow/fx/spec-7.md（S-80 taste_report、S-87 一致率）、
wow/fx/acceptance-5.md（共通規則、PROBE、報錯定義、±1 格、合成素材）。出題者 2026-11-05 查得現況：
scripts/ 已有 `fx_render.py`（`--list --json --validate --preview --review-html --previous --decisions --platform --proxy`）、`qa_media.py`、`review_pair.py`（A/B 時間對齊比較板）、
`review_shots.py`、`intake.py`、`captions.py`、`music_fit.py`、`music_sync.py`、`sfx.py`、`reframe.py`、`fx_reverse.py`、`beat_layers.py`；
**尚不存在**：`shot_index.py`（S-36）、`fx_lint.py`（S-38）、`taste_report.py`（S-80）、`cam_query`（spec-8）、任何 `vgs` 入口、MCP、OTIO。

每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條），附理由。
CLI／欄位名以建造者文件為準；本卷用 spec 用語（`vgs <verb>`、`--json`、`vgs schema`、`vgs look`、`vgs diff`、`vgs revert`、`vgs find`、`vgs export`、`vgs bench`），改名須在 references/ 寫明對應。

## 共通規則（第一～八輪全部沿用，另加）
- 技能 venv、ffmpeg 經 `VIDEO_GIF_FFMPEG`、不得改 examples/、不得改本答案卷、離線測試不下載／不讀真實權重、付費哨兵計數 = 0。
- **報錯**（沿用並加強）：非 0 結束碼、stdout／stderr 皆**無** `Traceback (most recent call last)` 字樣、不建立 `--out`／不寫入專案資料夾、牆鐘 < 3 s；
  `--json` 模式下 stdout 是**單一**合法 JSON 文件（`json.loads(stdout)` 成功，前後無雜訊、無進度條、無 ANSI 色碼），進度與日誌只能寫 stderr。
- **錯誤信封**（S-110 定義，下文簡稱 ERR）：`{"ok": false, "error": {"code", "location", "message", "suggestion", "options"}}`；
  `code` 為文件化的穩定列舉（例 `E_SCHEMA`、`E_NOT_FOUND`、`E_RANGE`、`E_UNSUPPORTED`、`E_NOT_IMPLEMENTED`、`E_CONFLICT`、`E_IO`、`E_CANCELLED`），
  `location` 為 JSON Pointer（RFC 6901，例 `/events/3/intensity`）或 `argv[2]`／檔案路徑，`options` 為陣列（可為空，但列舉型錯誤必須非空）。
- **成功信封**：`{"ok": true, "verb", "schema_version", "data", "meta"}`；所有隨時間變動的欄位（牆鐘、時間戳、絕對暫存路徑、pid）**只准放在 `meta`**。
- **量測不信任建造者**：時間、尺寸、熱點位置、拍點位置、OTIO 剪點皆由出題者從**輸出檔**量（PIL／numpy／ffprobe／opentimelineio），自報值只用來比對誠實度。
- **±1 格** = 輸出 fps 的一格（30 fps → 33.33 ms）。
- **網路守衛**（下文簡稱 NETGUARD）：出題者 harness 以環境變數 `PYTHONPATH=<guard_dir>` 注入 `sitecustomize.py`，把 `socket.socket.connect/connect_ex/bind/sendto`、
  `socket.create_connection`、`socket.getaddrinfo` 包成「記錄後放行」並把呼叫紀錄寫 JSON；另以 psutil 每 100 ms 取伺服器行程＋全部子孫行程 `net_connections(kind='inet')`。
  **允許**：Windows asyncio Proactor 事件迴圈以 `socket.socketpair()` 建的自用 loopback 對（兩端皆 127.0.0.1、無 LISTEN 狀態殘留、建立後 1 s 內不再有新的 bind）——須在文件寫明；
  **不允許**：任何非 loopback 位址、任何持續 LISTEN 的埠、任何 `getaddrinfo` 對外主機名、任何 HTTP(S)。
- **token 計數**：以 `tiktoken` 的 `cl100k_base` 計（作為各家 agent 的近似；未安裝時以 UTF-8 位元組數 ÷ 3 上取整代替，兩者取較大值判定）。

## 合成素材（全由測試程式以 numpy／PIL／ffmpeg lavfi 產生，不入庫真實影片）
| 代號 | 內容 | 用途 |
|---|---|---|
| BAR30 | 1920×1080、30 fps、10 s（300 格）mp4：每格燒入**格號條碼**（16 個 96×96 黑白方塊二進位，置中，JPEG 壓縮後仍可讀）＋左上角秒數文字 | S-112 取格精度 |
| BAR30V | 同 BAR30 但 1080×1920 直式 | 9:16 安全區、A/B |
| CHG-A / CHG-B | 兩支 1080×1920、30 fps、6 s 算繪：同一計畫，B 只在 2.0–3.0 s 把畫面 (x 400–600, y 900–1100) 的 200×200 方塊顏色由 (40,40,40) 改為 (230,60,60)，其餘逐位元相同（以 PNG 序列再編碼，`-crf 0` 或 PNG 格式） | S-112 熱圖 |
| CLK120 | 48 kHz mono 8 s：120 BPM、首拍 250 ms 的 1 kHz 10 ms click（−6 dBFS），其餘 −40 dBFS 粉紅噪；附 beats.json（16 拍） | S-112 波形＋拍點 |
| PROJ5 | 專案：5 段素材（lavfi testsrc2／smptebars／mandelbrot／life／rgbtestsrc，各 1080×1920、30 fps、4 s，各附不同 1 kHz 倍頻 click 當指紋）＋SONG（120 BPM 10 s）＋storyboard（5 鏡、每鏡有 transition、2 個效果事件、why 欄） | S-113、S-115、看完整成品 |
| CARDS40 | 40 張假鏡頭卡 JSON（S-36 格式；`description` 為中英文短句，例「夕陽下的人走過海邊」「a red car at night」），附 40 張 64×64 純色縮圖 | S-114 |
| BENCH-STUB | 3 題迷你基準（每題 1 段 lavfi 素材＋一句想法），以及「假評審」：只看檔案內嵌的隱藏分數（例 mp4 metadata `comment=score:0.7`）決定勝負，可設成偏好 A、偏好 B、平手、順序偏誤 | S-116 |

基準指令（名稱以建造者為準）：
```
vgs schema render --json
vgs render D/plan.json --out D/out --json
vgs look frame D/BAR30.mp4 --t 4.5 --out D/look --json
vgs look diff D/CHG-A.mp4 D/CHG-B.mp4 --out D/look --json
vgs diff D/proj v3 v4 --json ; vgs revert D/proj v3 --json
vgs find D/proj "夕陽下的人" --json
vgs export D/proj --format otio|fcpxml --out D/x
vgs bench run --baseline <ref> --candidate <ref> --json
python -m vgs.mcp   # 或文件化入口；stdio
```

---

## S-110 統一 CLI＋JSON 介面 —— 必要（理由：agent 錯一個欄位就重來＝工作台不存在；這是 S-111～S-116 的地基）
1. **動詞齊全**：`vgs verbs --json` 列出 spec 的 13 個動詞（analyze、plan、lint、preview、render、qa、taste、query-fx、query-cam、captions、music、intake、export）＋本輪新增（look、diff、revert、find、bench、schema、job）；
   每個動詞帶 `status ∈ {stable, experimental, not_implemented}` 與後端腳本名。後端尚未存在者（現況：analyze→shot_index、lint→fx_lint、taste→taste_report、query-cam→cam_query）
   呼叫時回 ERR `E_NOT_IMPLEMENTED`，`message` 指出待哪個 spec／S 編號，**不得**假裝成功或回空資料。**必要**（理由：誠實回報缺口比假成功好，agent 才會改走別路）
2. **每個動詞都有 JSON Schema**：`vgs schema <verb>` 回傳輸入 schema（`--output` 另回輸出 schema）；出題者以 `jsonschema` 的 Draft 2020-12 metaschema 驗證**每一份** schema 合法；
   每份 schema 至少含 1 個 `examples`，且 example 通過該 schema 驗證、實際以該 example 執行（可用 `--dry-run`）回 `ok: true`。**必要**
3. **先驗證再執行**：`vgs validate <verb> input.json`（或 `--dry-run`）只驗證不執行、不建任何檔；與真執行的驗證結果一致（同一組 30 個壞輸入，兩者回同 code 與 location）。**必要**
4. **錯誤格式**：對每個動詞餵以下壞輸入，全部符合「報錯」＋ERR：
   (a) 缺必填欄位 → `E_SCHEMA`、location 指向父物件、message 寫欄位名；
   (b) 型別錯（`"fps": "30"`）→ location `/fps`、suggestion 含正確型別；
   (c) 列舉錯（`"transition": "crossfdae"`）→ `options` 列出全部合法值，且第一個是最接近的（Levenshtein 最小）`crossfade`；
   (d) 範圍錯（`"intensity": 7`）→ `E_RANGE`、suggestion 含合法範圍；
   (e) 檔案不存在 → `E_NOT_FOUND`、location 為該路徑欄位；
   (f) 未知欄位（`"intesity": 0.5`）→ 報錯或警告（文件寫明哪種），並建議 `intensity`。
   以上 6 類 × 13 動詞（not_implemented 者只測 (a)(b)），**100%** 無 traceback。**必要**
5. **JSON 輸出穩定**：同一輸入跑 3 次（含不同工作目錄、不同 `PYTHONHASHSEED`），去掉 `meta` 後 stdout **位元組相同**；鍵序固定（排序或 schema 順序，文件寫明）；
   浮點固定精度（文件寫明，例 6 位小數）；路徑一律 POSIX 斜線、相對於專案根（或文件化為絕對）；Windows 與 POSIX 同義輸出。**必要**（理由：agent 拿 diff 判斷有沒有變，輸出飄就誤判）
6. **輸出符合自己的輸出 schema**：每個動詞成功輸出以 `vgs schema <verb> --output` 驗證 100% 通過；`schema_version` 存在，改 schema 時版本號增加（看 git 歷史）。**必要**
7. **舊腳本保留且等價**：`vgs render plan.json --out A` 與 `python scripts/fx_render.py plan.json --out B`（同旗標）輸出 frames sha256 逐格相同；
   第一～八輪既有測試全綠（共通規則「舊計畫不退步」）。**必要**
8. 結束碼文件化：0 成功、1 使用者輸入錯、2 內部錯、3 被取消（或等效表），出題者抽 5 種情況核對。**加分**
9. `vgs <verb> --help` 文字精簡（≤ 40 行）且每個旗標對應 schema 欄位。**無感**（理由：agent 看 schema，不看 help；不得抵其他條）

## S-111 MCP 伺服器 —— 必要（理由：spec 的驚豔時刻「在任何支援 MCP 的 AI 裡說一句」直接依賴它）
1. **啟動與握手**：出題者以官方 `mcp` Python SDK 的 stdio client（或手寫 JSON-RPC 2.0 over stdio）啟動伺服器：`initialize` 在 5 s 內回應，`serverInfo` 有名稱與版本，
   `capabilities.tools` 存在；送 `notifications/initialized` 後 `tools/list` 成功。stdout 只有 JSON-RPC 訊息（一行一則或文件化框架），日誌全在 stderr。**必要**
2. **工具列表**：每個 stable／experimental 動詞一個工具（或文件化的合併方式），每個工具有 `name`、`description`、`inputSchema`（type=object），
   `inputSchema` 與 `vgs schema <verb>` **語意等價**（出題者以 30 個樣本輸入在兩邊驗證結果一致）；not_implemented 的動詞**不得**出現在工具列表（或明確標示且呼叫回結構化錯誤）。**必要**
3. **逐一呼叫**：對工具列表中每個工具，以其 schema 的 `examples[0]`（在 PROJ5 上）呼叫 `tools/call` → `isError` 為 false、`content` 含 `type: text` 的 JSON（可 `json.loads`）；
   產出圖像的工具，結果附**可直接讀的縮圖路徑**（存在、JPEG、≤ 1280 px），或 `type: image` 內容（≤ 1280 px，base64 解碼 ≤ 300 KB）。**必要**
4. **錯誤走 MCP 慣例**：參數錯 → `tools/call` 結果 `isError: true` 且文字內容為 S-110 ERR（code/location/suggestion/options 齊全）；伺服器**不崩潰**，下一個呼叫正常。
   未知工具名 → JSON-RPC error（-32602 或 -32601，文件寫明）。**必要**
5. **長工作**：`render`（PROJ5 正式算繪）呼叫在 **≤ 2 s** 內回傳 `job_id`（不阻塞到算完）；`job_status`（或文件化工具）輪詢：`progress` ∈ [0,1] **單調不減**、
   至少 3 個不同中間值、最後 `state: done` 並附輸出路徑與縮圖；若 client 帶 `progressToken`，另發 `notifications/progress`（**加分**）。
   不存在的 job_id → ERR `E_NOT_FOUND`。**必要**
6. **零網路**：整個測試會話（握手→列表→逐一呼叫→長工作）在 NETGUARD 下：非 loopback 連線 0、LISTEN 埠 0、對外 getaddrinfo 0。
   另以 `--offline` 預設：即使環境有 `HTTP_PROXY`，也不嘗試連線。**必要**（理由：spec「本機 stdio，零網路」）
7. **工具描述 token 預算**：`tools/list` 回應整份（含所有 inputSchema）序列化後 **≤ 6 000 tokens**；每個工具 `description` **≤ 120 tokens**；
   每個 description 第一句說「做什麼」、並含「何時用」或一個最小範例（出題者抽 5 個人工確認）。超過 → 不過。**必要**（理由：spec「未抵達：工具描述吃光 token」；6 000 約為 agent 上下文 3%，出題者自訂，可校準）
8. **與 CLI 共用核心**：同一輸入經 MCP 與經 `vgs --json` 的 `data` 位元組相同（去 `meta`）。**必要**（理由：防止兩套邏輯分岔）
9. 在 Claude Code（`.mcp.json` 範例）與 Codex（`config.toml` 範例）的設定片段入庫，且出題者依片段實際註冊成功、能列出工具。**加分**
10. 伺服器關閉：client 關閉 stdin → 伺服器 5 s 內結束，無殘留子行程（psutil 確認），進行中的 job 標 `cancelled`。**必要**

## S-112 導演的眼睛（看的原語）—— 必要（理由：agent 看不到自己的作品就無法自我修正；大圖吃光 token＝spec 明列的未抵達）
共同：所有 `vgs look *` 輸出 **JPEG**（檔頭 `FF D8 FF`），長邊 **≤ 1280 px**（預設；`--max-px` 可調小，調大超過 1280 須明確旗標並警告），單張 **≤ 300 KB**；
JSON 回應列出每張圖路徑、尺寸、對應時間（ms）與格號。
1. **尺寸上限**：對 BAR30（1920×1080）、BAR30V（1080×1920）及 4K lavfi 片各取格、聯絡表、A/B、熱圖、波形：PIL 讀出 `max(w,h) ≤ 1280`、format = JPEG、檔案大小 ≤ 300 KB，100% 成立。**必要**
2. **指定時間取格精度**：BAR30 上請求 t ∈ {0, 0.5, 1.0333, 4.5, 9.9667} s 與 20 個隨機 t：讀回 JPEG 的條碼得格號 k，|k − round(t·30)| ≤ 1（±1 格）；回應自報格號與條碼一致 100%。
   請求 t > 片長 → ERR `E_RANGE`，options/suggestion 給有效範圍。**必要**
3. **事件前後聯絡表**：給 manifest 中某事件 → 一張圖含事件前 N、事件格、事件後 N 格（預設 N 文件寫明），每格標時間；出題者以條碼核對每格格號 ±1，順序遞增。**必要**
4. **A/B 並排**：兩支同長片（BAR30V 與其色彩反轉版）同時間 t → 一張圖左 A 右 B（或上下，文件寫明），兩半條碼格號相同 ±1，A／B 標籤可見；`--offset` 可對齊不同起點。可沿用 review_pair.py。**必要**
5. **差異熱圖**：CHG-A vs CHG-B：(a) 2.0–3.0 s 內任一格熱圖：熱點像素（熱圖亮度 ≥ 文件化門檻）外接框與改變區（縮放到熱圖座標後）**IoU ≥ 0.7**，區外熱點面積 ≤ 1%；
   (b) 0–2 s 與 3–6 s 的格：熱點面積 ≤ 0.5%（編碼雜訊不得被當成差異）；(c) JSON 回報差異時間段 = [2.0, 3.0] s ±1 格與 bbox。**必要**
6. **波形＋拍點＋事件疊圖**：CLK120 ＋ PROJ5 manifest 事件 → 一張圖：波形（clicks 為明顯尖峰）、拍點標線、事件標記；出題者由圖上偵測拍點標線 x 與尖峰 x，
   換成時間後與 beats.json 差 ≤ max(2 px, 1 格)；事件標記 x 與 manifest 事件時間差同上。**必要**
7. **9:16 安全區疊圖**：BAR30V 上疊 S-52 文件化安全區（上 ≥ 10%、下 ≥ 20%、右 ≥ 10%），出題者量疊圖邊界像素位置與文件數值差 ≤ 1%（高或寬）。**必要**
8. **token 效率**：一次「看 10 s 成片」的預設聯絡表（例 3×4 格）＝ 1 張 ≤ 1280 px 圖；`vgs look` 預設不回 base64（只回路徑），除非明示 `--inline`。**加分**（理由：同樣資訊花最少 token）
9. 熱圖在大量差異（整片換色）時給文字摘要「幾乎全畫面改變」而非一張全紅圖。**加分**

## S-113 專案與版本 —— 必要（理由：「第三鏡換掉」只重做那一鏡、事後說得出為什麼，靠的就是版本與理由）
1. **專案結構**：`vgs init`（或 analyze 自動建）PROJ5 → 文件化資料夾：素材索引、treatment、storyboard、plan、`versions/vN/`（每版：計畫快照、manifest、輸出、縮圖、決定紀錄）；
   每版有內容雜湊（計畫＋素材雜湊）與父版號。**必要**
2. **語意 diff**：v3 = PROJ5 原樣算繪；v4 = 只改 (i) 第 3 鏡 transition `crossfade → whip`、(ii) 事件 `e5.intensity 0.6 → 0.8`、(iii) 第 3 鏡 why 文字。
   `vgs diff v3 v4 --json` 列出的變更集合**恰好**是 {鏡 3 transition（舊值、新值）、e5 intensity（舊值、新值）、鏡 3 why}——precision = recall = 1.0；
   **不得**列出因時間重排而「看起來變了」但語意沒變的鏡頭，也不得只輸出檔案行差異。**必要**
3. **diff 附前後縮圖**：只對變更的鏡頭／事件附 before／after 縮圖（S-112 規格），每張以條碼或時間核對對應正確時間 ±1 格；未變更鏡頭不出圖。**必要**
4. **相同版本 diff**：見另卷。
5. **revert 位元相同**：v4 → `vgs revert v3` → 重新算繪：計畫／storyboard JSON 與 v3 **位元組相同**；PNG／GIF 輸出 sha256 與 v3 相同；
   MP4：若文件宣稱 bitexact（`-fflags +bitexact` 等）則位元組相同，否則 `ffmpeg -f framemd5` 逐格相同且音訊 PCM md5 相同。revert 為**非破壞性**（v4 仍在歷史，產生 v5 = v3 內容，或文件化等效）。**必要**
6. **增量重做**：v4 只改第 3 鏡 → 算繪紀錄顯示只重算第 3 鏡（及其相鄰轉場），其他鏡從快取取用（以算繪 log／快取命中數核對；牆鐘 ≤ 全片的 45%）。**必要**
7. **理由持久化**：每個決定（選鏡、轉場、效果、使用者回饋）存 `why`＋來源（agent／user）＋時間；revert 後 v3 的理由仍可讀、v4 的理由不遺失；
   使用者回饋「第三鏡換掉」被記錄並連結到產生的新版本。**必要**
8. `vgs log`：版本列表（版號、時間、一句摘要、父版號、qa 結果）。**加分**

## S-114 素材語意搜尋（選用）—— 加分（理由：spec 標「選用」；但一旦提供，下列 1–4 條即為**必要**，否則不得宣稱支援）
1. **可替換引擎介面**：文件化引擎介面（例 `encode_text(str)->vec`、`encode_image(path)->vec`），測試以 `--engine stub`（或環境變數）注入**假引擎**：
   以字串／檔案 sha256 產生確定性向量。CARDS40 上同查詢跑 3 次（含不同行程）→ 排名與分數**完全相同**；平手以 shot_id 字典序決定（文件寫明）。**必要（若提供）**
2. **排序正確**：假引擎設定成「查詢向量＝卡片 17 的向量＋小擾動」→ 第 1 名為卡片 17；回應每筆含 `shot_id`、`t_in_ms`、`t_out_ms`、`score`、縮圖路徑。**必要（若提供）**
3. **無模型退回文字搜尋**：未安裝 open_clip／無權重 → `vgs find` 回 `mode: "text"`＋警告（非錯誤），對 `description／tags` 做文字搜尋：
   查「海邊」→ 含「海邊」的卡片全部排在不含者之前；整個過程在 NETGUARD 下**零下載嘗試**。**必要（若提供）**
4. **權重授權紀錄**：入庫一份模型清單（例 `references/models.json`）：權重名、來源 URL、授權、可否商用、查證日期、sha256；
   程式只載入清單內且標「可商用」者，載入非清單權重 → ERR `E_UNSUPPORTED`。出題者逐條核對清單授權與來源頁一致（例：CC-BY-NC 的權重不得標可商用）。**必要（若提供）**（理由：spec「權重須可商用；授權逐一核實」）
5. 真實模型下（出題者手動）：在 PROJ5＋10 張自拍素材上，5 個查詢的 top-3 至少 3/5 命中人工標注。**加分**

## S-115 交給專業剪輯軟體（OTIO／FCPXML）—— 必要（理由：spec 驚豔時刻「匯出到 Resolve 還能繼續精修」；專業使用者的出口）
共同：PROJ5 v3 匯出；`opentimelineio` 為**選用相依**（未安裝時 `vgs export --format otio` 回 ERR `E_UNSUPPORTED` 並給安裝指令，或以純 JSON 寫出合法 `.otio`——文件寫明）。驗收時出題者安裝 opentimelineio。
1. **OTIO 自身載入器驗證**：`opentimelineio.adapters.read_from_file(x.otio)` 成功、無警告；`otio.schema.Timeline`，`global_start_time`、rate = 30。**必要**
2. **剪點精確**：OTIO 每個 video clip 的 `range_in_parent()` 起訖（RationalTime，rate 30）換成整數格 = manifest 剪點格號，**誤差 0 格**（不得有浮點漂移，例 89.99999）；
   `source_range` 起點 = storyboard in 點格號。**必要**
3. **軌道齊全**：至少 1 條 video track、1 條 music audio track、1 條 SFX audio track（SFX clip 起點 = manifest 音效時間，0 格誤差）、字幕（OTIO：marker 或文件化的 subtitle track，
   含文字與起訖；FCPXML：`<caption>` 或 `<title>`），以及標記（鏡號／理由 marker）。**必要**
4. **轉場對應**：crossfade → OTIO `Transition`（`transition_type = SMPTE_Dissolve`）且 in/out offset 與計畫時長一致；無原生對應者（例 whip、glitch）→ 以**算好的片段**替代：
   該處為 clip，`media_reference` 指向實際存在的檔案（相對路徑可解析），時長與計畫轉場時長相同 0 格誤差。**必要**
5. **FCPXML**：XML well-formed；根 `<fcpxml version="1.x">`（版本文件寫明）；所有時間為有理數字串（`N/30s` 或 `N/Ds`），不得為小數秒；`<resources>` 的 `<format>`
   frameDuration = `1/30s`；`<asset>` src 為 `file://` URL 且檔案存在。若可取得公開 DTD／XSD（例 OTIO 的 fcpx_xml adapter 或社群公開 DTD），以 `xmllint --dtdvalid` 驗證通過；
   否則出題者以 `opentimelineio` 的 FCPXML adapter（`otio-fcpx-xml-adapter` 等，若可安裝）讀回並比對剪點。**必要**
6. **來回**：OTIO → `vgs import`（或文件化）→ 時間軸／計畫 → 再匯出 OTIO：剪點、clip 順序、轉場類型、音軌事件時間**完全相同**（格號比對）；不支援的欄位列入報告不靜默丟。**必要**
7. **手動開檔**：出題者在 DaVinci Resolve（免費版）匯入 `.otio` 或 `.fcpxml`：剪點與片段順序正確、媒體不離線；Premiere 若可取得同測。**加分**（理由：需要外部 GUI，無法自動化）
8. 匯出含 9:16 時間軸設定（1080×1920）且非方形像素比為 1。**必要**

## S-116 導演評測基準 —— 必要（理由：沒有儀器，導演會「越改越亂」；spec 明列「評測基準沒人跑」為未抵達）
1. **固定題目集**：入庫 8–12 題（題數在範圍內），每題：素材（合成或可再散布、附授權）、一句想法、（可選）參考片、音樂；題目檔有 sha256 清單，runner 啟動時核對，被改動 → 拒跑。**必要**
2. **runner 產出**（以 BENCH-STUB＋假評審驗 runner 邏輯；正式題目集以真實評審驗）：每題、每對版本 **兩個順序**（AB、BA）各一筆盲評紀錄：`task_id`、`order`、`left`/`right` 的匿名代號、勝者、理由；
   評審輸入（提示詞、檔名、metadata）中**不出現**版本名／commit／分支字樣（出題者 grep 評審實際收到的檔案與文字）。**必要**
3. **taste_report 數字**：每個輸出附 S-80 量測 JSON（ASL、CV、對拍誤差、LUFS 等）；taste_report 尚未建成時，runner 記 `taste: not_available` 而非省略或造假。**必要**
4. **一致率**：報告 (a) 順序一致率（同一題 AB 與 BA 判定同一勝者的比例）、(b) 使用者抽查一致率（有使用者標註時；S-87）。
   假評審設成「永遠選左邊」→ 順序一致率 = 0，報告標示評審不可信、該輪結果不得當作勝負依據。**必要**
5. **結果入庫**：每次跑寫 `bench/results/<date>-<commit>.json`（含題目 sha、評審設定、全部紀錄）；可重算報告不需重跑評審。**必要**
6. **退步擋合併**：規則文件化（建議：新版在 ≥ 1 題「兩個順序都輸」且整體勝率 < 50% → 擋）。以假評審：偏好舊版 → `vgs bench gate` 非 0、訊息列出退步題目；
   偏好新版 → 0；並接上 trunk 流程（pre-merge 檢查腳本或 process.md 步驟），出題者以一次模擬合併證實會被擋。**必要**
7. 每次跑的成本（牆鐘、評審次數）入報告；全題目 proxy 跑完 ≤ 30 分鐘（本機，文件化機器）。**加分**
8. 報告附每題 A/B 並排縮圖（S-112）。**加分**
9. 報告用漂亮的 HTML 圖表頁。**無感**（理由：決策靠 gate 結果與數字，不靠排版）

---

## 看完整成品（agent 視角；出題者最後執行，全部**必要**）
目標：一個**全新** agent（不給 repo、不給 SKILL.md、不給 references/、不給本卷），**只**接上本 MCP 伺服器、只看得到 `tools/list`，能在不讀文件的情況下做出 10 秒片。
出題者以 3 個獨立 agent session（至少 2 種不同 agent，例 Claude Code 與 Codex）各跑一次，任務原文：
「用 PROJ5 這 5 段素材和這首歌，做一支 10 秒直式卡點片，做完給我看預覽；然後把第三鏡換掉；最後匯出給 Resolve。」
- [ ] **≥ 2/3 個 session 成功**交出：10 s ±1 格、1080×1920、30 fps CFR、剪點落拍（±1 格）、qa 通過的 mp4。
- [ ] 每個成功 session 的工具呼叫 **≤ 30 次**；schema 錯誤 ≤ 3 次，且每次都在**下一個呼叫**依 ERR 的 suggestion／options 自行修正成功（看呼叫紀錄）。
- [ ] agent 至少一次用 `look` 看了**自己的**預覽（聯絡表或取格），且之後有依所見做出決定（呼叫紀錄可證）。
- [ ] 全會話送進 agent 的圖片總 token（以圖片像素估：每 750×750 ≈ 1 圖塊）不超過「同等資訊用原尺寸 PNG」的 25%。
- [ ] 「第三鏡換掉」→ 新版本只重算第 3 鏡（S-113 第 6 條紀錄），`vgs diff` 只列第 3 鏡（＋相鄰轉場）變更，理由欄記錄使用者回饋。
- [ ] 匯出 OTIO／FCPXML 通過 S-115 第 1–3 條。
- [ ] 全會話 NETGUARD 零外連；付費哨兵 = 0；無任何 traceback 出現在工具結果中。
- [ ] agent 沒有因工具名或描述誤解而呼叫錯工具超過 2 次（例：想取格卻呼叫 render）。
- [ ] 任務中途問 agent「你剛剛改了什麼？」→ 它能用 `diff`／`log` 回答，回答與實際變更一致。
不過的條目寫進 build-notes 作為下一輪工具描述修訂依據；**任一條不過＝S-111 不算交付**（理由：spec 的驚豔時刻就是這個情境；只把腳本原封不動包起來＝未抵達）。

## 不做（照 spec）
雲端服務、帳號系統、GUI 剪輯器、付費模型（評審、嵌入模型皆須本機／免費；付費哨兵 = 0）。
