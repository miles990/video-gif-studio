# 答案卷 第三輪 — 主體感知、音效層、音樂結構、自動草稿、模板轉移、LUT、快速預覽、運動模糊（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-3.md（S-25..S-35、S-展示3）、第一輪 wow/fx/acceptance.md、第二輪 wow/fx/acceptance-2.md（格式、SYN 素材、共通規則）、
scripts/fx/core.py（`Context` 現有欄位：width/height/fps/beats_ms/downbeats_ms/t_ms/segment/seed/audio/sampling/history…）、
scripts/fx_render.py（`plan --out --formats --fx-dir --list --preview --validate --interpolate`）、scripts/fx_reverse.py（`source --out --beats --fps`，產出 `draft-plan.json`）、
scripts/music_sync.py（`music --out --bpm --offset-ms --engine rms|beat_this`，寫 `beats.json`：`beats_ms`、`onsets_ms`、選用 `downbeats_ms`）、
scripts/qa_media.py（`input --out --fps --loop --holds --expect-cuts --timeline`；音訊檢查 `loudness`／`true_peak`（≤ −1 dBTP FAIL 門檻）／`loudest_100ms`／`silence`）。出題者 2026-11-04 查得。
每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條）。
欄位名、新 CLI 名以建造者文件為準；本卷用 spec 用語（`anchor`、`follow`、`subject_reveal`、`match_cut`、`sfx`、`sections`、`drops_ms`、`on:"drop"`、`section`、`fx_autoplan.py`、`lut`、`--proxy`、`motion_blur`），改名須在 fx.md 寫明對應。

## 共通規則（第一、二輪全部沿用，另加）
- 技能 venv（有 cv2、無 onnxruntime）、ffmpeg 經 `VIDEO_GIF_FFMPEG`、「格時間」、亮度 Y、「報錯」定義（非 0、無 traceback、不建 `--out`、像素算繪前、牆鐘 < 3 s）、不得改 examples/、不得改本答案卷、離線測試不下載／不讀真實權重。
- 「主體質心（量測）」= 本卷以**顏色門檻**從輸出像素量得（不信任建造者 sidecar），例：S 的主體色 (240,200,40) 各通道 ±30 的像素集合的質心。
- 「1 拍」以該曲 beats.json 的相鄰拍間距計（120 BPM = 500 ms）；「±1 格」= 計畫 fps（預設 25 → 40 ms）。
- 音訊量測：48 kHz、float；STFT 窗 2048、hop 256、Hann；「頻譜質心」= Σf·|X|²/Σ|X|²；「事件起點」= 包絡（5 ms RMS）首次超過該事件峰值 −20 dB 的時刻。
- 舊計畫不退步：沒有寫任何第三輪鍵的第一、二輪計畫（P-base、P-ramp、demo2/plan.json）→ frames **sha256 逐格相同**於第三輪前（以 `main`／第二輪結束 commit 對照）。音軌若因「預設音效」而改變，必須是文件寫明的行為（例：預設關閉，或 `"sfx":"auto"` 才開）——**本卷要求舊計畫預設不自動加音效**（使用者舊片重算不應突然多出聲音）。

