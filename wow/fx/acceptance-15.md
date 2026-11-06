# 答案卷 第十五輪 — 接上 Suno MCP：音樂路由、遊戲 BGM 無縫循環、音效與 jingle、影片配樂、同主題變奏、歌詞逐字字幕、節拍驅動動畫、用量與來源、示範包（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-15.md（S-170..S-178）；suno-probe/suno-tools.md（2026-11-06 實測 35 個工具的 schema，只讀、未花點數）；references/music.md（`music_sync.py`、`music_fit.py`、Beat This! 選用引擎、−14 ±1 LUFS／≤ −1 dBTP 影片交付閘門）；`scripts/sfx.py`（現行 Kenney CC0／NumPy 後備音效）；acceptance-14（Godot 4 可攜版、`sprite_export.py`、`anim.json` 的 `events`）；
process.md（兩軸閘門：技術軸定去留、好聽／好看軸由使用者 U 類、不定生死；trunk-based、experimental 旗標）；wow/fx/thresholds.md（門檻動態類 **F** 固定／**R** 棘輪／**C** 錨點校準／**U** 使用者品味）；沿用 acceptance-13／-14 全部共通規則（ERR 信封、NETGUARD、manifest ledger、`engine_load` 誠實、`--experimental`）。出題者 2026-11-06 寫定。

出題者查得現況（HEAD 0935b2d）：已有 `music_sync.py`（RMS 拍點；`--engine beat_this` 才有 downbeat）、`beat_layers.py`、`music_fit.py`（候選裁切＋零交越＋40 ms crossfade）、`sfx.py`（6 類程式化音效）、`sprite_export.py --engine godot4…`。**沒有**任何 Suno／MCP 用戶端、沒有循環檢查器、沒有音訊引擎匯出。
本機引擎：Godot 4 可攜版 `C:\Users\User\src\vgs-fx-private\tools\godot4\Godot_v4.7.2-stable_win64_console.exe`（出題者持有、記 sha256；建造者可自備同版）。Unity、FMOD Studio、Wwise **都沒有** → 只能做格式層檢查，報告必須寫 `engine_load: "untested"`。

**從 schema 查得的能力事實（建造者不得宣稱超出這些）**：
- `sounds_create`：有 `tempo`（BPM）、24 值 `key`、`loop`；**一次產 2 個 clip、各扣 1 歌曲點**；**長度由模型決定，無 duration**；**沒有拍號參數**。
- `audio_create`：有 `duration`／`duration_strict`／`instrumental`／`style`／`negative_style`／controls；**沒有 BPM、沒有調性、沒有 loop 參數**。歌曲的 BPM／調性只能事後 `audio_analysis` 量，不能指定。
- `audio_covers_create`／`audio_mashups_create`：**沒有 tempo／key 參數**，變奏的 BPM 不保證相同。
- `audio_download`：mp3（預設）／wav；先不帶 `confirm` 呼叫，回 `requires_credit` 才需扣點，`confirm: true` 依工具文件「須經使用者同意」；拒絕碼 `quota_exhausted`(402)、`rate_limited`(429)、`daily_limit_exceeded`(429) 等。
- `audio_listen`：免費但每日 200 題、同時 5 題；`audio_analysis`／`audio_lyrics_alignment`：免費、非同步（`processing` → `complete|unavailable`）、`key` 可為 null。
- 建立類工具都有 `idempotency_key`（≥ 24 h、同 key 同參數回原資源、不同參數回 409）。
- `playlists_create` 有 `visibility: public|private`（預設 private）。
- 帳號：歌曲點 8,510、**下載點 67**。

每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條），附理由。每個門檻後標類別 `[F]`／`[R]`／`[C]`／`[U]`。
CLI／欄位名以建造者文件為準；本卷用 spec 用語（`music_route=suno`、`suno_route.py`、`audio_loop.py check|export`、`sfx.py jingle`、`gen-manifest.json`、`suno-ledger.json`），改名須在 references/ 寫明對應。若 `vgs` 存在，以 `vgs audio …` 子命令提供（JSON 進出、ERR 信封）。

---

## 共通規則（第一～十四輪全部沿用，另加）

- **下載點數閘門（最高優先，任何一條違反＝整卷不過）**：
  - 預覽一律走 `audio_listen`／`audio_analysis`／串流 `song_url`（`audio_wait until=playable`），**不呼叫** `audio_download`。
  - `audio_download` 只對「使用者選定」的 clip 呼叫：ledger 必須先有 `selection: {clip_id, selected_by: "user"|"standing:<授權 id>", at}`；先**不帶** `confirm` 呼叫；只有回 `requires_credit` 且通過下列守衛才可帶 `confirm: true`。
  - **守衛（必須寫在程式裡，不能只寫在提示詞／SKILL.md）**：(a) 本輪已扣點下載數 < `per_round_cap`（預設 5）；(b) 呼叫前**即時**以 `account_usage` 讀下載點，**≤ 9 拒絕**（spec「低於 10 停止」；10 允許，下載後成 9 即停）；(c) 同一 clip 同一格式已下載過 → 走本機快取，0 次呼叫；(d) `wav` 優先，要 mp3 須有理由。拒絕回 `E_DOWNLOAD_BUDGET`（含剩餘點數、本輪已用、建議）並停止整個下載佇列，不得改用其他途徑繞過。
  - 若架構是「代理直接呼叫 MCP 工具」（Python 叫不到 MCP），守衛必須以**執行期攔截**落地：Claude Code `PreToolUse` hook 比對 `mcp__suno__audio_download` 的 `confirm:true` 與 ledger 授權；Codex 端無等價 hook 時，README 必須寫明 `download_guard: "instruction_only"` 且該路徑**預設不得下載**（只產出待下載清單）。出題者以 FAKE-SUNO 實測攔截。
  - **串流不得冒充下載**：串流音訊只能存在暫存分析目錄（`.cache/suno-preview/`，標 `preview_only: true`），不得進任何交付目錄、引擎匯出、示範包；交付檔的 `source` 必須是 `audio_download`（含其 URL 回應紀錄）或使用者上傳。出題者掃描交付目錄的每個音檔 sha，必須能對到一筆 download 紀錄。
