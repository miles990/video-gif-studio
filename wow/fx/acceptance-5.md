# 答案卷 第五輪 — 交付層、字幕、音效、節拍分層、音樂裁長、具名運鏡、預覽、gl-transitions（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-5.md（S-50..S-64、P3、P4、評估修正）、wow/fx/research/synthesis.md、wow/fx/process.md（品質閘門、功能旗標）、
第三輪 wow/fx/acceptance-3.md（共通規則、音訊量測定義、QBD.wav 等素材）、第四輪 wow/fx/acceptance-4.md（S-41 重構圖數字、付費哨兵、量測不信任建造者）、
scripts/video_export.py（現況：第 52 行 `-framerate 100`、`frames --manifest --out --background`）、
scripts/qa_media.py（`input --out --fps --loop --holds --expect-cuts --timeline`；音訊 `loudness`／`true_peak`）、
scripts/fx_render.py（`plan --out --formats --background --fx-dir --list --preview --validate --interpolate`；轉場契約 `transition(a,b,p,ctx)`，見 scripts/fx/transitions/crossfade.py）。出題者 2026-11-04 查得。

每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條），並附理由。
新旗標、欄位、CLI 名以建造者文件為準；本卷用 spec 用語（`--fps`、`--platform`、`--keep-audio`、`--duck`、`--loudnorm`、`intake`、`--proxy`、`captions`、`sfx`、`cut_density`、`music_fit`、具名運鏡、`--review-html`、`keep/replace`），改名須在 fx.md 寫明對應。

## 共通規則（第一～四輪全部沿用，另加）
- 技能 venv、ffmpeg／ffprobe 經 `VIDEO_GIF_FFMPEG`（ffprobe 同目錄或文件化變數）、「報錯」定義（非 0、無 traceback、不建 `--out`、牆鐘 < 3 s）、不得改 examples/、不得改本答案卷、離線測試不下載／不讀真實權重、付費哨兵計數 = 0。
- **量測不信任建造者**：所有時間、響度、色彩、記憶體都由出題者量法（ffprobe、ffmpeg ebur128、psutil、numpy）從**輸出檔**量得，不讀建造者自報欄位當答案（自報值只用來比對是否誠實）。
- **±1 格** = 輸出 fps 的一格（30 fps → 33.33 ms）；**半格** = 16.67 ms。「格 k 的時間」= k/fps。
- **閃白偵測**：輸出 mp4 解碼後每格平均 Y；事件格 = 局部最大且 ≥ 前後 3 格中位數 + 40 的格。
- **字墨**：同計畫「有字幕」與「無字幕」兩次算繪逐格相減，|ΔY| > 16 或 alpha > 0.5 的像素。
- **ffprobe 指令**（下文簡稱 PROBE）：
  `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,pix_fmt,color_primaries,color_transfer,color_space,codec_name,profile,bit_rate:stream_side_data=rotation -of json OUT.mp4`
  逐格時間：`ffprobe -v error -select_streams v:0 -show_entries frame=pts_time -of csv=p=0 OUT.mp4`。
- **響度指令**（下文簡稱 EBU）：`ffmpeg -nostats -i OUT.mp4 -filter_complex ebur128=peak=true -f null -`，取 Summary 的 `I:`（LUFS）、`True peak: Peak:`（dBTP）、`LRA:`。
- **峰值記憶體量法**（下文簡稱 RSS）：出題者 harness 以 `subprocess.Popen` 啟動算繪，`psutil` 每 50 ms 取「該行程 + 全部子孫行程（含 ffmpeg）」RSS 總和，記錄最大值；Windows 另記 `peak_wset`（psutil `memory_info().peak_wset`）取兩者較大者。harness 碼入 tests 或 wow/fx/，結果寫 JSON（含機器、Python、ffmpeg 版本）。
- **舊計畫不退步**：第一～四輪 P-base、P-ramp、demo2/plan.json、demo3、demo4 plan → `--formats png` 的 frames **sha256 逐格相同**於第五輪前（第四輪結束 commit 對照）；GIF／APNG 輸出位元相同。MP4 預設 fps 改為 30 是**文件寫明的有意改變**，不算退步，但舊行為以明確旗標（例 `--fps 100` 或 `--legacy-100fps`）可重現，且輸出與舊版 mp4 解碼後逐格 PSNR ≥ 45 dB。