## 合成素材（第一、二輪 A、B、C、T、M、G、P、beats.json、syn.wav 照用；以下新增）
| 代號 | 內容 | 用途 |
|---|---|---|
| S（偏心主體） | 50 格 × 40 ms，320×180 不透明；背景 16 px 棋盤 (90,90,90)/(130,130,130)；主體 = 實心圓 半徑 24、色 (240,200,40)、圓心 (220,60) 靜止；附遮罩序列 `S/masks/00000.png…`（圓內 255、外 0） | anchor、subject_reveal 的 a 鏡 |
| SM（移動主體） | 同 S，但圓心 x = 60+4i、y = 90（i = 格號，每格 4 px 往右），附遮罩 | text follow、追蹤資料 |
| S2（第二鏡主體） | 50 格 × 40 ms；背景 (40,60,220) 加 24 px 白格線；主體 = 實心圓 半徑 36、色 (60,220,90)、圓心 (100,110)；附遮罩 | match_cut 的 b 鏡（質心、大小都不同） |
| QBD.wav（安靜→漸強→爆點） | 48 kHz mono、16.000 s、120 BPM、拍在 0,500,…,15500。0–4 s：每拍 1 kHz 20 ms click 振幅 0.05；4–8 s：click + 白噪振幅 0.02→0.35 線性上升、噪聲高通截止 200→4000 Hz 上升；**8.000 s 起爆點**到 14 s：每拍 55 Hz 正弦 kick（120 ms 指數衰減，振幅 0.9）+ 寬頻噪聲 0.3 + 每半拍 hi-hat；14–16 s：只剩 click 振幅 0.08 | 段落／drop、自動草稿 |
| QBD-beats | `music_sync.py QBD.wav --out D/qbd --bpm 120 --offset-ms 0` 產生；另一份手寫 `downbeats_ms` = 每 4 拍（0,2000,4000,…） | 重拍判定 |
| FLAT.wav | 16 s、120 BPM、全程同振幅 click+kick（無能量變化） | 無 drop 對照 |
| B2.wav（另一首） | 48 kHz、18.000 s、**100 BPM**（拍距 600 ms、首拍 300 ms）、結構同 QBD：intro 0.3–4.5 s、build 4.5–9.3 s、drop 9.3 s 起到 15.3 s、outro | 模板轉移目標曲 |
| P-T（參考計畫） | 依 QBD-beats 寫的計畫：段落剪點在拍 4、8、12、16、20、24；事件：拍 2 `zoom_punch`、拍 8 `shake`、拍 15 `whip_pan` 轉場、拍 16（drop）`flash_white`＋`hex_shutter`、拍 20 `rgb_split`、拍 28 `film_grain` 收尾 | 模板轉移來源 |
| L-id／L-swap／L-known | `.cube`：3D 恆等 size 17；3D 通道輪換 size 33（out = (g,b,r)）；3D 非線性 size 17：out = (r², √g, 0.5+0.5·sin(2πb)·0.5)；另 1D 恆等 size 1024 與 1D gamma（x^(1/2.2)）size 256 | LUT |

基準指令（名稱以建造者為準）：
```
python scripts/fx_render.py D/plan.json --out D/out --formats png wav mp4
python scripts/music_sync.py D/QBD.wav --out D/qbd
python scripts/fx_autoplan.py --footage D/A D/B D/S D/S2 --music D/QBD.wav --out D/auto
python scripts/fx_reverse.py <ref.mp4> --out D/rev --beats <ref beats.json>   # 再以文件化方式「換素材＋換音樂」
python scripts/qa_media.py D/out/out.mp4 --out D/qa
```

---

## S-25 主體追蹤資料 —— 必要（S-26、S-27 全部依賴它）
1. 對 SM 產生 sidecar（文件化指令或算繪時自動）：每格有 bbox、centroid、area（及遮罩路徑或內嵌）。量：centroid = (60+4i, 90) ±0.5 px；bbox = [x−24, y−24, x+24, y+24] ±1 px；area = π·24² ±3%。**必要**
2. 來源：可吃既有遮罩序列（本卷 S/masks）與透明素材的 alpha（對 C：centroid (160,90) ±0.5、bbox ≈ 橢圓外框 ±3 px 含柔邊）。`background_remove`／BiRefNet 快取路徑文件寫明；離線測試用注入遮罩，不跑模型。**必要**
3. 可手改：把 sidecar 第 10 格 centroid 手改成 (100,40) → 第 10 格的 anchor 效果以 (100,40) 為中心（量測同 S-26），其他格不變。**必要**（spec「可手改」）
4. 可快取：第二次算繪不重算遮罩（log 或計數器可證；牆鐘第二次 ≤ 第一次 50%，或文件化的快取命中紀錄）；改遮罩任一像素 → 失效重算。**加分**
5. ctx：效果函數可讀 `ctx.subject`（bbox、centroid、mask）；fx-dir 自訂效果記錄收到的 centroid 與 sidecar 逐格相同。**必要**
6. 沒有主體資料時 anchor 退回畫面中心 (160,90)，manifest 該事件記錄 fallback 與原因字串；不崩潰、不默默用上一段的主體。**必要**