- **生成額度**：本卷 live 上限：**建立類呼叫 ≤ 40 次**（`sounds_create`／`audio_create`／`covers`／`mashups`／`extensions`／`speech` 每次呼叫算 1，不論回幾個 clip）、**歌曲點花費 ≤ 500**（以 `account_usage` 前後差量）、**扣點下載 ≤ 5 次（全卷含 holdout 與 S-178 示範合計）**。超過任一 → 先問使用者。holdout 的下載題全部用 FAKE-SUNO，不花下載點。
- **兩層驗收**：
  - **離線層（決定性、CI 可跑）**：**FAKE-SUNO**（本機 MCP 伺服器或可替換的 transport，提供 35 個工具同名同 schema；腳本化回應：`requires_credit`、`processing`、`quota_exhausted`、`rate_limited`、`daily_limit_exceeded`、HTTP 500、409 idempotency 衝突、`Idempotency-Replayed`、可設定的下載點餘額序列；計數每工具呼叫數與 `confirm:true` 次數）。**SUNO-SENTINEL**：離線測試期間任何到 `suno.com`／`api.suno.com`／`*.suno.ai` 的連線（含子孫行程，沿用 NETGUARD）計數必須 = 0。
  - **live 層**：只在標「live」的條目、S-178 示範與「聽完整成品」跑；每次 live 存證（MCP 請求參數、回應、clip id、`account_usage` 前後）。
- **私人作品不外洩**：使用者 library 內容（歌名、歌詞、風格標籤、clip id、封面 URL、handle）**不得**出現在 repo 任何提交檔、測試夾具、交付包、README、公開 playlist、log 中會被分享的部分。只有使用者明示要重用自己的某首作品時才可 `library_search`／`reference_audio_ids`，且只記那一首的 clip id 於**私有** manifest（`private: true`，不入庫）。夾具 **LIB-PRIVATE** 帶 canary 字串（例：`CANARY-盤-7f3a`），出題者 grep 全 repo 與全部輸出：0 次命中。
- **對外動作先問**：`playlists_create visibility:"public"`、把 clip 加入公開 playlist、`audio_like`、任何改動使用者既有作品的 `audio_edit`／`workspaces_update_clips` → 先問。private playlist／workspace 可直接建（記 ledger）。
- **兩軸閘門**：技術軸（循環接縫、爆音、響度、對拍、時長、調性／BPM 一致）由本機量測決定 keep／fix／delete；「好不好聽」是 U 類，只決定預設與推薦，**永不決定刪除**。AI 評審（`audio_listen` 回答、wow-judge）只當參考排序。
- **能力誠實**：schema 沒有的參數（歌曲 BPM／調性、sounds 長度、拍號、stems 格式）不得寫成「已指定」；manifest 分開記 `requested` 與 `measured`；量不到寫 `null`＋原因，不猜。
- **單位**：響度以 ITU-R BS.1770-4／EBU R128（ffmpeg `ebur128` 或 pyloudnorm，兩者在 LOOP-OK 上差 ≤ 0.2 LU 才可互換）；true peak dBTP（4× 過取樣）；時間以樣本為準（48 kHz 交付；Suno 原生取樣率照實記錄，重取樣用 soxr 或 ffmpeg `aresample=resampler=soxr`）。
- **trunk-based**：每個 S 一個切片；全套測試＋doctor 綠就以 `experimental` 合回 main；本卷通過前 `music_route=suno` 需 `--experimental`。

## 合成素材與夾具（全部由測試程式以 numpy／ffmpeg 產生，或為 FAKE-SUNO 錄製匣；不入庫任何 Suno 生成音訊或使用者作品）