## 合成素材（第一～四輪全部照用；以下新增，全由測試程式以 numpy／ffmpeg lavfi 產生，不入庫真實影片或第三方音檔）
| 代號 | 內容 | 用途 |
|---|---|---|
| BIG | 1080×1920 RGBA、30 s、30 fps 計畫（900 格）：背景 = 程序漸層＋每格移動的雜訊紋理（防止編碼器過度壓縮讓測試失真）；事件 3 個效果：`zoom_punch`（拍上）、`rgb_split`（整段）、`film_grain`（整段）；節拍 120 BPM | S-50 記憶體 |
| BIG10 | 同 BIG 但 10 s（300 格） | S-50 片長無關 |
| BEATS-ODD | 拍點 = {0, 517, 1034, 1551, 2068, 2585, 3102, 3619, 4136, 4653} ms（間距 517 ms，故意不在 30 fps 網格上），每拍 `flash_white`（1 格） | S-51 量化 |
| SPEECH.wav | 48 kHz mono 20 s：「語音」= 300–3400 Hz 帶通白噪，以 4 Hz 音節包絡調變，振幅 0.3；出現在 4–8 s、12–16 s，其餘靜音 | S-53 ducking |
| MUS.wav | 48 kHz stereo 20 s：110 Hz 正弦 0.25 ＋ 6 kHz 正弦 0.05 ＋ 120 BPM kick；響度約 −20 LUFS | S-53 配樂 |
| HOT.wav | MUS.wav ×4（多處削波，true peak > 0 dBTP） | S-53 擋交付 |
| CLIP-A | 1080×1920 30 fps 10 s mp4，畫面 = 灰底＋每秒整秒格白閃；音軌 = 每秒整秒 1 kHz 10 ms click（−12 dBFS）＋ 440 Hz 底音 −30 dBFS | 保留原聲、A/V 同步 |
| PH-VFR | iPhone 樣式：1920×1080 HEVC 或 H.264，**VFR**：前 3 s 30 fps、3–6 s 24 fps、6–10 s 60 fps（`-fps_mode vfr` 以 setpts 產生），另每 10 格丟 1 格；畫面燒入**格號條碼**（16 個黑白方塊二進位）＋整秒白閃；音軌同 CLIP-A 的 click | VFR→CFR、同步 |
| PH-ROT | Android 樣式：儲存 1920×1080、display matrix rotation = −90（顯示為 1080×1920 直式；`ffmpeg -display_rotation 90 -i … -c copy` 或 `-metadata:s:v rotate=90`）；畫面內容 = **向上箭頭**（顯示方向）＋左上角紅色方塊（顯示方向）；10 s、30 fps、click 音軌 | 旋轉 |
| PH-HDR | HDR10：3840×2160 或 1920×1080、`yuv420p10le` HEVC、`color_primaries=bt2020`、`color_trc=smpte2084`、`colorspace=bt2020nc`，以 zscale 由 SDR 圖卡轉入；圖卡 = 11 階灰階條（0,10,…,100%）＋ 紅綠藍黃 75% 色塊＋膚色塊 (224,172,105)；附 MaxCLL 1000；5 s、30 fps、click 音軌 | HDR→SDR |
| SRT-W | 逐字時間 JSON／SRT（文件化格式）：中文句「我們今天要去台北市政府參加開放資料活動，真的嗎？好！」逐詞時間；英文句 "Make it pop at 3.14 seconds"；每詞起點已知 | S-56 |
| CJK-LB | 斷行測試字串集（見 S-56 第 3 條），每行字數上限 8／12／16 三種 | S-56 斷行 |
| BG-HARD | 字幕背景四種：純白 (255)、純黑 (0)、16 px 黑白棋盤、隨機彩色雜訊 | S-56 易讀 |
| SFXDIR-U | 使用者音效夾：`whoosh.wav` = 3.3 kHz 正弦 80 ms、`hit.wav` = 2.1 kHz 正弦 60 ms…（每類一個獨特頻率，當指紋） | S-57 優先序 |
| SFXDIR-K | 假 Kenney 夾（測試用、檔名仿 Kenney 結構）：各類另一組獨特頻率（4.7 kHz…）＋ License.txt（CC0） | S-57 優先序 |
| SONG64 | 48 kHz stereo **64 s**、120 BPM、4/4、首拍 0 ms → 32 小節（每小節 2000 ms）；段落：intro 0–8 s（4 小節）、verse 8–24 s、chorus 24–40 s、verse2 40–48 s、chorus2 48–60 s、outro 60–64 s；每段不同和弦音色（可分辨），每小節首拍 kick 較強；附 beats.json（beats、downbeats_ms、sections） | S-58、S-59 |
| CHART | 1080×1920 校準板：同心圓環（半徑每 40 px）＋十字中心＋ 32 px 棋盤；用來量每格縮放與平移 | S-60 |

基準指令（名稱以建造者為準）：
```
python scripts/fx_render.py D/plan.json --out D/out --formats mp4 --fps 30 --platform tiktok
python scripts/fx_render.py D/plan.json --out D/out --formats mp4 --proxy
python scripts/intake.py D/PH-VFR.mov --out D/in            # 或 fx_render 自動進件，文件寫明
python scripts/captions.py --srt D/SRT-W.srt --style pop --out D/cap   # 或計畫內 "captions" 鍵
python scripts/music_fit.py D/SONG64.wav --target 30 --candidates 3 --out D/fit
python scripts/qa_media.py D/out/out.mp4 --out D/qa --timeline D/out/manifest.json
```

---

## P0 交付層