## S-26 anchor／follow —— 必要（「效果跟著主體走」是本輪第一件事）
**anchor**（輸入 S，主體在 (220,60)）：
| 效果 | 計畫 | 預期 |
|---|---|---|
| zoom_punch（scale 峰值 1.3，取峰值格） | `anchor:"subject"` | 主體質心（量測）= (220,60) ±2 px；主體半徑（面積反推）= 24×1.3 ±5% |
| zoom_punch 同上 | 預設（畫面中心） | 主體質心 = (160+1.3·60, 90−1.3·30) = (238,51) ±2 px——兩者差 ≥ 15 px，證明 anchor 真的改變了中心 |
| beat_bounce（拍上峰值格） | `anchor:"subject"` | 同 zoom：質心 ±2 px 不動 |
| radial_blur（強度 1） | `anchor:"subject"` | 以 (220,60) 為中心 3×3 區差 ≤ 2/255；以 (220,60) 為圓心 r∈[50,70] 環帶切向方向的棋盤邊仍銳利、徑向被拉長（同第二輪方向性量法換中心）；以 (160,90) 為中心的 3×3 區**有**變化（MAD ≥ 4/255） |
| shake（含旋轉分量，若文件說 shake 無旋轉則量縮放分量） | `anchor:"subject"` | 旋轉／縮放的樞軸 = 主體質心：主體質心位移 ≤ 平移分量 +1 px；文件寫明 shake 的 anchor 語意 |
| 2.5D 推鏡（第二輪 parallax，假深度引擎） | `anchor:"subject"` | 推鏡縮放中心 = 主體質心 ±3 px |
- 邊緣：anchor 在 (220,60) 放大 1.3 → 輸出不新增純黑／透明像素（不透明輸入 alpha 全 255、Y<5 的新增像素 ≤ 0.5%）；文件寫明「中心靠邊時夾到可裁範圍」或「延伸補邊」。**必要**
- anchor 隨格更新（SM 上 zoom_punch 持續 10 格）：每格量測質心 = 該格主體位置 ±2 px（不是只取第一格）。**必要**
- `anchor` 未知值（如 `"subjct"`）→ 報錯含有效值列表。**必要**

**follow**（SM 上 `text` 「測試」96 px、`follow:"subject"`，全 50 格）：
1. 每格字墨（alpha>0.5 或與無字版差 >16/255 的像素）與主體遮罩重疊 ≤ 字墨面積的 2%。**必要**
2. 字墨 ≥ 98% 在畫面內（不出框）。**必要**
3. 真的在跟：字墨 bbox 與主體 bbox 最近距離 ≤ 48 px（每格）；字中心 x 與主體 x 的相關係數 ≥ 0.9。**必要**
4. 不抖：相鄰格字中心位移 ≤ 主體位移（4 px）+ 2 px；切換放置側（上→下等）時文件寫明是否有過渡，且一段內換邊 ≤ 2 次。**加分**
5. 貼紙（若有貼紙效果）同規則。**加分**

## S-27 主體轉場 —— 必要（短影音最紅的兩種，spec 點名）
共通：p=0 → ≈a、p=1 → ≈b（MAE ≤ 1/255）；同參數兩次逐位元相同；`--list` 有參數與說明；不透明輸入輸出 alpha 全 255。
**subject_reveal**（a = S[0]，b = B[0]，柔邊 0；p 取 0,0.05,…,1）：
1. b 覆蓋率（定義同第二輪 S-19）對 p 單調不減（容差 0.5%）。**必要**
2. 從剪影長出來：最早出現 b 的 p（覆蓋率首次 > 0.5%）時，b 像素 ≥ 95% 落在 a 主體遮罩膨脹 2 px 內。**必要**
3. 擴張次序：每個像素被揭露的 p 與它到主體遮罩的距離之 Spearman ρ ≥ 0.9（越遠越晚）。**必要**
4. 剪影的形狀是主體而不是圓：改用方形主體（S 的圓換 48×48 方塊）時，p 首次揭露那格的 b 區域與方形遮罩 IoU ≥ 0.8。**必要**（否則只是 circle wipe 換了中心）
5. 沒有主體資料時：報錯或退回文件寫明的形狀轉場，manifest 記錄。**必要**