| 代號 | 內容 | 已知答案／用途 |
|---|---|---|
| **LOOP-OK** | 48 kHz 立體聲、120 BPM 4/4、4 小節 = 8.000 s = **384000 樣本**；kick 在每拍、hat 每 8 分、pad 由頻率為 k/L 整數倍的正弦組成（數學上週期 = L），樣本級週期：x[L] 接 x[0] 與內部任意點同樣連續；整合響度 −16.0 LUFS | 循環正對照 |
| **LOOP-CUT** | LOOP-OK 的 8 小節非週期版（和弦進行 Am–F–C–G 各 2 小節）截在 3.6 小節（345600 樣本） | 非整數小節、拍相位跳 0.4 小節：必 FAIL |
| **LOOP-CUTBAR** | 同上 8 小節版截在**剛好第 4 小節**（384000 樣本）：拍格對得上，但和聲 C→Am 硬接、pad 相位不連續 | 「對齊小節但不是循環」：必 FAIL（不能只看拍格） |
| **LOOP-CLICK-SEAM** | LOOP-OK，最後 1 樣本 +0.25 FS 階躍 | 接縫爆音：必 FAIL |
| **LOOP-CLICK-MID** | LOOP-OK，第 2.37 小節處 1 樣本 0.5 FS 脈衝 | 內部爆音：必 FAIL，回報時間 ±1 ms |
| **LOOP-FADE** | LOOP-OK，尾 250 ms 淡出＋頭 50 ms 淡入 | 假循環（接縫掉音量）：必 FAIL |
| **LOOP-DRIFT** | LOOP-OK 加 +4 dB 線性增益斜坡 | 首尾響度不一致：必 FAIL |
| **LOOP-MP3** | LOOP-OK 經 LAME 編碼再以不處理 encoder delay 的方式解碼 | 前置靜音 ~1105 樣本：必 FAIL（mp3 不得當循環交付格式） |
| **LOOP-OGG** | LOOP-OK 經 libvorbis q6 編碼 | 解碼後樣本數 = 384000、接縫過：PASS |
| **LOOP-78** | 7/8，♪ = 240（♩ = 120），一小節 7 個八分 = 1.75 s，4 小節 = 7.0 s = 336000 樣本，重音 2+2+3 | 奇數拍號正對照；切在 4/4 小節線（8.0 s 的倍數）版必 FAIL |
| **VAR-SET** | 4 段 8 小節 120 BPM Am 變奏（探索／戰鬥／Boss／勝利），共用 4 音動機 A–C–E–D，downbeat 對齊 | 變奏正對照 |
| **VAR-BAD** | VAR-SET 中：一段 123 BPM、一段 downbeat 延後 37 ms、一段 B♭m | 三個各自必須被指出 |
| **JINGLE-SHEET** | 一個音檔內 5 個 one-shot，間隔 ≥ 400 ms 的 −60 dBFS 底噪；其中 1 個有 600 ms 殘響尾（−50 dB 才到底） | 音訊 sprite 切片；不得切斷殘響 |
| **SFX-RAW** | 300 ms 前置靜音、DC 偏移 0.02、峰值 −0.1 dBFS（4× 過取樣 true peak +0.8 dBTP） | 裁切／去 DC／正規化 |
| **BEAT-MAP** | Suno `audio_analysis` 格式的假回應：LOOP-OK 的 beats（含 `bar_position`）、`bpm`、`time_signature`、`key`、sections；另一份 120→124 BPM 漸快版 | 對拍題 |
| **LYR-ALIGN** | 假 `audio_lyrics_alignment`：40 字、其中 3 字 `success:false`；另一份 instrumental（`words: []`） | 字幕題 |
| **LIB-PRIVATE** | FAKE-SUNO `library_list`／`library_search` 回 12 首帶 canary 字串的假作品 | 隱私題 |
| **FAKE-SUNO** | 見共通規則 | 離線層 |

**循環量測器定義（S-171、S-174、S-178 共用；建造者實作，出題者另有獨立實作交叉比對，兩者對全部 LOOP-* 判定必須一致）**：
1. **長度**：L 必須是整數小節：|L − n·bar| ≤ 2 樣本 `[F]`（bar 由 BPM、拍號定義；BPM 量測值與宣告值差 > 0.5 BPM → 先報 BPM 不符 `[C]`）。
2. **拍相位**：把 x 接 x（x⧺x）算 onset envelope，接縫前後各 2 小節的拍格對 BEAT-MAP 或本機 beat 估計，相位誤差 ≤ 5 ms `[C]`。
3. **爆音／不連續**：x⧺x 經 4 kHz 二階高通，取 2 ms 滑窗能量；任一窗（**含接縫窗與內部**）對全段中位數比 ≤ +18 dB `[C]`；且接縫一階差 |x[L−1] − x[0]| ≤ 內部一階差 99.9 百分位 `[C]`。
4. **頻譜連續（尾→首交叉相關）**：接縫兩側各 46 ms（2048 點）的 chroma＋log-mel 向量，對「內部每個小節線兩側同長度片段」的距離分布：接縫距離 ≤ 內部 95 百分位 `[C]`；尾 1 小節對頭前 1 小節的 x⧺x 正規化互相關峰值落在 lag 0 ±1 ms `[C]`。
5. **響度一致**：首、尾各 3 s short-term LUFS 差 ≤ 1.0 LU `[C]`；接縫 ±400 ms momentary 響度不低於全段 momentary 中位數 −3 LU `[C]`；交付整合響度 = 目標 ±1 LU（BGM 預設 −16 LUFS，可設；手機／主機平台目標若引用 ASWG 等標準須附出處 `[F]`）、true peak ≤ −1 dBTP `[F]`。
6. **編碼後重驗**：每個交付格式（WAV、OGG）**解碼後**重跑 1–5；解碼樣本數 = 來源樣本數（OGG 誤差 0）`[F]`。
校準：`[C]` 數值以 LOOP-* 正負對照＋≥ 10 個 live Suno loop（出題者事後人工標「聽得出接點／聽不出」）校準，兩側各留 ≥ 合併 σ 的 25% 餘裕；分不開就標「儀器分不開」，不准上線（thresholds.md §5）。

---

## S-170 音樂路由（`music_route=suno`、`suno_route.py`）—— 必要（理由：其餘每個 S 都經過它；下載點數是唯一稀缺且不可逆的資源）

