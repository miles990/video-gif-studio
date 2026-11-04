# 答案卷 — fx 程式化特效／轉場框架（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec.md（含「比推文更好的做法」S-10..S-14）、scripts/compose_timeline.py、references/timeline.md、
references/music.md、scripts/qa_media.py CLI、scripts/music_sync.py、scripts/background_remove.py、examples/ 實況（出題者 2026-11-04 查得）。
每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條）。

## 共通規則
- Python：技能 venv `C:\Users\User\.codex\skills\video-gif-studio\.venv\Scripts\python.exe`（有 cv2；系統 Python 沒有 cv2，不能當驗收環境）。
  ffmpeg 以 `VIDEO_GIF_FFMPEG`／`VIDEO_GIF_FFPROBE` 指定（經 media_runtime），PATH 上沒有。
- 「格時間」：輸出若為固定 fps F，第 i 格起始 = i·1000/F ms，1 格容差 = 1000/F ms；若輸出沿用 `durations_ms`（可變），以累加計。
  「時間 T 顯示的格」= 起始 ≤ T < 結束 的那一格。容差寫「±1 格」即以此計。
- 亮度 Y = 0.2126R+0.7152G+0.0722B（0–255，sRGB 值直接算，不做線性化）。透明素材量 RGB 時只看 alpha>0 的像素；alpha=0 的隱藏 RGB 不算畫面。
- 「報錯」= 非 0 結束、**不得有 traceback**、不得建立 `--out` 目錄、在任何像素算繪前發生（牆鐘 < 3 s）。
- 不得修改 examples/：驗收前後 `git status --porcelain --ignored examples/` 必須相同（含被忽略的新檔；**不得用 `examples/neon-zen-pv/prepare_segment.py`，它會寫進 examples/**，
  改用 `scripts/gif_pipeline.py <source.mp4> --out wow/fx/demo/work/...`）。不得修改本答案卷。
- 已安裝技能 `~/.codex/skills/video-gif-studio` 除 venv 使用外不得改動（`git -C` 該處 status 不變）。

## 合成素材 SYN（測試與評審自行產生；建造者的測試也應涵蓋同型）
放在臨時資料夾 D，皆為 repo 標準動畫格式（`X/manifest.json` 含 `durations_ms`，旁邊 `X/frames/00000.png…`）。畫布 320×180。
| 代號 | 內容 |
|---|---|
| A | 50 格 × 40 ms（2000 ms），不透明；底色 (220,40,40)；白色 16 px 寬直條在 x=4i..4i+15（i = 格號） |
| B | 50 格 × 40 ms，不透明；底色 (40,60,220)；黑色 16 px 高橫條在 y=2i..2i+15 |
| C（透明主體） | 50 格 × 40 ms；橢圓中心 (160,90)、半徑 (40,60)，顏色 (200,160,60)、alpha 255；邊緣向外 3 px 線性衰減到 0；其餘 alpha=0，隱藏 RGB：偶數格 (0,0,0)、奇數格 (255,0,255)【陷阱】 |
| beats.json | `{"beats_ms":[0,500,1000,…,6000]}`（13 拍，120 BPM） |
| syn.wav | 48 kHz mono 16-bit、6.000 s，Python `wave` 產生：每拍起點放 30 ms、1 kHz 指數衰減短音；拍號偶數振幅 0.8、奇數 0.2（−12 dB） |
| syn-ramp.wav | 6.000 s、440 Hz 正弦，振幅從 0.02 線性升到 0.8 |
| 量測區 R | x∈[240,320)、y∈[130,170)：A 的直條（x≤211）與 B 的橫條（y≤113）永遠不會進入，只有底色 |

基準計畫 **P-base**（欄位名以建造者文件為準；以下用 `transition` 放在「進入該段」的段落上、強度參數稱 `amount`）：
```json
{"beatmap":"beats.json","music":{"file":"syn.wav"},
 "segments":[
  {"type":"animation","manifest":"A/manifest.json","end_beat":4},
  {"type":"animation","manifest":"B/manifest.json","end_beat":8,
   "transition":{"name":"crossfade","duration_ms":400}},
  {"type":"still","manifest":"C/manifest.json","frame":"first","end_beat":12,
   "transition":{"name":"hex_shutter","duration_ms":500}}],
 "effects":[
  {"name":"flash_white","start_beat":1,"end_beat":2,
   "amount":{"on":"beats","attack_ms":0,"decay_ms":200,"curve":"linear"}},
  {"name":"cutout_card","start_beat":9,"end_beat":12,"border_px":6}]}
```
指令：`python scripts/fx_render.py D/P-base.json --out D/out1 --formats png gif mp4`（指令名以建造者為準）。

---

## S-1 函數契約 —— 必要（框架的根；沒有它其他條都無從談起）
輸入：每個內建效果／轉場各呼叫一次；frame = A 第 0 格（320×180），分別以 uint8 與 float32（/255）各一份；轉場 a=A[0]、b=B[0]，p ∈ {0, 0.25, 0.5, 0.75, 1}。
ctx 由框架提供的建構函式產生（beats = beats.json，fps 25）。
預期：
1. 輸出 shape == (180,320,4)；dtype 符合文件契約（文件須寫明「回傳與輸入同 dtype」或「一律 float32」其一，實測一致）；無 NaN/Inf；float 在 [0,1]。
2. 純函數：呼叫後輸入陣列逐位元不變（先 `copy()` 比對）。
3. 決定性：同輸入呼叫兩次 → `np.array_equal`；不同行程（`PYTHONHASHSEED=1` 與 `=2`）各跑一次 → 輸出 sha256 相同。
4. ctx 至少有：寬、高、fps、拍點表、距上一拍、距下一拍、段落資訊（索引、起訖 ms）。t=1100 → 距上一拍 100、距下一拍 400；t=1000（正落拍）→ 距上一拍 0。
5. 轉場端點：p=0 輸出 ≈ a、p=1 輸出 ≈ b（MAE ≤ 1/255），flash_cut 亦同。
6. 隨機性：ctx 或參數提供 seed（文件寫明）。用 fx-dir 自訂一個呼叫該 RNG 的雜訊效果：同 seed 兩次 → 位元相同；seed 不同 → ≥ 1% 像素不同。

## S-2 內建效果與轉場 —— 必要（推文的六個例子就是使用者要的東西）
直接呼叫函數量（量測區 R，除非另註）：
| 項目 | 輸入 | 預期 |
|---|---|---|
| flash_white | A[0]，amount=1 / 0.5 / 0 | Y ≥ 250 / 介於原值 78±2 與 255 之間（線性約 167±15）/ = 原值（MAE ≤1/255）|
| beat_bounce | A[0]，拍點強度 1 與 0 | 1 → 與輸入不同（位移或縮放可量）；0 → 等於輸入（MAE ≤1/255）；文件寫明位移 px／旋轉度／縮放的預設值 |
| halation | 黑底中央 20×20 白方塊（Y=255） | 方塊外 10 px 內出現光暈（平均 Y ≥ 8）；距方塊 60 px 外 Y ≤ 2；warm 參數開啟時光暈區 R−B ≥ 10；原本不透明全黑區不變黑以外的顏色 |
| grade | A[0]：gain 1/gamma 1/lift 0/sat 1/temp 0（中性） | 輸出 = 輸入（MAE ≤ 1/255）；sat=0 → R=G=B（差 ≤1/255）；temp 暖 → R 升、B 降 |
| zoom_punch | A[0]，強度 1 | 中心 1 px 位置不變（中心像素差 ≤ 2/255）；直條變寬（量測寬度 ≥ 16×1.05）；強度 0 → 等於輸入 |
| cutout_card | C[0]，border_px=6 | 見下方「cutout 量測」 |
| crossfade | a=A[0]、b=B[0]、p=0.5 | 區 R 平均 (130±10, 50±10, 130±10) |
| whip_pan | a=b=8 px 直條紋（黑白），p=0.5；另 a=b=8 px 橫條紋 | 直條紋的水平方向標準差下降 ≥ 50%；橫條紋的垂直方向標準差保留 ≥ 80%（方向性模糊，不是全域模糊）|
| hex_shutter | a=A[0]、b=B[0]，p 取 0,0.05,…,1（21 點） | 「被遮像素」= 與 a、b 兩者 RGBA 差都 > 8/255 的像素。p=0.5 被遮 ≥ 90%；p=0.25、0.75 介於 15%–85%；0→0.5 單調不減、0.5→1 單調不增（容差 2%）；p=0、1 被遮 ≤ 1% |
| flash_cut | a=A[0]、b=B[0] | p=0.5 Y ≥ 240；p=0.25 區 R 偏紅（R−B ≥ 20）、p=0.75 偏藍（B−R ≥ 20） |

cutout 量測（C[0]，透明畫布，未設背景）：
- 白邊：橢圓邊界（alpha=0.5 等值線）向外 2–4 px 的環帶，≥ 95% 像素 RGB ≥ 240 且 alpha ≥ 0.95。
- 主體內部（距邊界向內 ≥ 5 px）RGB 與 (200,160,60) 差 ≤ 3/255、alpha=1。
- 陰影：文件寫明方向；在該方向白邊外 2 px 處 alpha>0 且 Y 低於白邊 ≥ 100。
- 透明保留：距橢圓 ≥ 40 px 的像素 alpha=0；指定 `bg` 顏色時這些像素 = 該色 ±2、alpha=1；指定變暗／模糊時背景 Y 下降可量。
- 【陷阱】奇數格（隱藏 RGB 洋紅）輸入：輸出中 alpha>0.05 的像素裡，去預乘後接近 (255,0,255)（各通道差 ≤ 40）的像素 = 0；白邊與主體之間不得有暗環（環帶 0–2 px 內 Y < 150 的像素 ≤ 2%）。

透明保留（所有「色彩類」效果：flash_white、grade、halation 預設）：輸入 C[0] → 輸出 alpha 與輸入**逐像素相同**（uint8 完全相同；float 差 ≤ 1e-6）；
halation 預設不得讓 alpha=0 區變成 alpha>0（若有「光暈擴張 alpha」選項，須預設關閉並寫明）。
幾何類（beat_bounce、zoom_punch）：alpha 總和變化 ≤ ±3%（未出畫面時，與縮放比例平方相符），半透明邊緣去預乘 RGB 與 (200,160,60) 差 ≤ 10/255（無黑邊）。
每個效果／轉場在 `--list` 有參數說明與預設值（見 S-5）。

## S-3 節拍驅動包絡 —— 必要（「卡點」的核心，沒有就退回手動 keyframe）
直接呼叫包絡求值函數（名稱由建造者定、文件寫明），beats = beats.json：
| 包絡 | 預期值 |
|---|---|
| 常數 0.7 | 任意 t → 0.7 |
| keyframes `[[0,0],[1000,1]]` 線性 | t=500 → 0.5±1e-6；t<0 → 0；t>1000 → 1（夾住，文件寫明） |
| `{"on":"beats","attack_ms":0,"decay_ms":200,"curve":"linear"}` | t=1000 → 1.0；1100 → 0.5±0.02；1200 → 0；999 → 0；1450 → 0 |
| 同上加 `attack_ms":100` | 峰值仍在拍點上（t=1000 → 1.0）；t=950 → 0.5±0.02（文件寫明 attack 在拍前）|
| 指定拍號清單 `[1,3]` | 500、1500 → 1；1000 → 0 |
| 每 N 拍 `every:2` | 觸發於 0、1000、2000…（索引 0,2,4…；若從 start_beat 起算須文件寫明，實測一致）|
| 效果區間 `start_beat:1,end_beat:2` | 區間外輸出 = 未加效果（MAE ≤1/255）；文件寫明 end 是含或不含 |
| `start_ms/end_ms` | 同上，以 ms |

剪點與轉場對齊（P-base，`out1/manifest.json` 與 frames）：
- 段落邊界 = 2000、4000 ms（恰好；10 ms 規則）。
- 文件寫明轉場是「以剪點為中心」或「對齊剪點（起/止）」。依寫明的對齊，p=0.5 的格落在預期時間 ±1 格；crossfade 該格區 R 平均 (130±10, 50±10, 130±10)。
- 轉場窗外：t ≤ 1760 的格區 R = (220,40,40)±1（flash 已衰減完）；轉場後 t ≥ 2240 = (40,60,220)±1（置中時）。
- 偏移規則【陷阱】：beats `[0,1234.4,2468.8,3703.2]`、`music.in_ms:100`、`end_beat:1` → 剪點 = 1130 ms；同一拍的 flash 峰值格在 1134.4 ms ±1 格（效果與剪點用同一套「減 in_ms」的時間）。
- 若置中轉場需要剪點後的 A 素材而 A 已用完，文件須寫明處理（延長末格／取 out_ms 之後的源影格），剪點時間不得因此改變。

## S-4 計畫與指令 —— 必要（一個指令出片是驚豔時刻本身）
1. P-base 一個指令成功，`out1/` 有與 compose_timeline 相同的交付物：`frames/`、`manifest.json`、`qc.json`、要求的 `animation.gif`、`animation.mp4`（含音軌：ffprobe 見 audio stream，`qc.json` 的音訊時長與畫面差 ≤ 100 ms）。
2. manifest 每個效果／轉場一筆：名稱、**解析後完整參數（含預設值）**、作用起訖 ms、beat 驅動者列出觸發時間；P-base 中 flash 觸發時間含 500、1000（依 end 含否），不含 0、2000。
3. 決定性：同計畫算兩次（新 out 目錄）→ `frames/*.png` sha256 全部相同；manifest 除路徑／時間戳記外相同（排除欄位須文件寫明）。
4. 空 fx 計畫等價【陷阱】：把 P-base 去掉 `transition` 與 `effects` → fx_render 的每一格，與 compose_timeline 同計畫在同一時間顯示的格**像素相同**（MAE 0），總長差 ≤ 1 格。
5. 不破壞既有：`git diff main -- scripts/compose_timeline.py` 若有改動，舊計畫（timeline.md／music.md 的範例型、SYN 版）在 main 與分支的輸出 frames sha256 相同；`tests/test_timeline.py`、`tests/test_music.py` 全過。
6. 定格摳像：一段 `still` ＋ cutout_card 即可做出（P-base 第 3 段），不需額外前處理指令（主體 alpha 來自素材本身）。
7. 已存在的 `--out` → 報錯不覆蓋（同 compose_timeline）；music 但只要 GIF → 同 compose_timeline 的錯誤。

## S-5 可擴充 —— 必要（「收進框架、下次直接調用」的機制）；--preview 加分（一眼看完所有效果很驚豔，但不影響出片）
- `D/fx1/invert.py` 用文件寫明的註冊方式定義 `my_invert`（RGB→1−RGB、alpha 不變），計畫中使用；`--fx-dir D/fx1` → 作用區間內區 R = (35,215,215)±1（A 底色反轉）。
  不改任何框架檔案即可（`git status` 只有計畫與 fx1 在 D）。
- `--fx-dir D/fx1 --fx-dir D/fx2`，fx2 也定義 `my_invert`（輸出全白）→ 依文件寫明的優先序生效，且 stdout/stderr 與 manifest **明確報告覆蓋**：名稱 ＋ 兩個來源檔路徑。覆蓋內建 `grade` 也一樣要報告。
- `--list`：列出所有內建 6 效果＋4 轉場＋已載入的自訂效果，每個含參數名、型別或範例、預設值、一行說明；`--list --fx-dir D/fx1` 會多出 my_invert 與來源路徑。（機器可讀 `--json` 加分）
- `--preview`（可配 `--fx-dir`）：輸出單一 PNG；含每個效果在同一幀上一格、每個轉場 p=0.25/0.5/0.75 三格，每格有文字標籤；數量 = 效果數 + 3×轉場數（評審肉眼數）；牆鐘 ≤ 15 s。

## S-6 錯誤訊息 —— 必要（計畫是 agent 寫的，寫錯看不懂 = 使用者被卡住）
每個都以 P-base 為底改一處，必須符合「報錯」定義，且訊息同時含：①計畫位置（如 `effects[0]`、`segments[1].transition`），②錯的那個字，③可用選項／有效範圍。
| 改動 | 訊息須含 |
|---|---|
| `"name":"flash_whit"` | `effects[0]`、`flash_whit`、可用效果清單（含 `flash_white`）；有「did you mean flash_white」類建議加分 |
| `"amout":1`（參數拼錯） | `effects[0]`、`amout`、flash_white 的有效參數清單（含 `amount`） |
| `"border_px":"wide"`（型別錯） | `effects[1]`、`border_px`、期望型別 |
| `"decya_ms":200`（包絡內鍵拼錯） | `effects[0]`、`decya_ms`、包絡有效鍵 |
| `"start_beat":99` | 99、有效範圍 0..12 |
| transition `"name":"hexshutter"` | `segments[2].transition`、可用轉場清單 |
| crossfade `"duration_ms":3000`（相鄰段僅 2000） | `segments[1]`、3000、相鄰段長度 |
| 頂層 `"effcts":[...]`（鍵拼錯）【陷阱】 | 不得默默忽略；指出未知鍵 `effcts` 與有效頂層鍵 |

## S-7 品質與效能 —— 量測如實寫入文件：必要；≥10 fps：加分（目標不是門檻）；nearest：必要（像素畫被抹糊是本 repo 明令禁止）
- 合成 1280×720、30 fps、3.0 s（90 格）兩段 + crossfade 500 ms + grade + halation + beat_bounce 同時作用；量「算繪到 RGBA 格」的 fps（不含 GIF/MP4 編碼）。
  references/fx.md 寫明數字、機器、numpy/opencv 版本、量法；評審重跑，實測與文件差 ≤ ±30%，或文件數字比實測保守。
- `grep -nE "for (y|x|row|col|px) in range" scripts/fx/` 不得出現逐像素 Python 迴圈。
- 像素畫：32×32、4 色調色盤、以 nearest ×8 放大成 256×256 的 RGBA 精靈；beat_bounce（縮放 1.25、旋轉 7°）與 zoom_punch 以 nearest 模式 → 輸出所有 alpha>0 像素的顏色 ⊆ 原 4 色；alpha 只有 0 或 255。
  預設模式（非 nearest）若會產生中間色，文件須寫明如何開啟 nearest；若素材 manifest 標記為 pixel art 而仍平滑，須至少警告。

## S-8 文件 —— 必要（下一部片的 agent 只會讀文件）
- `references/fx.md` 存在且含：契約（簽名、dtype、t 單位 ms、p、ctx 欄位）、內建清單＋參數＋預設、包絡語法（常數／keyframes／beats／onset／energy／downbeats）、
  轉場對齊規則、一個 ≤ 10 行可直接存檔使用的自訂效果範例（評審照抄到 fx-dir 能跑）、「何時用／何時不用」、效能數字、使用者層級庫的收錄步驟（S-13）。
- `grep -n "transitions/crossfades" references/music.md` 與 timeline.md 中「without transition blends」等敘述已更新為指向 fx.md（不再說未內建）。
- SKILL.md 的 Simple local editing 段提到 fx_render／fx.md；且明寫：只在使用者要求後期特效時使用、不替角色動作發明特效、不以特效取代物理動作或掩蓋壞轉場（與 SKILL.md 第 81 行一致）。

## S-9 測試 —— 必要
- `python -m unittest discover -s tests`（技能 venv）：基準 146 tests／2 個既有環境錯誤；建造後 tests ≥ 146＋新增，error 仍只有那 2 個，failure 0。
- 新增測試至少斷言：每個內建效果／轉場的 shape、dtype、alpha、決定性；包絡在拍點的值（S-3 表）；P-base 剪點 2000/4000 與轉場 p=0.5 格；自訂 fx-dir 載入與覆蓋報告；S-6 表至少 5 列（斷言訊息內容，不只斷言有例外）。
- 除 MP4 輸出外的測試在**無 ffmpeg** 下實際執行，不得 skip。

## S-10 跟著音樂強度（onset／energy 包絡）—— 必要（spec 宣稱比推文好的第一點；沒做就只是推文的翻版）
- 輸入：beats.json ＋ syn.wav；`{"on":"onset"}` 驅動 flash_white amount。
  預期：偶數拍（響）峰值 ≥ 0.9；奇數拍（−12 dB）峰值 ≤ 0.5；兩者比值 ≥ 2；對映方式（線性 RMS 或 dB）文件寫明。成片中響拍那格 Y 比輕拍那格高 ≥ 30。
  峰值時間在短音起點 ±10 ms（10 ms hop）內，成片中 ±1 格。
- syn-ramp.wav ＋ `{"on":"energy"}`：每 100 ms 取樣單調不減（容差 2%）；t=5 s 值 ≥ 3× t=1 s 值。
- 舊 beats.json 沒有強度曲線【陷阱】（examples/neon-zen-pv/music-analysis/beats.json 只有 `onsets_ms` 時間點與 1000 點 `waveform`，沒有 10 ms 強度）：
  要嘛由計畫的 `music.file` 重算（文件寫明、需 ffmpeg 時缺了要報錯含 media_runtime 安裝指示），要嘛報錯指出缺哪個欄位與重新分析的指令。不得默默當成全 0 或全 1。
- `music_sync.py` 新增輸出的欄位不得改變既有 `beats_ms`／`onsets_ms` 值（同一 wav 前後比對相同），test_music 全過。零新依賴：`git diff main -- requirements.txt` 無新增。

## S-11 重拍（Beat This! 選用引擎）—— 介面＋退回＋離線測試：必要；實機下載模型實測：加分（由主 agent 在沙盒外做）
- 未安裝 beat_this：`music_sync.py syn.wav --out D/bt --engine beat_this` → 清楚訊息（含套件名與安裝方式），並依文件行為退回 RMS：
  產出的 beats.json 記錄實際使用的引擎（如 `"engine":"rms"`）與退回原因；不得 traceback；不得假造 `downbeats_ms`。
- 計畫用 `"on":"downbeats"` 或 `end_downbeat`，但 beats.json 沒有 `downbeats_ms` → 報錯（S-6 定義），指出位置與「需 --engine beat_this」。
- 離線測試用 repo 內錄製的 Beat This! 輸出（fixture）：`downbeats_ms` 嚴格遞增、每個都在某個 `beats_ms` ±10 ms 內；`end_downbeat:k` 剪點 = round((downbeats_ms[k]−in_ms)/10)·10；
  `"on":"downbeats"` 只在重拍觸發（非重拍的拍值 = 0）。引擎介面可替換（測試能注入假引擎）。
- `requirements.txt` 不新增 torch／beat_this（可另放選用 requirements 檔）；THIRD_PARTY.md 含 Beat This! 出處 https://github.com/CPJKU/beat_this 、MIT 全文與版權行；music.md 更新「不辨重拍」敘述為「預設不辨，選用引擎可」。
- 實機（加分）：neon soundtrack.flac 以 beat_this 分析，相鄰重拍間距中位數 ≈ 4 拍（82 BPM → 2927 ms ±5%），結果與牆鐘記入 wow/fx/demo/。

## S-12 摳像品質（birefnet 選項）—— 必要：選項＋文件；加分：實測對照圖
- `background_remove.py --model` 接受 `birefnet-general`、`birefnet-portrait`；預設仍是 `u2netp`（不改既有行為）；無效名稱 → argparse 報錯列出選項。
- 沒裝 rembg（此機系統 Python 即是）→ 訊息指向 `requirements-matting.txt`，無 traceback。輸出 manifest 記錄 `model`。
- 離線測試用注入 masker，斷言 model 名稱被傳遞與記錄；不得在測試中下載模型。
- 文件（fx.md 或 background_remove 相關文件）寫明：定格摳像建議 birefnet-*（單張、品質優先）、每格耗時實測（若未實測須寫「未實測」）、影片逐格仍建議 u2netp 的理由。
- 加分：同一張 neon 定格以 u2netp 與 birefnet-general 摳像的邊緣對照圖放 wow/fx/demo/。

## S-13 使用者層級效果庫 —— 必要（推文「每做完一部片收進框架」的具體機制）
- 位置文件寫明（例 `~/.video-gif-studio/fx/`），且可用環境變數（或文件化方式）改指，讓測試不碰真實家目錄。
- 測試：把環境變數／`USERPROFILE`＋`HOME` 指向臨時夾，放入 `glow_lib.py` 定義 `lib_glow` → 不加任何旗標，`--list` 出現 `lib_glow` 與來源路徑；計畫可直接使用。
- 優先序文件寫明（建議 內建 < 使用者庫 < `--fx-dir`），任何層級覆蓋都報告（同 S-5）。可關閉自動載入（如 `--no-user-fx`）加分。
- 資料夾不存在 → 不報錯、不建立。庫內某檔語法錯 → 指出檔名與行號，不讓內建效果失效（跳過並警告，或明確報錯，文件寫明其一）。
- manifest 對每個非內建效果記錄來源檔路徑＋sha256（庫會變，成片要可追溯）。
- fx.md 有「收進庫」步驟：命名、參數說明、一張預覽、來源作品。

## S-14 逆向拆解（fx_reverse）—— 來回測與草稿計畫：必要；混淆表與縮圖表：必要；轉場類型辨識準確度：加分
**來回測素材 P-rt**（SYN 素材＋beats.json＋syn.wav，25 fps，總長 6000 ms）：
段落：A[0–1000) → B[1000–2000) → A[2000–3500) → still B 第 0 格 [3500–4500) → B[4500–5180) → A[5180–6000)（段長用 duration_ms／in/out 調出）。
| 時間 ms | 事件（已知真值） |
|---|---|
| 1000 | 硬切 A→B（無 transition） |
| 1500 | flash_white，attack 0、decay 120 |
| 2000 | whip_pan B→A，duration 240，水平（文件寫明方向參數） |
| 3000 | zoom_punch，強度使尺度變化 ≥ 1.15 |
| 3500–4500 | 定格 1000 ms（進入定格是硬切，3500 算一個 cut） |
| 4500 | hex_shutter，duration 400 |
| 5180 | 硬切，**不在拍上**【陷阱】 |
指令：`fx_render.py P-rt.json --out D/rt --formats mp4` → `fx_reverse.py D/rt/animation.mp4 --out D/rev`（有音軌則一併分析拍點；另跑一次附 `--beats D/beats.json` 或文件化等價旗標）。
預期：
1. `D/rev/report.json` 可 json.load；`D/rev/` 有逐鏡縮圖表（每個偵測鏡頭至少一張縮圖，標時間）與草稿計畫（如 `draft-plan.json`）。
2. 硬切 1000、3500、5180 被偵測，誤差 ≤ 1 格（40 ms）；whip_pan（2000）、hex_shutter（4500）報為「轉場」並帶類型，各只算一個剪點，不得報成兩個硬切；
   閃白（1500）與縮放衝擊（3000）不得被報成 cut。
3. 閃白偵測在 1500 ±1 格；定格段偵測為 3500–4500（起訖各 ±1 格），定格中段不得報 cut。
4. 甩鏡／動態模糊在 2000 ±2 格並帶方向（水平）；縮放衝擊在 3000 ±2 格並給尺度變化估值（≥ 1.1）。
5. 剪點落拍率：{1000, 2000, 3500, 4500, 5180} 中落在拍點 ±1 格者 → 4/5（依文件定義計算亦可，但報告須寫明分子分母與容差）。
6. 草稿計畫：只用本框架內建名稱；`fx_render` 的計畫驗證（S-6 規則）**直接通過**（素材路徑可為佔位但須明確標示，換成 SYN 路徑即可算繪）；信心低的項目帶 `"review": true`；
   把草稿換回 SYN 路徑重新算繪 → 再跑 fx_reverse，剪點與閃白時間與第一次一致（±1 格）。
7. 混淆表：建造者自行設計 ≥ 3 支已知計畫（每種內建轉場至少出現 2 次）的來回測，fx.md 或 wow/fx/ 下寫出「真實轉場 × 偵測類型」混淆表；
   硬切與閃白的時間誤差全部 ≤ 1 格是必要，類型正確率是加分（如實寫）。
8. 真實素材煙霧測：`fx_reverse.py examples/neon-zen-pv/final.mp4 --out D/neon-rev` 不崩潰；剪點**不得**把 chain-qc 所列接續接點（5.55、11.73、17.60、24.20 s）以外的大量動作誤報為 cut（總 cut 數 ≤ 12）。
9. 授權與範圍：fx_reverse 與 fx.md 檔頭寫明只吸收 rea-video 的概念、自行實作；repo 內 `grep -ri "rea-video"` 只出現在出處／說明處；fx.md 有「拆解是為了學結構，不搬運他人畫面、音樂、肖像」；
   不提供 AI/實拍判定、反推提示詞、人聲分離。
10. 測試：來回測 1–5 至少有一支離線版本在 tests/ 中（可輸出 PNG 序列或 GIF 以避開 ffmpeg；不得 skip）。

## S-展示 —— 必要（驚豔時刻；沒有可看的片就沒有交付）
素材事實（出題者查得）：examples/ **沒有**已備好的影格夾（neon 的 `segment-0X/prepared/` 不存在、只有 `generation/source.mp4`）；
RGBA 角色只以成品存在：chibi `final.apng`（768²，112 格，alpha 覆蓋 6.5%、138 階軟邊）、robot `final.gif`（512²，145 格）、seated `final.gif`（640²，289 格）；
neon `final.mp4` 960×540、`soundtrack.flac`、`music-analysis/beats.json`（82 BPM、41 拍、拍點是非 10 ms 倍數的浮點）、`beatmap.json`（7 個編輯剪點）。
建造者必須在 `wow/fx/demo/work/` 自行準備影格（gif_pipeline）並統一畫布（4:2:0 需偶數尺寸）。
- `wow/fx/demo/` 有：`plan.json`、`demo.mp4`（含音樂）、`demo.gif`（預覽）、`preview.png`（--preview）、`qa/report.md`＋`report.json`、
  第二組 `plan-b.json` 與其輸出、`README.md`（一行重現指令、牆鐘、素材來源）。
- plan.json：必要 ≤ 60 行；加分 ≤ 35 行（spec「~30 行」）。內含至少：1 個 still＋cutout_card 定格、beat_bounce、flash_white、halation 或 grade、
  whip_pan／hex_shutter／flash_cut 至少兩種轉場。一個指令出片，牆鐘記錄在 README。
- 拍點量測：從 demo.mp4 解出每格 Y 平均；對 manifest 中每個 flash_white 觸發時間 T，[T−3格, T+3格] 內 Y 最大的格在 T ±1 格，且峰值比 T−3 格高 ≥ 40。
  每個轉場的 p=0.5 格在其剪點（或文件化對齊點）±1 格。
- `python scripts/qa_media.py wow/fx/demo/demo.mp4 --out wow/fx/demo/qa --expect-cuts <manifest 剪點秒數> --holds <定格區間>`：cuts PASS；frame 0 PASS；
  report 中每個 WARN/FAIL 都落在 manifest 已規劃事件（閃白／轉場）±1 格內，且 README 解釋；任何未規劃的 flash/pop/freeze = 不過。
- 第二組：`diff plan.json plan-b.json` 的差異行只有素材路徑值（manifest/image/file/beatmap）；換另一組角色＋影片（如 robot＋seated，或不同 neon 段）成功出片，
  且同樣通過上面的拍點量測。
- 不修改 examples/（見共通規則）。

## 看完整成品（評審肉眼判定；只看抽出的格與聯絡表，不看建造過程）
抽格：每個剪點 −3..+3 格、每個閃白拍 −1..+1 格、定格段首/中/尾、每個轉場 p≈0.25/0.5/0.75、demo.gif 聯絡表。看完整片（有播放器時以原速聽著音樂看）。
| 項目 | Kano | 理由 |
|---|---|---|
| 閃白、彈跳、轉場明顯「踩在拍上」，看/聽時不覺得慢半拍 | 必要 | 卡點片的全部價值；偏 1 格以上人眼就感覺得到 |
| 重拍比輕拍有力（S-10/11 的差別看得出來） | 加分 | 這是「比推文好」的可感部分 |
| 效果不像預設濾鏡：閃白有衰減曲線而非一格全白、光暈柔和不是糊一片、調色不偏色過頭 | 必要 | spec 列為「未抵達」；廉價感會讓使用者直接棄用 |
| 接點無瑕疵：剪點前後沒有一格黑格／錯位／畫布跳尺寸／上一段殘影 | 必要 | 任一可見瑕疵即不能交付 |
| 定格摳像卡片：白邊連續等寬、無鋸齒或缺口、無黑邊或原背景殘色、陰影方向一致 | 必要 | 驚豔時刻的主角 |
| 透明素材 alpha 邊緣乾淨（GIF 預覽無洋紅/黑點、APNG/MOV 半透明邊不發灰） | 必要 | spec：alpha 被毀＝未抵達 |
| 六邊形快門看得出是六邊形、收攏再張開；甩鏡有方向感 | 加分 | 形狀正確才有「設計過」的感覺 |
| 效果節制：不是每拍都疊滿；有呼吸與留白 | 加分 | 專業剪輯師會在意，一般人感覺「舒服」 |
| 角色動作沒被特效「發明」或取代（例如用 bounce 假裝跳躍） | 必要 | SKILL.md 既有預設 |
| 音樂起訖淡入淡出、無爆音、片長與音樂對齊 | 必要 | 成片含音樂是交付物 |
| preview.png 一張看完全部效果與轉場、標籤可讀 | 加分 | 選效果時省時間 |
| 第二組素材的片同樣成立（不是只在挑過的素材上好看） | 必要 | spec 明列「未抵達」 |
| GIF 預覽檔案大小合理（≤ 15 MB） | 無感 | 預覽用，使用者不會注意，除非大到打不開 |

## 不算通過的樣子
- 轉場或閃白偏離拍點 > 1 格；剪點不在 end_beat 的 10 ms 規則上；效果與剪點對 `music.in_ms` 的處理不一致。
- 透明素材 alpha 被改、隱藏 RGB 漏出、cutout 有暗環；像素畫在 nearest 模式出現新顏色。
- 加效果要改框架核心；覆蓋同名效果沒有報告；計畫鍵拼錯被默默忽略；錯誤訊息只有 traceback。
- 空 fx 計畫和 compose_timeline 輸出不同；既有測試退步；requirements.txt 新增必要依賴（torch、beat_this）。
- 修改 examples/ 或本答案卷；用挑過的單一素材宣稱通過 S-展示。