**match_cut**（a = S，b = S2；硬切模式，以及短溶接模式 duration 200 ms）：
1. 剪點後第一個 b 格：b 主體質心（量測，綠色 (60,220,90) ±30）= a 主體質心 (220,60) ±3 px；b 主體半徑 = 24 ±5%（縮放 = 24/36 對齊大小）。**必要**
2. 縮小 b 造成的空白不得露黑／透明：不透明輸出 Y<5 的新增像素 ≤ 0.5%（填法文件寫明：模糊延伸、鏡像、或改以放大 a 側對齊等）。**必要**
3. 之後回到 b 的自然構圖（若文件設計會「放開」）：放開時間 = 文件值 ±1 格，質心軌跡單調、無跳格（相鄰格質心位移 ≤ 總位移/放開格數 ×2）。**加分**
4. 硬切：剪點前一格 = a 原格逐位元；溶接：中點格兩主體質心重合 ±3 px（疊影只有一個圓心）。**必要**
5. 剪點時間仍在計畫拍點 ±0（10 ms 規則），總長不變。**必要**

## S-28 程序合成音效層 —— 必要（「聲音跟著畫面」是本輪第二件事）；使用者音效檔：必要；ducking：加分
以文件化方式單獨輸出每種音效為 wav（或算繪 `--formats wav` 只含音效軌），48 kHz：
| 音效 | 預期 |
|---|---|
| whoosh | 時長 = 參數 ±10 ms；主動區（包絡 > 峰值 −30 dB）內頻譜質心逐窗序列與時間的 Spearman |ρ| ≥ 0.8（掃頻），最大／最小質心比 ≥ 2；頻譜平坦度中位數 ≥ 0.2（是噪聲而不是純音） |
| hit／impact | ≥ 70% 能量在 < 200 Hz；包絡峰值在起點後 ≤ 15 ms；峰值後 ≤ 1 s（或文件參數）降到 −40 dB |
| riser | 主動區質心（或基頻）單調上升 ρ ≥ 0.8；RMS 後 25% 平均 ≥ 前 25% 的 2 倍（+6 dB）；**結束點**（包絡峰）= 目標時間（下一個事件）±10 ms |
| shutter／click | 時長 ≤ 80 ms；≥ 60% 能量 > 1 kHz；可有 2 個瞬態（開合） |
| glitch | 同 seed 逐 sample 相同、不同 seed 相關係數 < 0.9；含 ≥ 3 個能量突變（相鄰 10 ms RMS 比 ≥ 6 dB） |
- 零授權：全部 numpy 合成；`git ls-files | grep -iE "\.(wav|mp3|flac|ogg|aiff)$"` 不得新增第三方音檔（測試夾具若有，須是程式產生並註明）。**必要**
- 對位：P-base 加 `sfx` 預設（whip_pan→whoosh、flash_white→hit、hex_shutter→shutter）後，每個音效事件起點（hit 用包絡峰）落在 manifest 該視覺事件時間 ±10 ms。**必要**
- 計畫控制：關閉（`"sfx":false` 或文件化）→ 音軌與無 sfx 版逐 sample 相同；替換（指定另一種）→ 頻譜特徵符合新類型；音量 −6 dB → 該事件 RMS 比 = 0.501 ±5%。**必要**
- 使用者自己的音效檔（wav 44.1k stereo 也要吃，重採樣）：起點對位 ±10 ms；不存在 → 報錯含路徑。**必要**
- 混音：成片 mp4 經 `qa_media.py` → `true_peak` PASS（≤ −1 dBTP）；配樂本身已到 −0.5 dBTP 時也要 ≤ −1（限幅／增益由混音器負責）。**必要**
- ducking（啟用時）：音效主動期間配樂 RMS 下降 ≥ 3 dB，音效結束後 ≤ 300 ms 恢復到原值 ±1 dB；未啟用時配樂逐 sample 不變（除整體限幅外，文件寫明）。**加分**
- 決定性：同計畫兩次算繪音軌 sha256 相同。**必要**

