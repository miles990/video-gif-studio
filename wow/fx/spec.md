# wow 輕量 — video-gif-studio：程式化特效／轉場框架（fx）（2026-11-04）

交付：輕量（wow references/lite.md）。分支 `fx-framework`，開發副本 C:\Users\User\src\video-gif-studio；
已安裝的 ~/.codex/skills/video-gif-studio 在驗收通過、合併前不動。
來源（使用者 2026-11-04 貼的推文 @MANISH1027512）：「特效說白了就是一個函數：輸入一幀畫面和當前時間，輸出處理好的一幀。
轉場也一樣，輸入前後兩個鏡頭的畫面和進度，輸出中間那一幀」；例：閃白、卡片隨節拍跳、甩鏡、六邊形快門、膠片光暈、摳人；
「每做完一部片，好用的效果收進框架，下一部直接調用」。
交付模式由 agent 選定（使用者只說「使用 wow 技能」）：需求已指定、範圍是一個核心情境，上一輪同 repo 也用輕量。

## 核心情境（只做這一個）
使用者給「素材（已備好的影格 manifest 或影片）＋音樂的 beats.json＋一句想法」，agent 寫一份 JSON 計畫，
一個指令就輸出節拍同步的成片：段落之間有轉場、畫面上有跟著節拍的特效、可做「定格摳像卡點」，不開任何剪輯軟體。
每個特效／轉場都是一個短小、可讀、可改的 Python 函數；專案自己的效果放進資料夾就能被同一個計畫呼叫。

## 驚豔時刻與未抵達的樣子
- 驚豔：一份 ~30 行的計畫＋一個指令，得到一支「定格摳像卡點」短片（凍結→主體摳出、白邊卡片隨拍彈跳、
  閃白／甩鏡／六邊形快門轉場、膠片光暈調色），轉場與閃白落在拍點上（qa_media 量得到）；
  `--list` 看到每個效果的參數，`--preview` 一張圖看完所有效果在同一畫面上的樣子；打開任一效果原始碼，十幾行就看懂。
- 未抵達：效果看起來廉價或像預設濾鏡；轉場或閃白偏離拍點 > 1 格；透明素材的 alpha 被毀；
  新增一個效果要改框架核心；計畫寫錯時報錯看不懂；成片只能在挑過的示範素材上成立。

## 驗收條目（S-編號；核心輸入與預期結果由獨立評審在建造前補上，見 acceptance.md）
- S-1 函數契約：`scripts/fx/`（或同等位置）提供兩種純函數簽名——
  效果 `effect(frame, t, ctx, **params) -> frame`、轉場 `transition(a, b, p, ctx, **params) -> frame`；
  frame 為 HxWx4 RGBA（float32 0–1 或 uint8，契約寫明），t 為毫秒，p 為 0–1 進度；ctx 提供畫布尺寸、fps、拍點表、
  距上一拍／下一拍的時間、段落資訊。同樣輸入必得同樣輸出（隨機效果用 seed）。
- S-2 內建效果（至少）：`flash_white`（像素推向白）、`beat_bounce`（位移＋微旋轉＋縮放隨拍衰減）、
  `halation`（亮部模糊後疊回、可帶暖色）、`grade`（lift/gamma/gain、飽和、色溫）、`zoom_punch`、`cutout_card`
  （把主體 alpha 摳出加白邊＋陰影，背景可變暗／模糊／換色，做定格摳像卡點）。
  內建轉場（至少）：`crossfade`、`whip_pan`（橫向動態模糊＋平移）、`hex_shutter`（先收攏再張開的六邊形遮罩）、`flash_cut`（閃白切）。
  每個都附參數說明與預設值；透明素材保留 alpha（cutout/轉場的 alpha 合成正確）。
- S-3 節拍驅動：參數可寫成時間包絡——常數、keyframes、或 `{"on":"beats","attack_ms":…,"decay_ms":…,"curve":…}`
  在每拍（或指定拍號清單／每 N 拍）觸發；效果可用 `start_beat`/`end_beat` 或 `start_ms`/`end_ms` 限定區間；
  轉場以剪點為中心或對齊剪點（寫明），剪點仍落在 `end_beat` 指定的拍上（沿用 compose_timeline 的 10ms 規則）。
- S-4 計畫與指令：沿用 compose_timeline 的 timeline JSON（segments、beatmap、music 不變），新增
  段落上的 `transition` 與頂層 `effects` 軌（以及定格：一段 still＋cutout_card 即可做出）。
  新指令（例 `scripts/fx_render.py plan.json --out DIR --formats …`）輸出與 compose_timeline 相同的交付物與 manifest，
  manifest 記錄每個效果／轉場的名稱、參數、作用時間。不得破壞既有 compose_timeline 行為與測試。
- S-5 可擴充：`--fx-dir DIR`（可多個）載入專案自己的 .py 效果，用註冊裝飾器或約定名稱；同名覆蓋需明確報告。
  `--list` 列出所有效果／轉場與參數；`--preview` 產出一張對照圖（每個效果在同一幀上的樣子＋轉場在 p=0.25/0.5/0.75 的樣子）。
- S-6 錯誤訊息：未知效果名、參數名拼錯、型別錯、拍號越界、轉場比相鄰段落長，都在算繪前報錯並指出計畫中的位置與可用選項。
- S-7 品質與效能：像素運算以 numpy／OpenCV 向量化；720p、30fps、同時 3 個效果＋1 個轉場的算繪速度在本機量測並寫進文件
  （目標 ≥ 10 fps；未達則如實寫）；pixel-art 素材可選 nearest 取樣，不偷偷平滑。