**命令形狀**：
```
suno_route.py plan   --request req.json --json            # 只規劃：會呼叫哪些工具、預估歌曲點、預估下載數
suno_route.py create --request req.json [--experimental] --out <dir> --json
suno_route.py select --clip <id> --by user|standing:<id>   # 記錄使用者選定
suno_route.py download --clip <id> [--format wav|mp3] --json
suno_route.py usage [--round <id>] --json
```
1. **記帳**：每次 MCP 呼叫寫 `suno-ledger.json`：`tool`、正規化參數、`idempotency_key`、回傳 `clip_ids`、`status`、時間、`account_usage` 前後的 `credits_remaining`／`download_credits_remaining`（下載前後必讀；建立前後每輪至少讀一次）、扣點差量。ledger 可重放出本輪總花費，與 `account_usage` 差量一致（誤差 0）`[F]`。**必要**
2. **下載守衛（離線、FAKE-SUNO，不花點）**：
   - 同一輪第 6 次扣點下載 → `E_DOWNLOAD_BUDGET`，FAKE-SUNO 收到的 `confirm:true` 次數 = 5（**不是** 6）`[F]`；
   - 餘額序列 `[67, 12, 10, 9]`：第 3 次（餘 10）允許、第 4 次（餘 9）拒絕；`confirm:true` 總數 = 3 `[F]`；
   - 沒有 `selection` 紀錄的 clip → 拒絕，`confirm:true` = 0；
   - 不帶 confirm 的第一次呼叫回 URL（免扣點）→ 不再帶 confirm 呼叫第二次、不計入扣點下載數；
   - `quota_exhausted` → 停整個佇列、不重試；`daily_limit_exceeded` → 停；`rate_limited` → 退避 ≥ 1 s 重試 ≤ 2 次；`processing` → 依文件重呼叫 `audio_download`（**不得**呼叫 `audio_wait`），間隔 ≥ 1 s；
   - 執行期攔截（若為代理直呼架構）：模擬代理直接送 `mcp__suno__audio_download {confirm:true}` 給未授權 clip → hook 擋下、FAKE-SUNO 計數 0。**必要**
3. **快取**：`cache_key = sha256(tool, 正規化參數（鍵排序、數值正規化 120 = 120.0、字串 NFKC＋去首尾空白）, model)`；同請求重跑 → 建立類呼叫 0 次、輸出 sha 相同 `[F]`；使用者說「再來一版」→ 明確 bypass 並記 `cache: "bypass:user"`。建立呼叫一律帶 `idempotency_key`（由 cache_key＋嘗試序號衍生）；暫時性錯誤重試用**同一** key，FAKE-SUNO 回 `Idempotency-Replayed: true` 時不重複記帳 `[F]`。**必要**
4. **非同步輪詢**：建立後用 `audio_wait`（`ids` ≤ 4 一批）、`audio_analysis`／`audio_lyrics_alignment` 輪詢至離開 `processing`；`unavailable` 停止輪詢並在 manifest 記 `null`＋原因；`audio_listen` 同時 ≤ 5 題、每日計數 ≤ 200（超過排隊或改用本機分析）。**必要**
5. **路由誠實**：`suno_route.py plan` 對每個請求標出走哪個工具與為什麼（例：要求「BPM 128、D 小調、可循環」→ 只有 `sounds_create` 能指定 → 選它；要求「90 秒有歌詞主題曲」→ `audio_create`，BPM／調性 `requested: null`、事後量）。要求歌曲指定 BPM／調性時，回報「schema 無此參數，改為：生成後量測＋必要時本機時間伸縮（≤ ±4%）或改用 sounds」。**必要**
6. Suno 無法連線／未登入（Claude Code 尚待 `/mcp` 登入）→ `E_ROUTE_UNAVAILABLE`＋「本機替代」（`sfx.py` 程式化音效、使用者自備音訊＋`music_fit`），不得靜默改用其他付費服務。**必要**
7. 路由 dry-run 報告（`plan` 的人類可讀版：要花多少歌曲點、要下載哪幾個、剩餘下載點）。**加分**（理由：使用者在乎下載點，一眼看到很安心）
8. ledger 的 CSV 匯出。**無感**

## S-171 遊戲 BGM 無縫循環（`audio_loop.py check|export`）—— 必要（理由：驚豔時刻核心；接縫一響就不能 ship）