## S-29 音樂結構 —— 必要（「大動作落在高潮」需要先知道高潮在哪）
1. `music_sync.py QBD.wav --out D/qbd`：beats.json 新增 `sections`（每項至少 label∈{intro,build,drop,outro}（或文件化集合）、start_ms、end_ms，首尾相接覆蓋 0..duration、無重疊）與 `drops_ms`。既有鍵 `beats_ms`／`onsets_ms`／`bpm`／`offset_ms` 與第三輪前**數值相同**。**必要**
2. drop：`drops_ms` 中與 8000 最近者 |Δ| ≤ 500 ms（±1 拍），且吸附在 beats_ms 上（±10 ms）；不得有另一個 drop 落在 0–7000 ms（安靜段／漸強段誤報）。**必要**
3. 段落：含 8000 ms 的段 label = drop；含 2000 ms 的段 = intro；含 6000 ms 的段 = build；含 15000 ms 的段 = outro。邊界 4000／8000／14000 各 ±1 拍。drop 必要，其餘三個邊界 **加分**（合成曲夠清楚，但段落命名本來就有主觀性）。
4. 計畫語法：`{"on":"drop"}` 解析為 drops_ms[0]（第一個；文件寫明多個時如何選，如 `drop_index`）；`"section":"build"` 解析為 [build.start, build.end)；manifest 記錄解析後的 ms。拼錯（`"section":"bild"`）→ 報錯含可用段名。**必要**
5. 手改優先：手改 beats.json 的 `drops_ms` 為 [10000] → 計畫 `on:"drop"` 事件落在 10000 ±0（不重新偵測覆寫使用者）。**必要**
6. `--engine beat_this`（假引擎注入 downbeats 每 4 拍）時，段落邊界吸附到 downbeats ±10 ms。**加分**
7. 波形圖：PNG，標出各段（色帶＋文字標籤）與 drop 線；drop 線 x 位置 = 8000 ms 對應像素 ±1%寬。**加分**
8. 離線：rms 引擎下不需任何選用模型；16 s 音檔分析牆鐘 ≤ 5 s。**必要**

## S-30 自動草稿 —— 必要（本輪的「驚豔」入口：一行指令出第一版）
指令：`python scripts/fx_autoplan.py --footage D/A D/B D/S D/S2 --music D/QBD.wav --out D/auto`。
1. 產出 plan.json，`fx_render.py D/auto/plan.json --validate` 通過，且可直接算繪成片（mp4 含音樂）。**必要**
2. 剪點落在重拍：每個段落邊界 ∈ downbeats（有 downbeats_ms 時用它；沒有時用文件寫明的規則，例：每 4 拍自 offset 起）±10 ms。**必要**
3. drop 最重：轉場依文件「重量」排序（fx.md 有表），最重的轉場時間在 drop ±1 拍（500 ms）；drop ±1 拍內有 flash 類（flash_white／invert_flash／black_flash）。**必要**
4. build：build 段內有 riser（音效），其結束點 = drop ±10 ms；build 最後 1 拍前有變速（ramp／speed<1 進拍）或文件化的「拍前」動作。**必要**
5. 密度弧線：每秒效果＋轉場事件數 intro < build < drop（嚴格）；outro < drop。**必要**
6. 每個決定（段落、效果、轉場、音效）有非空 `reason`（或文件化等名），引用段落名或拍號（regex `intro|build|drop|outro|beat|拍` 命中）；無理由的決定 = 0。**必要**
7. 決定性：同輸入兩次 plan.json 位元相同（或只差文件寫明的時間戳欄）。**必要**
8. 素材使用：每個輸入素材至少用到一次（4 個素材 ≥ 4 段）；不重複同一素材連續兩段（素材數 ≥ 2 時）。**加分**
9. 有主體資料的素材（S、S2）之間優先用主體轉場（subject_reveal／match_cut）並在 reason 說明。**加分**
10. 牆鐘（不含算繪，16 s 音樂、4 素材）≤ 10 s。**加分**