### S-50 串流算繪 —— 必要（理由：現行整片入記憶體，1080×1920 30 s ≥ 7.5 GB，16 GB 機器必爆，交不出片）
1. **峰值記憶體**：BIG 以 RSS 量法量測 `fx_render.py BIG/plan.json --formats mp4 --platform tiktok`（1080×1920、30 fps、900 格、3 效果）→ 峰值 **≤ 1.5 GB**（1 610 612 736 bytes）。量 3 次取最大值。**必要**
2. **與片長無關**：BIG10 與 BIG 的峰值差 ≤ 15%（或 ≤ 150 MB，取較大者）。只有 30 s 版過 1.5 GB 而 10 s 版遠低於 = 仍是整片入記憶體 → 不過。**必要**
3. **真的是串流**：harness 每 50 ms 記錄輸出檔大小；在算繪牆鐘 50% 時，輸出 mp4（或暫存編碼檔）大小 > 0 且 ≥ 最終大小的 20%（證明邊算邊寫，不是最後才一次寫）。若建造者用「先寫 frames 到磁碟再編碼」→ 須另證磁碟暫存 ≤ 2 GB 且文件寫明；仍以第 1 條為準。**必要**
4. **正確性**：串流輸出與非串流參考（`--formats png` 後以同參數 ffmpeg 編碼）解碼後逐格 PSNR ≥ 45 dB；格數 = 900（PROBE `nb_frames`，或逐格 pts 計數）。**必要**
5. **失敗收尾**：算繪中途 raise（以 fx-dir 注入第 450 格丟例外的效果）→ 非 0、無殘留 ffmpeg 子行程（psutil 確認 5 s 內子孫行程數 = 0）、不留下可被誤認為成品的 `out.mp4`（刪除或改名 `.partial`）。**必要**（理由：半截 mp4 被當成品上傳＝最糟的交付錯誤）
6. GIF／APNG 路徑也串流或文件寫明上限（例 GIF 最多 N 格）；超過上限報錯而非 OOM。**加分**

### S-51 固定影格率輸出 —— 必要（理由：100 fps 上平台被重取樣，卡點在觀眾端消失）
1. 預設 MP4：PROBE `r_frame_rate == avg_frame_rate == "30/1"`；逐格 pts 差全為 1/30 s（容差 1 ms，ffprobe 精度）；`nb_frames` = round(片長×30)。MOV、WebM 同（WebM 用逐格 pts 檢查，因 nb_frames 可能為空）。**必要**
2. `--fps 24|25|50|60` 各一次：`r_frame_rate == avg_frame_rate == "N/1"`，格數 = round(片長×N)。其他值（例 29、100 未加明確旗標、0、−1）→ 報錯並列有效值；29.97 可接受與否文件寫明（接受則為 `30000/1001` 且兩者相等）。**必要**
3. **拍點量化**：BEATS-ODD 在 30 fps 輸出，每拍閃白偵測格 k_i；|k_i/30 − t_i| ≤ 16.67 ms（半格）全部 10 拍成立；量化規則 = 四捨五入到最近格（文件寫明；平手規則寫明）。**必要**
4. **誤差寫明**：manifest 每個事件記錄 `requested_ms`、`frame`、`quantized_ms`、`error_ms`；出題者以第 3 條量得值核對 `frame` 欄 100% 一致，|error_ms| 自報值與實際差 ≤ 0.1 ms。**必要**
5. 同 BEATS-ODD 在 60 fps：誤差 ≤ 8.33 ms；在 24 fps：≤ 20.83 ms。**必要**
6. **GIF／APNG 不受影響**：同計畫輸出 GIF，延遲序列仍為 10 ms 整數倍，第一～四輪 GIF 位元相同（共通規則）。**必要**
7. 兩個事件量化到同一格（例 30 fps 下 t=1000 與 t=1010）→ 不崩潰、manifest 記錄合併或順延規則，`--validate` 給警告。**加分**
8. qa_media 對 mp4 輸出回報 `cfr: true` 與實測 fps；餵入 100 fps 舊片 → 回報 `cfr: true, fps: 100` 並給「平台會重取樣」警告。**加分**

### S-52 平台預設 —— 必要（理由：使用者要一行交片到 TikTok／Reels／Shorts）
1. PROBE 數值（`--platform X`，計畫為 16:9 或 9:16 任一皆須轉到目標）：

| 平台 | width×height | fps | pix_fmt | color_primaries / transfer / space | codec | 位元率 |
|---|---|---|---|---|---|---|
| tiktok | 1080×1920 | 30 | yuv420p | bt709 / bt709 / bt709 | h264 | 文件值 ±25%（建議 8–16 Mbps） |
| reels | 1080×1920 | 30 | yuv420p | bt709 ×3 | h264 | 同上 |
| shorts | 1080×1920 | 30（文件可允許 60） | yuv420p | bt709 ×3 | h264 | 同上 |
| youtube | 1920×1080 | 30（或來源 fps 對應 24/25/30/50/60） | yuv420p | bt709 ×3 | h264 | 文件值 ±25% |
| square | 1080×1080 | 30 | yuv420p | bt709 ×3 | h264 | 文件值 ±25% |
   `color_range` = tv（limited）；`moov` 在 `mdat` 前（faststart；以 `ffprobe -v trace` 或讀 atom 順序確認）；音訊 AAC 48 kHz（或 44.1，文件寫明）、立體聲。**必要**