**命令形狀**：
```
suno_route.py create --kind bgm-loop --mood "雪山探索" --bpm 110 --key Dm [--meter 4/4] --out bgm/
audio_loop.py check bgm/explore.wav --bpm 110 --meter 4/4 --json
audio_loop.py export bgm/explore.wav --engine godot4,unity,fmod,wwise --formats wav,ogg --out export/audio/
```
1. **生成**：`sounds_create {loop:true, tempo, key}`；manifest 記 `requested` 與 `measured`（本機量 BPM、`audio_analysis` 的 bpm／key／time_signature）。量測 BPM 與要求差 > 0.5 或調性不同 → 標 `spec_mismatch`，不得當作符合交付（可重生 ≤ 1 次或回報）。**必要**
2. **循環量測器**（上方定義 1–6）：LOOP-OK、LOOP-OGG、LOOP-78 PASS；LOOP-CUT、LOOP-CUTBAR、LOOP-CLICK-SEAM、LOOP-CLICK-MID、LOOP-FADE、LOOP-DRIFT、LOOP-MP3 **全部 FAIL** 且報告指出哪一項、時間位置（±1 ms）。正對照不過＝儀器壞，不判作品。**必要**
3. **live Suno loop 的處置**：每個 live loop 跑量測器並記錄；不過時：(a) 本機修補——只能在**小節線**做等功率 crossfade（≤ 1 拍）或重新裁到整數小節，修補後重驗 1–6 全過、修補方法與樣本位置記 manifest；(b) 修不好 → 重生 ≤ 1 次；(c) 仍不過 → 不得標 `seamless: true`，回報。**不得**用淡出淡入假裝循環（LOOP-FADE 那種）。**必要**
4. **交付格式**：WAV（PCM 16/24-bit、48 kHz）＋OGG Vorbis；**mp3 不得作為循環交付**（encoder delay）`[F]`；每檔附 loop 點：`loop_start`／`loop_end`（樣本，end 為「不含」的總樣本數，並在 README 寫清楚各格式的含／不含慣例）、`bpm`、`beats_per_bar`、`bar_count`。**必要**
5. **Godot 4 匯出＋真引擎載入**：
   - OGG：`.import` 的 `[params]` 含 `loop=true`、`loop_offset`（秒）、`bpm`、`beat_count`、`bar_beats`；WAV：`edit/loop_mode`（forward）、`edit/loop_begin`、`edit/loop_end`（樣本）——**鍵名以 4.7.2 實際匯入結果為準**（出題者會先用 Godot 自己匯入一份當參考）。
   - **載入檢查**：`Godot_v4.7.2-stable_win64_console.exe --headless --path <proj> --import` 後 `--headless --script check_audio.gd`：載入每個 stream、斷言 `loop`、`loop_offset`、`bpm`、`bar_beats`、`get_length()` 與來源差 ≤ 1 ms、WAV `loop_end` = 總樣本數；AudioStreamPlayer 播 2 個循環不報錯。Godot 輸出 0 個 ERROR／WARNING（與音訊相關者）。`engine_load: "tested:4.7.2"`。**必要**
6. **Unity／FMOD／Wwise 風格**：WAV 內嵌 RIFF `smpl` chunk（`dwStart`／`dwEnd` 樣本、**`dwEnd` 為含端點 = L−1**——陷阱，出題者以反向讀取器驗 off-by-one）＋`cue `／`LIST adtl` 小節標記；sidecar `<name>.loop.json`（`loop_start_samples`、`loop_end_samples`、`bpm`、`meter`、`bar_markers_ms[]`、`sample_rate`）；Unity `.meta`（`AudioImporter`，`loadType: Streaming` for BGM、`preloadAudioData`）為加分。三者 `engine_load: "untested"`。**必要**（smpl＋sidecar）／**加分**（Unity .meta）
7. OGG Vorbis comment `LOOPSTART`／`LOOPLENGTH`（RPG Maker 等慣例）。**加分**
8. 循環預覽頁：波形＋接縫放大＋「連播 3 次」音檔。**加分**（理由：使用者唯一會用的檢查方式是聽接縫）
9. 匯出檔命名、資料夾結構。**無感**

## S-172 遊戲音效與 jingle（`sfx.py jingle` / `suno_route.py create --kind sfx`）—— 必要（理由：spec 驚豔時刻「升級與勝利 jingle」；UI 音一大一小就不能用）

1. **生成**：`sounds_create`（one-shot，`loop:false`）；jingle 帶主題的 `key`（主題曲調性由 `audio_analysis` 量得；`null` 時以本機 chroma 估計並標 `key_source: "local_estimate"`）與 `tempo`。每個產出 `measured_key`；與要求不同 → 標 `spec_mismatch`。**必要**
2. **調性一致** `[F]`（音樂理論）：jingle 與主題同調、或為關係調／屬調／下屬調／同主音大小調（manifest 寫關係名）；其他關係必須是使用者明示要求並記 `key_conflict: "user_requested"`。**必要**
3. **後處理**（SFX-RAW 驗）：前後靜音裁切至首個 > −50 dBFS 樣本前 ≤ 5 ms `[C]`；DC 偏移 ≤ 0.001 `[F]`；結尾淡出 5–30 ms 且淡出後最後 10 ms ≤ −60 dBFS `[C]`；**不得切斷殘響尾**（JINGLE-SHEET 殘響那個：裁切後保留到尾音 −50 dB 以下）；true peak ≤ −1 dBTP `[F]`。**必要**
4. **響度一致（同一組）** `[C]`：UI 類（click／hover／confirm）short-term 最大響度彼此差 ≤ 2 LU；jingle 類彼此差 ≤ 2 LU；jingle 相對 BGM 整合響度 +2～+6 LU（壓得過 BGM 但不刺耳；可設）。**必要**
5. **音訊 sprite（省下載點）**：允許把多個 one-shot 以一次 `sounds_create`（描述「依序 5 段、以靜音分隔」）或本機合併成一個 clip → 一次下載 → 本機以靜音偵測切片，輸出各檔＋`audio-sprite.json`（`{name: {start_ms, end_ms}}`，Howler.js 相容）。JINGLE-SHEET：5 段全部切出、起點誤差 ≤ 5 ms、殘響不截斷、切出段數 ≠ 5 時報錯不靜默。**必要**（理由：下載點只有 67，這是 S-178 能塞進 ≤ 5 次下載的唯一合理方式）
6. **與 spec-14 VFX 對時**：讀 `anim.json` 的 `events`（例 `hit` 第 k 格），音效的感知起點（onset，非檔頭）落在事件格起始時間 ±1 個顯示格（60 fps = 16.7 ms）`[F]`；有預備音（whoosh 先於 hit）時，以 manifest `sync_point_ms` 宣告對齊點。Godot 匯出 `AnimationPlayer` audio track 或 `AnimationLibrary` method track 呼叫播放，頭端靜音已扣除。**必要**
7. `sfx.py` 現有 6 類程式化音效保留為離線後備（`music_route` 不可用時），既有測試零退步。**必要**
8. 變化版（同一拾取音 3 個微變體，防聽膩）。**加分**
9. 音效分類資料夾名稱。**無感**