## S-31 模板轉移 —— 必要（「套用別人的節奏」是本輪第四件事）
來回測：P-T（QBD 120 BPM）→ 以文件化指令換成 B2.wav（100 BPM）＋素材 S、S2、A、B。
1. 事件類型序列（依時間排序的名稱列表）與 P-T 完全相同。**必要**
2. 相對節拍位置保留：每個事件在新曲的拍索引 = P-T 的拍索引（以各自首拍為 0），或以段落為單位映射（文件寫明其一）；以段落映射時，事件相對所屬段落起點的拍數相同 ±0。**必要**
3. 每個事件與剪點時間 ∈ B2 的 beats_ms ±1 格（40 ms）。**必要**
4. 段落：P-T 的 drop 事件（拍 16 的 flash_white＋hex_shutter）落在 B2 的 drop（9300 ms）±1 拍（600 ms）。**必要**
5. 反向來回：把轉好的 B2 計畫再轉回 QBD → 事件時間與 P-T 原時間逐一相同 ±1 格。**必要**
6. 從真實參考片：`fx_reverse.py` 拆 demo2 成片 → draft → 轉到 B2：draft 中被偵測到的剪點／事件全部帶過去（數量相同，或被丟棄者在報告中逐一列出理由）。**必要**
7. 不搬運：轉移後計畫中所有 `manifest`／`file`／`music` 路徑都只指向使用者給的素材與音樂（grep 參考片路徑 = 0 筆）；fx.md／README 寫明「只轉移結構，不搬運他人畫面、音樂、肖像」。**必要**
8. 新曲比參考片短：結尾超出部分依文件「截斷並報告」或「壓縮最後一段」，報告列出被截掉的事件。**必要**（詳細邊界見另卷）

## S-32 LUT 調色 —— 必要（調色標準做法）；內建程序 LUT：必要；效能：加分
輸入：G（漸層）、A[0]、隨機 RGB 圖 256×256（seed 0，uint8）、C（透明）。
1. L-id（3D size 17）、1D 恆等 size 1024 → uint8 輸出與輸入**位元相同**（float 路徑 MAE ≤ 0.5/255 且量化回 uint8 後相同）。**必要**
2. L-swap（size 33）→ 輸出 = (g,b,r) ±1/255（三線性對線性函數應精確）。**必要**
3. L-known（非線性 size 17）→ 與出題者參考實作（scipy `RegularGridInterpolator` 線性，或獨立 numpy 三線性）逐像素差 ≤ 1/255。**必要**
4. 1D gamma size 256 → 與 1D 線性插值參考差 ≤ 1/255。**必要**
5. 強度：`amount:0` = 輸入（MAE 0）；`0.5` = 輸入與全強度的中點 ±1/255；吃拍包絡。**必要**
6. alpha 逐像素不變；C 的 alpha=0 隱藏 RGB 不影響輸出可見部分。**必要**
7. `.cube` 格式：容忍 `#` 註解、`TITLE`、空行、CRLF、`DOMAIN_MIN/MAX`；資料行數 ≠ size³（或 size）→ 報錯含期望與實際行數。**必要**
8. 附 2–3 個程序產生的 LUT（產生程式入庫、`.cube` 由程式產生或入庫但標頭註明 procedural）；`git ls-files "*.cube"` 只含這些；THIRD_PARTY.md 寫明不散布第三方 LUT。**必要**
9. 向量化：`grep -nE "for (y|x|row|col|px|r|g|b) in range" ` LUT 模組無逐像素迴圈；1280×720 size 33 單格中位數 ≤ 80 ms（記入 fx.md）。**加分**

## S-33 快速預覽 —— 必要（「say yes or no 在幾秒內」）
基準：demo2/plan.json（或 1280×720、≥ 10 s、含 ≥ 8 事件的合成計畫，文件寫明）。
1. `--proxy` 牆鐘 × 3 ≤ 正式算繪牆鐘（各量 3 次取中位數；同機、暖快取）；比值記入 fx.md。**必要**
2. 解析度 = 文件比例（例 1/3）±1 px；時間軸相同：格數、`durations_ms` 總和、剪點 ms 與正式版**相同**。**必要**
3. 事件縮圖頁（HTML 或 PNG）：縮圖數 = manifest 中效果＋轉場事件數（每個一張）；每張標名稱與時間（ms 或拍號）；HTML 中圖片相對路徑都存在。**必要**
4. 跳過選用模型：在無 onnxruntime 環境、計畫含 parallax／rife 時 proxy 仍完成，該事件縮圖標「proxy: skipped <原因>」，manifest 記錄；正式算繪同情況仍依第二輪規則報錯。**必要**
5. proxy 不汙染正式：proxy 後再正式算繪，frames sha256 = 從未跑過 proxy 的正式算繪。**必要**
6. 牆鐘：demo2 proxy ≤ 15 s。**加分**