- S-8 文件：references/ 新增 `fx.md`（契約、內建清單、包絡語法、寫自訂效果的 10 行範例、「何時用／不何時用」）；
  timeline.md／music.md 中「transitions/crossfades 未內建」的敘述更新；SKILL.md 的 Simple local editing 路線接上；
  與 SKILL.md 既有預設一致——只在使用者要求後期特效時使用，不替角色動作「發明」特效、不取代物理動作。
- S-9 測試：tests/ 加離線測試（每個內建效果／轉場的形狀、dtype、alpha、決定性；包絡在拍點的值；剪點時間；
  自訂 fx-dir 載入；S-6 錯誤），既有測試不退步（基準：上一輪 146 tests／2 個既有環境錯誤）。
- S-展示 用 repo 內既有素材（examples/ 的 RGBA 角色與 neon-zen-pv 的影片＋beats＋soundtrack，皆為本 repo 作品）
  做一支「定格摳像卡點」示範 MP4（含音樂）與 GIF 預覽，計畫檔、`--preview` 對照圖、qa_media 報告放 `wow/fx/demo/`；
  再用第二組不同素材跑同一份計畫（只換素材路徑）證明不是只在挑過的素材上成立。

## 比推文更好的做法（使用者 2026-11-04：「吸收 改善 video-gif-studio技能, 看還有沒有更好的做法?用最好的做法做」）
調查（2026-11-04）後選定，每項寫明為什麼比推文的做法好、代價是什麼：
- **S-10 跟著音樂「強度」走，不只跟拍點**：推文的參數只跟時間與節拍變。新增包絡 `{"on":"onset"}`／`{"on":"energy"}`，
  從音樂本身的起音強度與響度曲線（music_sync 已算的 10ms RMS／onset）取值，重拍閃得重、輕拍閃得輕，不用手調每一拍。
  代價：零新依賴。
- **S-11 拍點升級為「重拍（downbeat）」**：repo 現在的 RMS 週期法不辨小節重拍（music.md 已寫明），卡點最該落在重拍。
  加選用引擎 Beat This!（CPJKU，MIT，2024 SOTA beat＋downbeat）：`music_sync.py --engine beat_this` 輸出 `downbeats_ms`，
  計畫可寫 `"on":"downbeats"`／`end_downbeat`。未安裝時清楚報錯並退回現有方法，不成為必要依賴；授權寫進 THIRD_PARTY。
  代價：選用的 torch／模型下載（由主 agent 在沙盒外安裝實測，建造者寫可替換介面＋錄製輸出供離線測試）。
- **S-12 摳像品質**：推文用 Mac「拷貝主體」。repo 的 background_remove 預設 rembg u2netp（輕但邊緣粗）。
  允許選 `birefnet-general`／`birefnet-portrait`（rembg 2.0.84 內建、同為本機 CPU），文件寫明定格摳像建議用哪個、速度代價；
  定格只摳一張，品質優先。
- **S-13 效果庫會長大**：除了 `--fx-dir`，自動載入使用者層級庫（例 `~/.video-gif-studio/fx/`），
  fx.md 寫「做完一部片把好用效果收進庫」的步驟（含命名、參數說明、一張預覽、來源作品）。這是推文「每做完一部片收進框架」的具體機制。
- **S-14 看到爆款 → 拆成可改的計畫（逆向）**（使用者 2026-11-04 貼的第二則推文 @ganfanren_ai：rea-video 逐鏡拆解畫面、剪輯、聲音並給復刻方案）：
  新指令（例 `scripts/fx_reverse.py ref.mp4 --out DIR`）把參考影片拆成：剪點時間、閃白格、甩鏡／動態模糊格（含方向）、
  縮放衝擊（整體尺度變化）、靜止定格段，以及音樂拍點與「剪點落拍率」；輸出 report.json、一張逐鏡縮圖表，
  以及一份**可直接給 fx_render 用的草稿計畫**（段落、end_beat、transition、effects 皆用本框架內建名稱，信心低的標 `"review": true`）。
  驗證用來回測：用 fx_render 算一支已知計畫的片 → fx_reverse → 剪點與閃白時間誤差 ≤ 1 格、轉場類型辨識結果寫出混淆表。
  **授權**：rea-video 倉庫未附開源授權（所有權利保留），只吸收「概念」，自行實作，不讀不抄其程式碼；
  不做 AI/實拍判定、反推提示詞、人聲分離（超出本核心情境，列之後候選）。fx.md 註明：拆解是為了學結構，不搬運他人畫面、音樂、肖像。
- 評估後**不採用**（列為之後候選）：gl-transitions（GLSL 轉場庫，需 GPU／Node 或 moderngl，增加安裝面；
  契約相同，之後可寫轉接器把 .glsl 當轉場載入）；讓 AI 操作剪映／Resolve（推文已說明繞遠路）；
  雲端剪輯 MCP（對外上傳素材、付費）。

## 不做
Mac「拷貝主體」（本機 Windows；摳像沿用 repo 既有 alpha／background_remove）；GUI 編輯器；GPU／shader；
多軌混音；字幕；自動依音樂寫計畫（agent 寫計畫即可）。

## 限制來源
- 輕量 3 小時／subagent ≤ 6：wow lite.md 預設（agent 沿用）。
- 不改 examples/、不動已安裝 skill：agent 自訂（避免毀使用者資料）。
- ≥ 10 fps 目標：agent 自訂儀器，不是門檻；未達如實寫。

## 預算
3 小時、subagent ≤ 6；無截止。建造者 Codex（跨廠商），評審與出題 Claude 子代理。