## S-173 影片配樂（`suno_route.py create --kind score --brief brief.json`）—— 必要（理由：spec 列出；原本影片管線就要配樂，這是第一個能生成的來源）

1. 依 brief／分鏡的總長與段落產生 `audio_create {instrumental:true, duration, duration_strict:true}`；量得長度與要求差記錄（Suno 精度未知 → 記 `measured_duration_ms`，不得假設準）。**必要**
2. **對到片長**：最終配樂長度 = 片長 ±1 個影片格 `[F]`；不足 → `audio_extensions_create`（`continue_at` 選在小節線，記錄）＋`audio_full_song`；過長 → 既有 `music_fit.py` 在小節線裁切、40 ms crossfade、零交越；接點處跑循環量測器的 3（爆音）與 5（響度 ±400 ms 不掉 > 3 LU）。**必要**
3. **drop／段落對位**：brief 標的 drop 時間與 `audio_analysis` 的 section 起點（或本機 Beat This! downbeat）配對，最終成片中 |drop 誤差| ≤ 1 拍且 ≤ 250 ms `[C]`；做不到 → 報告列出差值並提出 2 個候選（不同裁切點），不靜默交付。**必要**
4. **節拍來源交叉驗證**：Suno `audio_analysis` 的 beats 對本機 `music_sync.py --engine beat_this`（串流預覽或下載檔）的 downbeat：中位 |Δ| ≤ 20 ms、BPM 差 ≤ 1%（倍速／半速要辨識並註明）`[C]`；不一致時以本機為準並記錄。**必要**
5. 交付影片音軌照 references/music.md：−14 ±1 LUFS、≤ −1 dBTP（ebur128 獨立量）`[F]`。**必要**
6. 同 brief 出 2–3 個風格候選（只串流預覽，不下載）讓使用者挑。**加分**
7. 配樂段落色彩標示的時間軸圖。**無感**

## S-174 同主題變奏（`suno_route.py create --kind variants --theme <clip>`）—— 必要（理由：spec 驚豔時刻「同主題的探索／戰鬥兩段」；切換時跳拍會毀掉整個遊戲手感）

1. **同 BPM**：所有變奏本機量測 BPM 差 ≤ 0.5 `[F]`（遊戲切換是小節級硬接，差 0.5 BPM 在 8 小節累積 ≈ 33 ms 仍需靠切換點重對齊）；Suno covers／mashups 無 tempo 參數 → 若量測不符，允許本機時間伸縮（rubberband／soxr，比例 ≤ ±4%，記錄）或改用 `sounds_create` 指定 tempo 重做；超過 ±4% 不得硬拉。**必要**
2. **同調性**：所有變奏同調，或為宣告的關係調（Boss 版轉同主音小調可，manifest 記錄）`[F]`。VAR-BAD 的 B♭m 被指出。**必要**
3. **小節對齊切換點**：每個變奏輸出 `switch_points_ms[]`（每個小節線或每 2／4 小節，宣告），第 1 個 downbeat 在所有變奏同一樣本位置（差 ≤ 2 ms）`[C]`；VAR-BAD 的 37 ms 偏移被指出。**必要**
4. **切換實測**：對每對變奏（A→B、B→A）在每個宣告切換點做硬接與 1 拍等功率 crossfade 兩種拼接，全部跑循環量測器 2（拍相位 ≤ 5 ms）、3（爆音）、5（momentary 不掉 > 3 LU）；VAR-SET 全過、VAR-BAD 對應的對失敗。**必要**
5. **共用動機**（技術軸可量部分）：每個變奏的 chroma 序列與主題的動機片段做時間伸縮不變的互相關（DTW 或 2D chroma xcorr），最佳匹配分數 ≥ 主題與**不相關**曲（負對照：VAR-SET 以外的一段隨機和弦進行）分數 + 合併 σ 的 25% `[C]`；做不到 → 標「動機未量得」，不得宣稱共用。**加分**（理由：Suno 不保證保留旋律，這條能量但不能保證做到）
6. Godot 4 `AudioStreamInteractive`（4.3+）匯出：clip 列表＋transition 用 `TRANSITION_FROM_TIME_NEXT_BAR`（或等價），headless 載入並斷言 clip 數與 transition 表。**加分**
7. FMOD 風格 sidecar：`transition_markers`、`destination_markers`（小節編號、ms、樣本）。**加分**
8. 8-bit 版。**加分**（理由：好聽與否是 U 類；技術上同 1–4）
9. 變奏命名用中文或英文。**無感**

## S-175 歌詞逐字對齊 → 字幕（`audio_lyrics_alignment` → P1 字幕）—— 加分整體，條目內標（理由：遊戲 BGM 多為純音樂；對主題曲 MV 有用）