## S-34 幾何運動模糊 —— 加分（避免頻閃是專業感，但沒有也能交片）；開關與決定性：必要
輸入 A（白直條），shake（seed 7）或 push 轉場，`motion_blur: 8`（子格取樣數）。
1. `motion_blur` 未寫或 `0`／`1` → 與第三輪前 frames sha256 相同。**必要**
2. 高速格（直條相鄰格位移 ≥ 8 px 的格）：直條邊緣 10%–90% 過渡寬度 ≥ 位移 × 0.5（無模糊時 ≤ 2 px）；邊緣最大水平梯度下降 ≥ 30%。**加分**
3. 「跳動」量：直條亮度質心的相鄰格位移序列不變（±1 px，模糊不改變運動本身）；而每格「直條最亮欄的 Y 峰值」在高速格下降、靜止格不變（靜止格與無模糊 MAE ≤ 1/255）。**加分**
4. 決定性：兩次 sha256 相同；n=8 耗時 ≤ n=0 的 8.5 倍（只多做取樣，不爆炸）。**必要**
5. 非幾何效果宣告 `motion_blur` → 報錯或文件寫明忽略並 stderr 警告。**必要**

## S-35 測試 —— 必要
- 新離線測試至少斷言：S-25 sidecar 值、S-26 anchor 質心不動 vs 中心縮放質心移動、follow 重疊 ≤ 2%、S-27 reveal 單調與起點在剪影、match_cut 質心／縮放、S-28 每種音效頻譜／包絡特徵與 ±10 ms 對位與 true peak、S-29 合成 QBD 的 drop ±1 拍、S-30 剪點在重拍＋最重轉場在 drop＋reason 非空、S-31 來回測、S-32 恆等／已知 LUT、S-33 proxy 時間軸相同、S-34 開關。
- `python -m unittest discover -s tests`（技能 venv、無 onnxruntime、無 ffmpeg 亦可）：failure 0；error 只有第一輪既有環境錯誤；新測試不得 skip（需 ffmpeg 的 mux／true peak 例外，skip 訊息寫明）；測試數比第二輪結束時多。**必要**
- 全套不退步：第一、二輪 acceptance 的 P-base、P-ramp、demo2 frames sha 與第三輪前相同（見共通規則）。**必要**
- `grep -nE "for (y|x|row|col|px) in range" scripts/fx/` 仍無逐像素迴圈。**必要**

## S-展示3 —— 必要（驚豔時刻）
位置（建造者定，例 `wow/fx/demo3/`）：
- **自動草稿片**：`plan-auto.json`（fx_autoplan 原始輸出，不得事後修改）、`plan.json`（最終）、`diff.md`（每一處手改：改了什麼、為什麼）、成片 mp4（含配樂＋音效層）、預覽 gif、`qa/report.md`＋`report.json`、`README.md`（一行重現、牆鐘、素材來源、fresh clone 步驟）。**必要**
  - 片長 15–30 s（ffprobe）。**必要**
  - 「少量手改」：plan-auto 與 plan 的決定（段落＋事件）中被改／刪／增的 ≤ 30%（以 diff.md 列舉數 ÷ plan-auto 決定數，評審抽查 diff 與實際 JSON 差異一致）。**必要**
  - manifest 可查到：音效層 ≥ 3 種、主體轉場（subject_reveal 或 match_cut）≥ 1、drop ±1 拍內最重轉場＋flash＋hit。**必要**
  - qa_media：true_peak PASS；所有 WARN/FAIL 落在已規劃事件 ±1 格內且 README 解釋；未規劃 flash／pop／freeze = 不過。**必要**
  - 音畫對位抽量：每個 hit／whoosh 在 mp4 音軌的起點與視覺事件（逐格差分能量峰）差 ≤ 1 格（40 ms）。**必要**
- **模板轉移片**：把 demo2 的節奏（fx_reverse → draft，或 demo2/plan.json）套到另一首曲子＋另一批素材（都不同於 demo2）；README 列出來源計畫、目標曲 beats.json、事件對照表（原拍號 → 新拍號 → 新 ms）；所有事件在新曲拍上 ±1 格。**必要**
- 「自動草稿 vs 最終」差異說明：前述 diff.md，並附兩版各一張聯絡表（同時間點抽格）。**必要**
- 不修改 examples/；不引入第三方音檔／LUT／模型入庫。**必要**