2. **色彩標記與實際一致**：輸出 75% 色條（計畫內 RGB (191,191,0) 等）解碼回 RGB（以 bt709 limited 反算）各通道誤差 ≤ 3/255——防止「標記 bt709 但用 bt601 矩陣」。**必要**
3. **安全區**：文件（references/fx.md 或 director.md）列每平台 UI 區，數值不得小於第四輪 S-41 第 6 條（9:16：上 ≥ 10% 高、下 ≥ 20% 高、右 ≥ 10% 寬）；square／youtube 也要寫（可較小）。字幕與標題字墨 **100%** 在安全區內（每格），距安全區邊 ≥ 2% 寬。**必要**
4. `--platform` 未知值 → 報錯列有效值；`--platform tiktok --fps 60` 衝突時規則寫明（覆寫或報錯）。**必要**
5. 平台預設 + 透明來源：輸出 alpha 被正確合成到文件化背景（不出現黑邊／預乘錯誤的深色暈）；見另卷。**必要**
6. 每平台一份 preset 表（JSON 或文件），含來源連結與查證日期。**加分**（理由：平台規格會變，可追溯即可）

### S-53 聲音 —— 必要（理由：音量忽大忽小、無原聲＝業餘感最強的來源）
1. **響度**：MUS.wav 作配樂、CLIP-A 原聲保留，`--platform tiktok` 輸出 → EBU：`I = −14 ±1 LUFS`、`True peak ≤ −1.0 dBTP`。HOT.wav 作配樂同樣達標（兩段 loudnorm 生效）。**必要**
2. **兩段**：log 或 manifest 記錄第一段量測值（`input_i`、`input_tp`、`input_lra`、`input_thresh`）與第二段 `linear=true` 或文件化理由；出題者以 EBU 量原始混音，與自報 input_i 差 ≤ 0.5 LU。**必要**
3. **保留原聲**：`--keep-audio`（或文件化預設）→ 輸出含 440 Hz 底音：Goertzel 440 Hz 能量比無原聲版高 ≥ 20 dB；`--keep-audio off` → 440 Hz 能量 ≤ 無原聲基準 +3 dB。click 時間 vs 畫面白閃 ±1 格（同步）。**必要**
4. **Ducking**：SPEECH.wav（原聲／旁白）＋ MUS.wav，量 110 Hz Goertzel（50 ms 窗）的配樂電平：
   - 深度：語音段（4.5–7.5 s、12.5–15.5 s 中段）相對非語音段（1–3 s、9–11 s、17–19 s）下降 **6–15 dB**（預設值文件寫明，實測與文件值差 ≤ 2 dB）。**必要**
   - 攻擊：語音起點後 ≤ 150 ms 內降到目標深度的 90%；釋放：語音結束後 200–1000 ms 內回到原電平 −1 dB 內；無抽吸（非語音段 110 Hz 電平標準差 ≤ 1 dB）。**必要**
   - 語音本身不被壓：300–3400 Hz 帶能量（語音段）與單獨 SPEECH 經同一 loudnorm 增益後差 ≤ 2 dB。**加分**
5. **擋交付**：關掉 loudnorm（測試旗標或直接餵 HOT 混音的 mp4）給 qa_media → true_peak FAIL、整體非 0；`fx_render --platform …` 的交付步驟遇 qa FAIL → 非 0 並不把檔放到最終路徑（或標 `.failed`）。**必要**
6. 只有音樂、無原聲 → 不 duck（110 Hz 電平全程標準差 ≤ 1 dB）。**必要**
7. 靜音音樂／無音軌情形見另卷。**必要**

### S-54 手機素材進件 —— 必要（理由：手機片 VFR、旋轉、HDR 是使用者第一個會碰到的坑）
共同：輸出 = 進件後中介檔（或直接算繪成片，文件寫明），PROBE 與解碼量測。
1. **PH-VFR → CFR**：輸出 `r_frame_rate == avg_frame_rate`（30/1 或文件化目標）、pts 等距；**時間正確**：解碼每格讀格號條碼得來源格號 → 換成來源時間 t_src，與輸出格時間差 ≤ 1 格（33.3 ms）全部格成立；丟格處以重複前格或補格（文件寫明），不得整段時間位移。**必要**
2. **A/V 同步**：每秒白閃（畫面）與 click（音訊，事件起點定義同第三輪）時間差 ≤ 1 格（±33.3 ms），全片 10 個點都成立，且第 10 s 的漂移不大於第 1 s 的 +1 格（無累積漂移）。**必要**
3. **PH-ROT → 直立**：輸出 1080×1920（顯示即儲存，PROBE `rotation` side data 不存在或 = 0）；箭頭尖端在畫面上 1/3、紅方塊在左上象限（量色塊質心）。不得雙重旋轉（倒立）或忽略旋轉（橫躺）。**必要**
4. **PH-HDR → SDR BT.709**：PROBE `color_primaries=bt709`、`color_transfer=bt709`（或 `iec61966-2-1` 不接受，必須 bt709）、`pix_fmt=yuv420p`（8-bit）；
   - 灰階條解碼 Y 嚴格單調（11 階 Spearman = 1.0），最暗階 Y ≤ 30、最亮階 Y ≥ 200（不灰濛、不全白）；中間 50% 階 Y 在 [90, 170]。**必要**
   - 色相保持：紅綠藍黃與膚色塊 hue（HSV）與 SDR 圖卡原值差 ≤ 12°，膚色塊飽和度不降超過 40%。**必要**
   - tonemap 演算法（hable／mobius／bt2390）文件寫明；zscale 不可用時的退路寫明（例 `colorspace` + 曲線）並報警告，不得靜默輸出 PQ 當 SDR。**必要**