1. 取對齊（輪詢至 `complete|unavailable`）；`words` 原樣轉成 P1 逐字字幕時間（ms 取整，誤差 0）`[F]`；`success:false` 的字標記為「推論時間」並在報告列出；LYR-ALIGN 的 3 字被列出。instrumental `words: []` → 正常回「無歌詞」，不報錯。`unavailable` → 回報並提議本機 whisper 退路（不自動跑付費服務）。**必要**（做了就要對）
2. live 抽 20 字以本機 whisper 字級時間交叉驗：中位 |Δ| ≤ 150 ms `[C]`；超過列出。**必要**（做了就要對）
3. 卡拉 OK 式逐字上色預覽。**加分**
4. 歌詞全文不出現在任何提交檔（若是使用者 library 作品，依私人規則）。**必要**

## S-176 節拍驅動動畫（`imagegen.py animate --beat-sync <analysis>` 或 `sprite_export.py --beat-sync`）—— 必要（理由：驚豔時刻「角色 sprite 跟著 BGM 的拍子呼吸、攻擊落在重拍」）

1. **對拍時間表**：輸入 `audio_analysis` beats（`bar_position`）或本機 downbeat；輸出 `beat-sync.json`：每個循環動畫的週期 = 整數拍（idle 1 或 2 拍、walk 每步 1 拍，宣告），逐格 `duration_ms` 調整使週期精確 = 拍長×n（累積誤差 0 ms，以整數 ms＋餘數分配，不得每格四捨五入後累積漂移）`[F]`。**必要**
2. **命中落在重拍** `[F]`：attack 的 `hit` 事件（S-161.6 的接觸格）起始時間 vs 目標 downbeat：在 metadata 時間軸上 |offset| ≤ 1 ms；Godot 播放執行期（以 `AudioStreamPlayer.get_playback_position() + AudioServer.get_time_since_last_mix() − AudioServer.get_output_latency()` 為時鐘）≤ 1 個顯示格（16.7 ms @60 fps）。headless dummy 音訊驅動若播放位置不前進 → 執行期一項記 `runtime_av_sync: "untested"`，不得寫 tested。**必要**
3. **長時間不漂**：以 BEAT-MAP 的 32 小節模擬播放，第 32 小節的命中誤差 ≤ 5 ms `[F]`（動畫由音訊時鐘驅動，不是自己的 fps 計時器）；負對照：固定 12 fps 四捨五入的天真版本被量測器報出漂移（> 30 ms）。漸快版 BEAT-MAP（120→124）：仍逐拍對齊（每個 downbeat 誤差 ≤ 5 ms），證明不是只用單一 BPM。**必要**
4. **倍速／半速防呆**：只用 `bar_position == 1` 的 downbeat 當重拍；Beat This! 回倍速時（BPM 估 2×），命中仍落在真 downbeat（夾具：BEAT-MAP 以 240 BPM 標的錯誤版本 + 正確 bar_position，必須選對）。**必要**
5. **不破壞動作品質**：調整逐格時長後，acceptance-14 S-161.3／4／7（腳不滑、重心、循環接縫）重驗全過；攻擊預備段時長仍 ≥ 接觸後 40%（S-161.9）。若要把攻擊塞進 1 拍導致預備太短 → 改用 2 拍並記錄，不得硬壓。**必要**
6. VFX（spec-14 S-166）發光脈衝亮度隨拍：alpha 總和的峰值時間對 beat ≤ 1 個顯示格。**加分**
7. 對拍預覽影片（sprite＋BGM＋節拍器 click 軌可開關）。**加分**（理由：使用者用聽的檢查）

## S-177 用量與來源紀錄（`gen-manifest.json` 的 `suno` 區塊）—— 必要（理由：授權與點數都要能追溯）

1. 每個交付音檔：`clip_id`、`tool`、`model`（回應中有才寫，不猜）、`params_requested`、`measured`（bpm、key、meter、duration_ms、lufs、true_peak）、`idempotency_key`、`credits_spent`、`download: {format, at, credit_spent: bool}`、`license: "user_account_generated (Suno Premier)"`、`sha256`、`source: download|upload`。出題者對每個交付檔 sha 反查：100% 有紀錄 `[F]`。**必要**
2. **私人作品**：LIB-PRIVATE canary 在 repo、交付包、README、公開 log、playlist 名稱 0 命中 `[F]`；manifest 若引用使用者作品，只在 `private-manifest.json`（.gitignore 已列）。**必要**
3. `suno_route.py usage` 回報：本輪建立呼叫數、歌曲點花費、扣點下載數、剩餘下載點、距 10 點停止線還有幾次。**必要**
4. 授權說明一段（Suno 帳號產出、Premier 方案期間的使用權依 Suno 條款；附條款連結與查閱日期，不作法律保證）。**加分**

## S-178 示範與驗收（`suno_route.py demo game --scene snow-mountain`）—— 必要（理由：spec 的交付證明）