## 看完整成品（第三輪；獨立評審肉眼＋原速聽看判定，不看建造過程）
抽格：每個剪點 −3..+3 格、drop 前 2 拍到後 2 拍每格、每個主體轉場 p≈0.25/0.5/0.75 與剪點前後 3 格、每個 follow 文字段首／中／尾、片頭 2 s 與片尾 2 s 每 5 格。另原速有聲播放兩片各至少兩次。
| 項目 | Kano | 理由 |
|---|---|---|
| 音效讓剪輯「變專業」：whoosh／hit 跟畫面同步、音量融入配樂，關掉音效對照時明顯少了衝擊感；不像罐頭音效貼上去 | 必要 | spec 第二件事；音效做壞比沒有更糟 |
| 音效有節制：不是每個事件都響、不互相疊成一團、沒有爆音或削波聲 | 必要 | 過度音效是業餘感最快的來源 |
| 大動作真的落在 drop：聽到爆點的那一刻看到最重的轉場＋閃白，前面的 build 有「蓄力」（riser＋拍前變速）而不是平鋪直敘 | 必要 | 本輪第三件事，也是爆款片最核心的爽點 |
| intro 克制、drop 爆發、outro 收得乾淨：整支片有能量弧線，不是每拍一樣忙 | 必要 | 「片子好」與「效果多」的差別 |
| 主體轉場「無縫」：match_cut 兩鏡主體位置大小看起來接得上；subject_reveal 從主體輪廓長出來而不是一個圓圈擴張；轉場時無黑邊、無撕裂 | 必要 | 短影音最紅的兩種，做不像就失去意義 |
| zoom／bounce 以主體為中心：放大時主體不被推出畫面或切掉頭 | 必要 | 主體感知的直接可見結果 |
| 跟隨文字不擋臉、不抖、可讀 | 必要 | follow 做壞會直接擋住主角 |
| 模板轉移片「感覺像參考片的節奏」：停頓、爆點、密度的位置相對於音樂和原片一致，但畫面與音樂完全是新的 | 必要 | spec 第四件事 |
| 模板轉移片沒有出現參考片的任何畫面、聲音或人物 | 必要 | 授權與倫理界線 |
| 自動草稿本身（plan-auto 算出的版本）是個合理起點：不看 diff 直接播也像一支能用的初稿，reason 讀起來有道理 | 必要 | spec 明說「給人改的起點」；起點爛就沒有價值 |
| diff.md 的手改是「品味調整」而非「救火」（不是把 autoplan 的大半決定推翻） | 加分 | 證明 autoplan 有用 |
| LUT 調色讓兩批素材色調統一、不過飽和、膚色／主體色不怪 | 加分 | 專業標準做法 |
| 快速運動（shake／push／zoom）無頻閃感（有用 motion_blur 時） | 加分 | 細節質感 |
| proxy 縮圖頁一眼看懂每個事件、幾秒內可決定要不要 | 加分 | 工作流速度 |
| 任何格無瑕疵：無黑格、錯位、畫布跳尺寸、透明洞、上一段殘影 | 必要 | 任一可見瑕疵即不能交付 |
| 角色動作沒被特效「發明」或取代 | 必要 | SKILL.md 既有預設 |
| 音樂起訖淡入淡出、片長 15–30 s 與音樂段落對齊（結束在樂句尾而非半拍） | 必要 | 成片交付物 |
| 預覽 GIF 大小 | 無感 | 預覽用 |

## 不算通過的樣子
- anchor 寫了但質心照樣移動（仍以畫面中心縮放）；follow 文字蓋到主體；沒有主體資料時崩潰或默默用錯的主體。
- subject_reveal 其實是圓形擴張；match_cut 質心差 > 3 px 或露黑邊。
- 音效偏離視覺事件 > 10 ms、true peak > −1 dBTP、入庫第三方音檔；舊計畫重算突然多出音效或畫面變了。
- drop 偵測落在安靜段或 build 中段；`on:"drop"` 覆寫使用者手改值。
- autoplan 剪點不在重拍、最重轉場不在 drop、決定沒有理由、或輸出無法直接算繪。
- 模板轉移後事件不在新曲拍上、事件類型順序改變、計畫指向參考片素材。
- 恆等 LUT 不是位元相同；壞 .cube traceback；入庫第三方 LUT。
- proxy 不到 3× 快、時間軸與正式版不同、或汙染正式算繪。
- 修改 examples/ 或本答案卷。