5. 進件報告（JSON）：每支來源記錄原始 fps 模式（cfr/vfr）、rotation、色彩、轉換動作；出題者比對三支的偵測欄 100% 正確。**必要**
6. 合成測試片產生器入庫（iPhone／Android 樣式），測試離線、只用 ffmpeg lavfi。**必要**（spec 要求）

### S-55 效能與 proxy —— 必要（理由：使用者等不了；proxy 也是 S-62 的前提）
1. `--proxy`：輸出短邊 ≤ 540 px（或文件值），同計畫牆鐘 ≤ 正式版的 35%；proxy 與正式版剪點／事件格號完全一致（manifest 比對）。**必要**
2. benchmark JSON（例 wow/fx/benchmark-5.json）記錄 720p、1080p 各一個 30 s 3 效果計畫的 fps 與 RSS 峰值、機器資訊；出題者重跑 fps 差 ≤ 30%。**必要**
3. 熱點優化後輸出 PSNR ≥ 45 dB vs 優化前（或 sha 相同）。**必要**
4. 1080p 30 s 3 效果正式算繪 ≥ 3 fps（本機 16 GB、CPU only）。**加分**（理由：數字依機器，記錄比達標重要）

---

## P1 最大感知差

### S-56 逐字動畫字幕 —— 必要（理由：競品第 1 名；四輪都沒有）
1. **時間**：SRT-W 逐詞起點 t_w；每詞「首次出現字墨」的格 k_w（字墨定義見共通規則，限該詞 bbox）→ |k_w/30 − t_w| ≤ 1 格；typewriter 樣式以字為單位同樣成立。詞消失（行替換）時間 ≤ 下一行首詞起點 + 1 格。**必要**
2. **來源**：吃使用者 SRT／純文字稿＋時間 JSON（離線、必要）；faster-whisper 為選用依賴：未安裝時要求轉錄 → 報錯並給安裝指令或「改用 --srt」提示（無 traceback）；測試不跑模型（以注入的逐字 JSON 代替）。**必要**
3. **中文斷行**（每行上限 8／12／16 字各跑一次；樣本至少含下列）：
   - 「我們今天要去台北市政府參加開放資料活動，真的嗎？好！」
   - 「他說：「這個『效果』太棒了！」然後……就走了。」
   - 「Version 2.0 在 2026 年 11 月 4 日上線（共 3.14 GB）」
   規則全部成立：(a) 行首不為 `，。、！？；：」』）】》…—％` 等避頭字元；(b) 行尾不為 `「『（【《` 等避尾字元；(c) 文件化詞表中的詞（至少「台北市政府」「開放資料」「效果」）不被拆；(d) 英文單字、數字（`2.0`、`2026`、`3.14`）、`GB` 與前面數字不拆；(e) 每行字數 ≤ 上限（全形 1、半形 0.5 計，或文件化寬度量法以像素為準）；(f) 「……」「——」成對不拆。出題者以字墨列 bbox 切行後與輸入字串對位檢查。**必要**
4. **關鍵字強調**：自動選出的關鍵字（文件化規則，例 名詞／數字／使用者標記）以樣式色呈現：關鍵字 bbox 內樣式色像素（ΔE76 ≤ 10）≥ 字墨 30%；非關鍵字 bbox 內 = 0%。手改：計畫中把關鍵字改為「真的嗎」→ 只有該詞變色。**必要**
5. **安全區**：同 S-52 第 3 條；字幕位置 `bottom`／`center`／`top` 三種皆 100% 在安全區。**必要**
6. **易讀**：BG-HARD 四種背景上，字填色與其外圈（描邊或底框，取字墨外 3 px 環）WCAG 對比 ≥ 4.5:1（每個預設樣式）；字高（大寫／漢字框）≥ 畫面高 3.5%（1920 → ≥ 67 px）；描邊 ≥ 字高 5% 或有底框。**必要**
7. **進場動畫**：pop（縮放峰值 1.1–1.35，≤ 200 ms 回到 1.0 ±2%）、typewriter（可見字數逐格非遞減、每字出現於其時間 ±1 格）、bounce（y 位移有 ≥ 1 次過衝、≤ 400 ms 穩定 ±1 px）。以字墨 bbox 量。**必要**
8. **樣式系統**：欄位（字型、大小、描邊、陰影、底框、關鍵字色、進場、每行字數、位置、安全區）皆可在計畫中覆寫，每欄位一個測試證明有效（改值 → 輸出變化且方向正確）。**必要**
9. **3–4 個預設樣式全部過品質閘門**（process.md：兩位跨廠商評審取較低分 ≥ 4），紀錄檔存在；未過者刪除並列於 fx.md「評估過但未收錄」。**必要**
10. 缺字型（例 CJK 字型不存在）→ 文件化退路或報錯，不得輸出豆腐框（字墨中「□」形狀偵測：每字 bbox 填充率檢查，或列出使用字型路徑）。**必要**
11. 字幕可匯出 SRT／ASS 給平台或剪輯軟體。**加分**