**示範包內容**（`demo/snow-fox-audio/`，接 acceptance-14 的 `demo/ice-fox/`）：
- `audio/theme/`：主題曲（可只有串流預覽＋量測報告；**是否下載由預算決定**）；
- `audio/bgm/`：探索、戰鬥兩段無縫循環（WAV＋OGG＋loop metadata），同 BPM 同調；
- `audio/sfx/`：5 個 jingle／UI 音（升級、勝利、失敗、拾取、UI 確認）＋`audio-sprite.json`；
- `godot-project/`：場景中角色 idle 隨 BGM 拍子、attack 命中落在重拍、探索↔戰鬥在小節線切換、jingle 由事件觸發；
- `README.md`：怎麼開、每個檔案、`engine_load` 狀態、哪些量測 untested、建立呼叫數、歌曲點、下載數、剩餘下載點；`gen-manifest.json`、`suno-ledger.json`。
1. **下載預算**：示範扣點下載 ≤ 4（建議：2 段 loop＋1 個 jingle sprite＋1 備用），全卷合計 ≤ 5 `[F]`；示範後下載點 ≥ 62 且從未在 ≤ 9 時下載。**必要**
2. 上列全部存在且 S-171..S-177 各條必要門檻 0 項 FAIL（出題者用同一驗收腳本跑示範包）。**必要**
3. Godot 4.7.2 headless：匯入 0 錯誤、載入所有音訊與 SpriteFrames、跑 30 s 場景（含一次小節線切換、一次 jingle、兩次 attack）0 ERROR，並輸出事件時間 log 供 S-176.2 判定。**必要**
4. 重跑決定性：快取命中時重跑 0 次建立呼叫、0 次下載、輸出 sha 相同。**必要**
5. 從乾淨狀態牆鐘 ≤ 30 分鐘（含 Suno 排隊）。**加分**
6. 兩軸：技術軸＝量測器全部報告＋獨立評審聽「接縫連播 3 次」「對拍片」挑瑕疵（對刻意破壞版：LOOP-CLICK-SEAM 注入版、命中延後 80 ms 版必須贏）；好聽軸＝使用者抽查（U），只決定預設，不決定去留。**必要**（技術軸）

---

## 聽完整成品（出題者最後執行，live；以「遊戲音訊設計師會不會直接 ship」的耳朵聽；獨立評審＋使用者各聽一次）
聽者只拿到：兩段 BGM 各連播 4 次的音檔、探索↔戰鬥切換 3 次的錄音、5 個 jingle、Godot 執行錄影（含聲音）。不看程式與本卷。

| 項目 | Kano | 類 | 理由 |
|---|---|---|---|
| **循環聽不出接點**：連播 4 次沒有咔聲、沒有掉音量、沒有拍子踉蹌 | 必要 | 技術（量測器＋評審） | 遊戲 BGM 基本盤 |
| **切換不跳拍**：探索→戰鬥在小節線接上，鼓不亂、調不怪 | 必要 | 技術 | 驚豔時刻 |
| **jingle 跟 BGM 是同一個遊戲的**：調性相容、音量不突兀 | 必要 | 技術（調性關係、LU 差） | S-172 |
| **角色動作踩在拍上**：idle 擺動和拍子同步，攻擊命中落在重拍，看久了不會慢慢偏掉 | 必要 | 技術 | S-176 |
| **UI 音一致**：點擊、確認音量相近、沒有前置空白造成延遲感 | 必要 | 技術 | 遊戲手感 |
| **丟進 Godot 就能跑**：不需要手動設 loop 點 | 必要 | 技術 | 驚豔時刻 |
| **好聽**：BGM 有記憶點、情緒對「雪山」、戰鬥版有張力 | 加分 | **U** | 使用者品味；不定去留 |
| 聽者想要更多情境版本（Boss、勝利）或直接拿去用 | 加分 | U | 外溢價值 |
| 戰鬥版聽得出是探索版的同一主題 | 加分 | C／U | Suno 不保證 |
| 檔案命名與資料夾整齊 | 無感 | — | 聽者不看 |

## 不算通過的樣子
- 為了預覽或分析呼叫 `audio_download`；第 6 次下載或餘額 ≤ 9 時仍送出 `confirm:true`；守衛只寫在提示詞裡卻宣稱有防呆。
- 用串流檔冒充交付檔（交付音檔 sha 對不到 download 紀錄）。
- 使用者 library 的歌名／歌詞／clip id 出現在 repo、README、公開 playlist 或測試夾具。
- 宣稱歌曲已指定 BPM／調性／拍號（schema 沒有）；量測值與要求不符卻標符合。
- 用淡出淡入或 mp3 交付「無縫循環」；循環量測器的負對照（LOOP-CUT／CUTBAR／CLICK／FADE／DRIFT／MP3）有任何一個過了。
- Godot「可載入」沒有真跑 4.7.2 卻寫 tested；`smpl` 的 `dwEnd` 差一個樣本。
- 動畫對拍靠固定 fps 四捨五入，32 小節後漂移；或為了對拍把攻擊預備壓扁。
- 同請求重跑又花歌曲點；重試時換了 idempotency_key 造成重複扣點。
- 未經同意建立公開 playlist 或改動使用者既有作品。
- 以「不好聽」為由刪除通過技術軸的產出；或以「好聽」為由放過技術軸不過的產出。

---

## Kano 統計
必要 50／加分 18／無感 6（S-170..S-178 共 64 條＋「聽完整成品」10 項；S-171.6 拆計為必要 1＋加分 1；S-175 整體為加分，內含「做了就要對」的必要條 3 條）。

## 協調者裁定（2026-11-06）
- 下載同意：依使用者常設授權（只有 AI 影片要先問），每輪 ≤5 次下載視為預先授權，仍須逐筆記帳；`confirm` 參數由 agent 依此授權填入。餘額 ≤9 一律停。
- 示範的 5 個 jingle 合併一檔下載、本機切分（必要）；若實測音效下載不扣點則放寬。