### S-57 音效規則表 —— 必要（理由：競品第 4 名；每個視覺事件有聲音＝專業感）
1. **規則表**（文件一張表）：whoosh→甩鏡／推移（whip_pan、push 類）、hit→閃白／重拍 zoom、pop→字幕／貼紙出現、riser→變速衝拍前（結束於衝拍點）、click→快門（freeze／拍照）。計畫開 `"sfx":"auto"`，每類事件各一個 → 輸出音軌每事件偵測到對應指紋頻率。**必要**
2. **位置**：每個音效事件起點（第三輪定義）與事件時間差 **≤ 10 ms**（whoosh 若文件定義為「峰值對齊」則量峰值，≤ 10 ms）；riser 的「結束／峰值」與衝拍點 ≤ 10 ms。在 30 fps mp4 中音訊仍以樣本精度定位（音訊不跟影格量化）。**必要**
3. **來源優先序**：SFXDIR-U 與 SFXDIR-K 都在 → 全部用 U 的指紋（3.3 kHz…）；拿掉 U → 用 K 的指紋；兩者都拿掉 → 程序合成（指紋不屬於 U、K，且 manifest `source: "procedural"`）。每事件 manifest 記錄 `source`、檔案路徑、授權。**必要**
4. **Kenney**：下載腳本存在（不在測試中執行，付費哨兵／網路哨兵計數 = 0）；repo 不入庫完整包（入庫音檔總數 ≤ 10 且 ≤ 2 MB，附 CC0 授權與署名）。**必要**
5. **舊計畫不加音效**：沒寫 `sfx` 的計畫音軌與第四輪位元相同（或 PCM 相同）。**必要**
6. 音效電平：混音後每個音效峰值比當時配樂 RMS 高 3–12 dB（不被埋、不炸）；整體仍過 S-53 第 1 條。**加分**
7. 同時間多個事件 → 同類只放一個、不同類疊加後 true peak 仍 ≤ −1 dBTP。**加分**

### S-58 節拍分層＋剪點密度 —— 必要（理由：每拍都剪＝業餘；重拍剪、拍上點綴＝專業）
輸入 SONG64（32 小節、下拍每 2000 ms）＋ 8 支素材（第四輪 V-SHARP 等），自動或文件化計畫產生：
1. **剪點只在下拍**：所有剪點（qa_media `--timeline` 或出題者以場景差偵測）到最近 `downbeats_ms` 的距離 ≤ 半格；**節奏客觀分數**（剪點到最近重拍的中位距離）≤ 5 ms，由 qa_media 輸出此欄。**必要**
2. **剪點數區間**（64 s、32 小節；文件須寫明同一套區間，實測須落在內）：low = 每 4 小節 → **6–9** 剪；mid = 每 2 小節 → **13–17** 剪；high = 每 1 小節（chorus 段可 2 拍）→ **28–40** 剪。且 low < mid < high 嚴格成立。**必要**
3. **拍上點綴**：非剪點的拍上有 zoom／閃類事件，事件時間到最近拍 ≤ 半格；high 下每小節非下拍的點綴 ≥ 1 個（chorus 段）。**必要**
4. **段落交界換風格**：SONG64 每個 section 邊界（8、24、40、48、60 s）兩側 2 s 內使用的效果／轉場類型集合 Jaccard ≤ 0.5；邊界必有剪點。**必要**
5. 無下拍資料（beats.json 只有 beats）→ 以每 4 拍推定並在 manifest 記錄「推定」；不崩潰。**必要**
6. `cut_density` 未知值 → 報錯列 low|mid|high。**必要**

### S-59 音樂裁長 —— 必要（理由：使用者常有 60 s 歌要做 15/30 s 片）
1. `SONG64 --target 30 --candidates 3`：產出 3 個候選；每個長度與 30 s 差 ≤ **1 小節（2000 ms）**；3 個候選的接點集合兩兩不同。**必要**
2. **接點在小節邊界**：每個接點（manifest 記錄來源時間 in/out）與 `downbeats_ms` 距離 ≤ 10 ms；接點兩側段落標記合理（例 不從 intro 中段接到 chorus 中段；文件化規則）。**必要**
3. **無爆音**：接點 ±20 ms 內相鄰樣本差 |x[n]−x[n−1]| 最大值 ≤ 該歌全曲相鄰樣本差 99.9 百分位 ×1.5；接點 ±10 ms 的 8 kHz 以上能量 ≤ 前後 200 ms 平均 + 6 dB。交叉淡化長度文件寫明（例 10–50 ms）。**必要**
4. **結尾**：淡出版最後 50 ms RMS ≤ −40 dBFS；或「接 outro」版結尾為 SONG64 的 outro 段（頻譜指紋比對）。**必要**
5. 候選清單含 `in/out` 接點、段落、長度、預覽 wav；HTML 或文字表標示接點時間。**必要**
6. **無音樂版**：輸出不含音軌（或靜音軌，文件寫明）的 mp4 ＋ 拍點標記檔（JSON 與 SRT／CSV 任一，含下拍時間）；拍點標記與原計畫 beats 一致 ±1 ms。**必要**（理由：授權音樂只能在平台上加）
7. 依小節裁長後 beats.json 同步改寫（接點後拍點平移正確），S-58 在裁後歌上仍剪在下拍。**必要**

### S-60 具名運鏡詞彙 —— 必要（理由：agent 用名字叫用才穩定）
1. **表**：文件一張表，至少 crash_in、crash_out、expo_in、smooth_in、whip、punch，每列：縮放／平移目標、時長預設、緩動名、用途。計畫以 `{"move":"crash_in"}` 叫用；未知名稱 → 報錯列有效值。**必要**
2. **量測**（CHART 上，30 fps，以同心圓半徑擬合得每格縮放 s(k)、以十字中心得平移）：
   - crash_in：≤ 3 格內達到目標縮放的 90%；crash_out 反向同。**必要**
   - expo_in：s(k) 正規化曲線與 Penner `easeInExpo` 參考 ≤ 0.03 最大誤差（全程）。**必要**
   - smooth_in：s(k) 單調、最大速度出現在時長 40–60% 處、首末格速度 ≤ 最大速度 15%。**必要**
   - whip：平移峰值速度 ≥ 畫面寬 / 4 每格，且有方向性運動模糊（垂直於運動方向的邊仍銳利）；punch：縮放峰值後 ≤ 6 格回到 1.0 ±1%。**必要**
3. **緩動函數**：每個 Penner 函數在 t ∈ {0, 0.01, …, 1}（101 點）與獨立參考實作（出題者寫）最大絕對誤差 ≤ 1e-9；f(0)=0、f(1)=1 精確；檔頭有 Robert Penner BSD 授權與署名，THIRD_PARTY 有條目。**必要**
4. **spring**（自寫）：參數（stiffness、damping、mass 或文件化等價）→ 過衝量與穩定時間符合解析解 ±2%；臨界阻尼時無過衝（≤ 0.1%）。**必要**
5. 運鏡可配 `anchor:"subject"`（第三輪 S-26 量法，質心 ±2 px）。**加分**

### S-61 9:16 主體重構圖 —— 必要（理由：一次錯就毀片）
沿用第四輪 acceptance-4.md S-41 第 1、2、3、5、6 條全部數字：V-WALK → 9:16，主體 bbox 完整在框內 ≥ 98% 格、出框面積 ≤ 10%；框中心相鄰位移 ≤ 12 px、加速度 ≤ 4 px/格²、> 8 px 跳動 ≤ 2 次；頭頂留白 ≥ 主體高 10%（≥ 95% 格）；無主體退回並記錄；字幕 100% 在安全區且與主體重疊 ≤ 2%。另加：與 `--platform tiktok` 合用時輸出 PROBE = 1080×1920、30 fps，上述量測換算到輸出座標後同樣成立。**必要**

### S-62 先預覽後算繪 —— 必要（理由：使用者在 proxy 上選，贏家才花時間算）
1. `--review-html`（或文件化）：產出離線 HTML（`grep -E "https?://"` 於 html/css/js = 0，除註解）；每個事件一張縮圖（`<img>` 數 = manifest 事件數，每張檔案存在、取自事件格 ±1 格）；每鏡有「保留／換掉」控制，結果存成文件化 JSON（例 `decisions.json`）。**必要**
2. **只重算改到的鏡頭**：8 鏡計畫，決定檔把第 3、6 鏡標「換掉」（並給替代素材或效果）→ 重算鏡數 = 2（log／manifest 計數器）；其餘 6 鏡 frames sha256 逐格與前次相同；第 3、6 鏡有變化（MAD ≥ 4/255）；牆鐘 ≤ 全片重算的 50%。**必要**
3. 換掉一鏡改變了長度 → 後續鏡頭時間平移、剪點仍在拍（S-58 第 1 條）且只有時間平移不重算像素（若需重算則文件寫明理由）。**加分**
4. HTML 在 Chrome 開啟無 console error（出題者手動或 Playwright）。**加分**

---

## P2 效果庫擴充

### S-63 gl-transitions 移植 —— 必要（理由：效果多但每個都好；授權必須乾淨）
對**每一個**移植轉場（目標 30–40 個）自動跑，任何一個不過即不收（不得只抽樣）：
1. **端點恆等**：A = 640×360 RGBA 程序紋理（seed 1）、B = 另一紋理（seed 2），不透明；`transition(A,B,0,ctx)` 與 A 最大差 ≤ 1/255，`p=1` 與 B ≤ 1/255。**必要**
2. **alpha**：A、B 為含透明區的 RGBA（中央不透明圓、外圍 alpha=0，透明處 RGB 填亂數垃圾值）→ 任一 p ∈ {0.25,0.5,0.75}：輸出在兩者 alpha 皆 0 處 alpha = 0；透明處的垃圾 RGB 不出現在輸出（輸出 alpha>0 像素的預乘 RGB 中，與垃圾色 ΔE ≤ 5 的像素 ≤ 0.1%）；不透明輸入 → 輸出 alpha 全 255。**必要**
3. **決定性**：同輸入兩次 sha256 相同；含亂數者以 `ctx.seed` 決定，換 seed 有變化。**必要**
4. **非正方畫布**：1080×1920 與 1920×1080 上 p=0.5 不崩潰、無拉伸（以圓形圖案量長短軸比 1 ±3%，對以 ratio 參數化的原著轉場同樣要求）。**必要**
5. **單調性**：p 取 0..1 共 21 點，輸出與 B 的 MAD 序列 Spearman ≤ −0.8（明確文件化為非單調的轉場除外，列名單）。**必要**
6. **署名**：每個移植檔頭含原轉場名、原作者、原授權（MIT／BSD…）與 gl-transitions 原始檔路徑或 commit；THIRD_PARTY（或 NOTICE）每位作者一條；出題者以 gl-transitions 官方清單比對作者名 100% 一致（抽 10 個人工核對 + 腳本全查欄位存在）。**必要**
7. **參照一致**：若環境有 moderngl／OpenGL 可跑原 GLSL，p ∈ {0.25,0.5,0.75} PSNR ≥ 35 dB；無環境則以文件化手推公式的單元測試替代。**加分**
8. 清單：其餘未移植轉場列表（名、作者、未移植理由）。**必要**
9. 選用 ffmpeg `xfade` 快速路徑：同名轉場 p=0.5 與 numpy 版 PSNR ≥ 30 dB，或文件寫明差異；預設關閉。**無感**（理由：只影響長片速度，觀眾看不出）
10. 全部過品質閘門（S-64 同規則）；未過者不在 `--list`。**必要**

### S-64 第二輪效果品質閘門 —— 必要（理由：「不夠好的不要」是使用者原話）
1. **每個效果一份閘門紀錄**（JSON 或 md，路徑文件化）：自動檢查結果（alpha、接縫、flicker、黑格、決定性、720p 單格毫秒）、兩位評審 id（跨廠商）、各自分數與理由、取較低分、決定（stable／重做一次後的結果／刪除）、日期、commit。第一～五輪所有 stable 效果與轉場（含字幕預設樣式、gl 移植）都有紀錄，覆蓋率 100%。**必要**
2. stable ⇔ 較低分 ≥ 4（出題者以紀錄重算，100% 一致）；分數 3 有且只有一次重做紀錄。**必要**
3. 刪除的效果：不在 registry、`--list`、文件主表；在 fx.md「評估過但未收錄」並附理由；舊計畫引用被刪效果 → 報錯並建議替代（不得靜默略過）。**必要**
4. 評審看的小片（2 種素材 × 2 s）與縮圖表存在且可重算。**加分**

---

## P3 導演（簡）
- 鏡頭卡（技術／美感兩欄、可量測欄位逐位元可重現）、處理方案＋分鏡表、lint（只收可量測規則，每條正反例）、風格包 3 個（定格摳像卡點、電影感、Vlog 輕快）、預設 2 個 proxy 版本＋使用者選、導演報告——沿用第四輪 S-36..S-46 對應條目的數字（版本差異 ≥ 2 項、盲評雙順序）。**必要**
- **OpenTimelineIO／FCPXML 匯出**：`otio` 可被 `opentimelineio` 讀回，剪點與 manifest ±1 格、片段來源路徑存在；FCPXML 通過 DTD／schema 驗證並在 Resolve 或 Premiere 匯入（人工抽查 1 次，截圖存證）。**加分**（理由：專業使用者驚豔；一般使用者無感）

## P4 進階（簡）
- 動態摳像時間平滑（光流帶遮罩）：SM 類移動主體 alpha 邊緣逐格閃爍（邊界帶 alpha 時間標準差）比逐格版降 ≥ 40%，主體 IoU 不降 > 1%。**加分**
- SAM 2.1 tiny、Video Depth Anything Small：選用、下載器只允許可商用名稱、無權重時報錯清楚。**加分**
- 模板轉移、All-In-One 段落：延後，不驗收。**無感**（本輪）

## 評估修正 —— 必要
1. 盲評雙順序、n 依 `wow-judge panel init` 檢定力，紀錄存在。**必要**
2. **使用者抽查**：本輪 3–5 個小片的使用者選擇與評審選擇並列；一致率 = 一致數／抽查數；< 70% → 該輪評審結論標「不作數」並在 progress.md 寫明。**必要**
3. qa_media 輸出節奏客觀分數欄（剪點到最近重拍的中位距離，ms）。**必要**
4. 測試集：≥ 10 個真實或擬真手機素材專案（擬真 = 本卷 PH-* 類生成器的變體），每個記錄算繪時間與峰值 RSS（RSS 量法）。**必要**（10 個）；20 個 **加分**。

## 測試與不退步 —— 必要
- `python -m unittest discover -s tests`：failure 0；新測試覆蓋 S-50（小尺寸串流 RSS 與片長無關）、S-51（量化表）、S-52（PROBE 欄）、S-53（EBU）、S-54（三支 PH-*）、S-56（斷行規則每條正反例）、S-57（優先序）、S-58（區間）、S-59（接點無爆音）、S-60（緩動 101 點）、S-62（重算鏡數）、S-63（每個移植轉場的 1–5 條，參數化）。需 ffmpeg 的測試在無 ffmpeg 時 skip 並寫明理由，其他不得 skip；測試數多於第四輪結束時。
- 共通規則的舊計畫 sha 對照通過；`grep -nE "for (y|x|row|col|px) in range" scripts/fx/` 仍無逐像素迴圈（gl 移植須向量化）。
