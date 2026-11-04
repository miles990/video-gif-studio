# 答案卷 第八輪 — 虛擬攝影機、2.5D 運鏡、手持質感、運鏡語言庫、參考片抽運鏡、跨鏡連貫、分鏡本與俯視圖、生成控制、運鏡量測（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-8.md（S-100..S-109）、wow/fx/spec-7.md（S-90..S-94 分鏡層：storyboard.json、storyboard_lint、animatic、提示詞）、
references/spatial-previs-workflow.md（camera-only 引導片、motion_pack 驗證與編碼）、scripts/motion_pack.py（CLI：`motion_pack.py PACK` 只驗證並印 `{"valid":true,"frames":N,"size":[w,h],"controlOwnership":…}`；
`motion_pack.py PACK --output X.mp4` 驗證後編碼並寫 `X.verification.json`；schema `laceframe.motion-pack.v1`（`pack.json`、`clip.fps` 1–60、`clip.frames` 1–1800、`|frames − durationSec·fps| ≤ 0.5`、
`control/frame-0001.png` 起、`atSec = i/fps`（容差 0.00011 s）、每格 sha256、同尺寸 PNG ≤ 4096）或 `laceframe.white-model.frame-pack.v1`（fps ∈ {12,24,30}、≤ 900 格、偶數寬高 ≤ 1920）；
未寫 `controlOwnership` 時預設 `camera-body`）、第五輪 acceptance-5.md 與第七輪 acceptance-7.md 的共通規則。出題者 2026-11-05 寫定。

每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條），並附理由。
CLI／欄位名以建造者文件為準；本卷用 spec 用語（`camera.json`、`camera_track.json`、`cam_render`、`cam_handheld`、`cam_query`、`cam_extract`、`continuity_lint`、`storyboard_book`、`cam_export`、`taste_report` 的 `camera` 段），改名須在 references（例 `camera.md`）寫明對應。

## 共通規則（第一～七輪全部沿用，另加）
- 技能 venv、ffmpeg 經 `VIDEO_GIF_FFMPEG`、「報錯」定義（非 0、無 traceback、不建 `--out`、牆鐘 < 3 s）、不得改 examples/、不得改本答案卷、付費哨兵計數 = 0、離線測試不下載也不讀真實模型權重。
- **量測不信任建造者**：本卷每個已知答案由出題者的合成幾何決定，或由出題者的獨立量法從**輸出檔**重算：
  - **標記點追蹤**：合成卡片上的彩色標記點（每層顏色唯一）以色彩遮罩求質心（次像素），算該層的平移與縮放（兩兩距離比）。
  - **全域運動追蹤**：OpenCV ORB/SIFT＋RANSAC `estimateAffinePartial2D`（相似變換：tx、ty、scale、rotation），限定在出題者已知的區域遮罩內。
  - **模糊量**：ESF（邊緣擴散函數）10–90% 寬度，減去來源同邊緣的 10–90% 寬度，單位 px。
  - **jerk／加速度**：對逐格狀態序列（或逐格量得的位移）做三階／二階中央差分，dt = 1/fps，單位文件寫明（m/s³、°/s³、px/s³）。
  建造者 JSON 自報值只拿來比對誠實度：與出題者值差超出本卷容差 → 該條不過。
- **JSON 健全**：所有 JSON 用 `json.loads(..., parse_constant=拒絕)` 可讀；不得有 NaN／Infinity；未定義寫 `null` 並附 `reason`。
- **可重現**：同輸入、同設定、同 seed 跑兩次 → JSON（除時間戳／耗時欄）與 PNG／frames 逐位元相同；`PYTHONHASHSEED=0` 與 `=1` 結果相同。
- **深度來源**：本卷所有 2.5D 測試以 `--depth`（float32 公尺 `.npy` 或 16-bit 毫米 PNG，文件寫明）餵入出題者的**精確深度圖**；不得因無 Depth Anything 權重而 skip。有權重時另跑一次真實深度路線，只檢查不崩潰與 S-101 拒絕邏輯。
- **攝影機約定**：等效焦距以 36 mm 寬全片幅定義，`f_px = W · f_mm / 36`；主點在畫面中心；右手座標 +X 右、+Y 上、+Z 往前（文件若用別的約定須寫明，出題者換算）。本卷 W×H = 960×540、30 fps、35 mm → `f_px = 933.33`，除非另寫。
- **舊計畫不退步**：第一～七輪基準計畫 `--formats png` frames sha256 逐格相同於第八輪前 commit；具名運鏡（S-60）舊計畫結果不變，除非文件寫明且有旗標回復。

## 合成素材（全由測試程式以 numpy／OpenCV／ffmpeg lavfi 產生；不入庫真實影片）
| 代號 | 內容 | 已知答案（出題者以針孔投影算出） |
|---|---|---|
| CARDS3 | 三張正對攝影機的平面卡：**NEAR** Z=2 m、0.6×0.8 m、中心 X=+0.4 m（紅／黃二色棋盤）；**MID** Z=5 m、2.0×1.2 m、中心 X=−1.0 m（綠／青棋盤）；**FAR** Z=20 m、30×17 m 全幅背景（藍／淺灰棋盤，約 1.46× 過掃）。每張卡 4 個該層專屬顏色的標記圓（半徑 6 px 起）。附精確深度圖（z-buffer）與每層遮罩。所有調色盤顏色 Y ≥ 40（無黑） | 起始：NEAR 中心 x ≈ 666.7 px、寬 280 px；MID 中心 x ≈ 293.3 px、寬 373 px |
| DZ | 主體卡 Z=5 m、0.8×1.6 m 置中（洋紅／白），背景卡 Z=20 m（直條紋＋標記點）；附深度圖 | 主體影像高 = f·1.6/5 = **298.7 px** |
| RACK6 | 六條並排直條卡，深度 Z ∈ {1.5, 2, 3, 5, 10, 20} m，每條世界寬 = 160·Z/f（影像寬皆 160 px），每條有黑白垂直階梯邊（來源 ESF 10–90% 寬 ≤ 1 px） | 對焦 5 m 時 thin-lens 失焦量 ∝ \|1/Z − 1/5\| = {0.467, 0.300, 0.133, 0, 0.100, 0.150} |
| LINE | CARDS3 但 NEAR 與 FAR 各加 2 px 寬白色垂直細線 | 運動模糊長度量測 |
| HORIZ | 960×540：上半天空漸層、下半地面紋理，中間一條清楚的水平地平線；可疊 roll | 地平線傾角 = 疊加 roll |
| SUBJ | 灰紋理背景＋主體圓（半徑 0.12 H）＋主體 sidecar bbox | 構圖：中心位置、頭頂空間已知 |
| TEX | 4000×3000 程序紋理（多尺度雜訊＋隨機形狀，seed 3），平面場景（相似變換精確） | S-104 參考片來源 |
| REFMOVE | 由 TEX 以已知相似變換逐格取景，960×540、30 fps、12 s、H.264 CRF 18、疊 σ=2 雜訊。段落：0–2 s **pan**：內容水平速度 v(t)=6·sin²(πt/2) px/格（總位移 180 px）；2–4 s **tilt**：3 px/格 等速（180 px）；4–6 s **zoom in**：縮放 1.00→1.30（每格等比）；6–8 s **roll**：0→6°（0.1°/格）；8–10 s **static**；10–12 s **複合**：pan 4 px/格＋roll 0.05°/格＋zoom 1.30→1.20 | 每格 tx、ty、scale、rotation 真值表（出題者存 JSON） |
| REFCUT | REFMOVE 0–4 s 接一段由 TEX 另一區域取景的 4 s 反向 pan（−5 px/格），第 120 格硬切 | 剪點 = 格 120；兩鏡曲線各自已知 |
| STATIC10 | TEX 固定取景 10 s，σ=4 雜訊＋全畫面亮度 2 Hz ±8% 閃爍＋H.264 CRF 23 | 攝影機運動 = 0 |
| REFHAND | TEX 固定取景，疊加 S-102 handheld 層級 seed 7 的抖動軌跡（換算為 px 與度） | 抖動軌跡真值 |
| SB-6 | 分鏡（spec-7 S-90 格式）：雙人對話 A 左、B 右；6 鏡：1 WS static、2 MS push-in on A、3 OTS CU B、4 MS truck 右、5 CU A static、6 WS pull-out；第 5 鏡無素材（剪影卡） | 6 格面板；全部機位在軸線同側 |
| SB-6-CROSS | SB-6 但第 4 鏡機位放到軸線另一側，無越軸理由 | 越軸於第 4 鏡 |
| CC-* | 跨鏡連貫夾具（見 S-105） | 見表 |

基準指令（名稱以建造者為準）：
```
python scripts/camera.py validate D/camera.json
python scripts/camera.py sample D/camera.json --fps 30 --out D/track.json [--strict | --smooth]
python scripts/cam_render.py D/scene.png --depth D/depth.npy --camera D/camera.json --out D/out --formats mp4,png
python scripts/cam_handheld.py --tier handheld --seed 7 --duration 120 --fps 30 --out D/hh.json
python scripts/cam_query.py --intent reveal --duration 3s
python scripts/cam_extract.py D/REFMOVE.mp4 --out D/preset
python scripts/storyboard_lint.py D/storyboard.json --continuity --out D/lint
python scripts/storyboard_book.py D/storyboard.json --out D/book --formats html,pdf
python scripts/cam_export.py D/camera.json --scene D/scene --format motion-pack --out D/guide.zip
python scripts/motion_pack.py D/guide.zip
python scripts/motion_pack.py D/guide.zip --output D/guide.mp4
python scripts/taste_report.py D/film.mp4 --storyboard D/storyboard.json --camera D/track.json --out D/taste
```

---

## S-100 虛擬攝影機模型 —— 必要（理由：其餘九條都吃這份狀態；沒有可取樣、可量的攝影機，運鏡只是一個名字）
1. **欄位**：狀態 = 位置（x,y,z m）、pan/tilt/roll（°）、焦距（等效 mm）、對焦距離（m）、景深強度（文件化單位，例 f-number 或 0–1 強度並寫換算）、快門角（°）。JSON Schema 檔存在，以 `jsonschema` 驗證；缺欄、型別錯、焦距 ≤ 0、對焦距離 ≤ 0、快門角 ∉ [0, 360]、keyframe 時間非遞增 → 報錯並指出欄位路徑。**必要**
2. **keyframe＋緩動**：KF 夾具：pan t=0 → 0°、t=1.0 s → 10°（easeInOutCubic）、t=2.0 s → 10°（hold）；30 fps 取樣 61 格。出題者 Penner 公式：格 6 = **0.320°**、格 15 = **5.000°**、格 24 = **9.680°**、格 30..60 = 10.000°；每格誤差 ≤ 1e-4°。S-60 全部具名緩動各取 101 點對 Penner 參考 ≤ 1e-6（正規化）。**必要**
3. **spring**：文件化參數（剛度、阻尼或 ζ、ω）；欠阻尼 spring 的取樣與閉式解 `1 − e^{−ζωt}(cos ω_d t + ζω/ω_d sin ω_d t)` 差 ≤ 1e-3；過衝量與閉式解差 ≤ 1%。**必要**（spec 明列 spring）
4. **逐格軌跡輸出** `camera_track.json`：每格完整狀態、fps、格數 = round(時長·fps)；所有後續量測與 S-107 匯出都讀這份。**必要**
5. **jerk／加速度上限**：預設值以文件寫明（每通道：位置 m/s³、角度 °/s³、焦距 mm/s³），並寫「專業穩定器量級」的校準依據（量了什麼、數值）。兩個夾具：
   - **SMOOTH**：pan 0→10°、2 s、easeInOutCubic（解析 jerk = 24·10/2³ = **30 °/s³**）→ 預設上限下**不得**報錯、不得被改（`--smooth` 開或關，輸出軌跡逐位元相同）。若預設上限讓 SMOOTH 失敗＝上限不合理 → 不過。**必要**
   - **STEP**：pan 0→10° 線性、0.1 s（3 格）→ `--strict`：報錯，訊息含 keyframe 序號／時間、實測峰值 jerk、上限值，不產出軌跡；預設模式至少發警告（不得靜默）。**必要**
   - **STEP `--smooth`**：出題者對輸出軌跡三階中央差分：max \|jerk\| ≤ 上限 ×1.05、max \|加速度\| ≤ 加速度上限 ×1.05；終值 10° ±0.1°；過衝 ≤ 行程 2%；若必須延長時間，報告寫明新的到達時間，且延長 ≤ 文件化上限；報告列原始與平滑後峰值 jerk。**必要**
6. 位置、焦距通道各有一組 STEP／SMOOTH 夾具同上（例 dolly 0→1 m 於 0.1 s／2 s）。**必要**
7. 三階差分在 24／30／60 fps 下判定一致（同一 STEP 在三種 fps 都被抓，同一 SMOOTH 都通過）。**加分**（理由：防止上限其實綁死在 30 fps）

## S-101 2.5D 運鏡算繪 —— 必要（理由：spec 驚豔時刻「一張照片＋一句話像穩定器拍的」；未抵達樣子「像 Ken Burns 等速無視差」就是這條的反例）
全部以 CARDS3／DZ／RACK6／LINE 與精確深度圖，960×540、30 fps；量測用標記點追蹤。
1. **push-in 視差比例（針孔）**：攝影機沿光軸前進 Δz = 0.5 m（easeInOutSine，2 s）。末格各層縮放（標記點距離比）理論值 s(Z)=Z/(Z−0.5)：NEAR **1.3333**、MID **1.1111**、FAR **1.0256**；
   - 各層 s 實測誤差 ≤ 1%（相對）。**必要**
   - **視差比** (s_NEAR−1)/(s_MID−1) = **3.000**、(s_MID−1)/(s_FAR−1) = **4.333**，各 ±5%。（等比縮放的 Ken Burns 得 1.0 → 必然不過。）**必要**
   - 每格標記點質心與針孔投影 `x = cx + f·X/(Z−Δz(t))` 差 ≤ 1.5 px（全部格、全部可見標記點）；中間格的時間曲線也跟 keyframe 緩動（≤ 1.5 px 即隱含）。**必要**
2. **truck／pedestal**：攝影機右移 Δx = 0.05 m → 影像位移 −f·Δx/Z：NEAR **−23.33 px**、MID **−9.33 px**、FAR **−2.33 px**，比例 10 : 4 : 1；各層絕對誤差 ≤ 1 px、比例 ±5%。pedestal Δy = 0.05 m 垂直方向同理。**必要**
3. **dolly zoom**（DZ）：攝影機後退 Δ：0 → 2.5 m（3 s，easeInOutCubic），焦距 f(t) = f0·(5+Δ)/5（35 → 52.5 mm）。
   - 主體影像高每格 = 298.7 px **±2%**（全部 91 格）。**必要**
   - 背景縮放（背景標記點距離比）末格理論 (7.5/5)·(20/22.5) = **1.3333**；實測 ≥ **1.20**（變化 ≥ 20%）且與理論差 ≤ 3%；逐格單調。**必要**
   - 主體輪廓外 4 px 帶內無撕裂（同第 6 條判定）。**必要**
4. **rack focus**（RACK6）：
   - 固定對焦 5 m、文件化中等景深強度：模糊量（ESF 增寬）最小者 = 5 m 條，且 5 m 條增寬 ≤ 0.5 px；近側嚴格單調 1.5 m > 2 m > 3 m > 5 m，遠側嚴格單調 20 m > 10 m > 5 m。**必要**
   - 全 6 條的模糊量與 \|1/Z − 1/Z_f\| Spearman ≥ 0.94。**必要**
   - 預測模糊 ≥ 2 px 的條，模糊比例與 thin-lens \|1/Z − 1/Z_f\| 比例差 ≤ 20%。**加分**（理由：專業者看得出焦外隨深度增長是否「像真鏡頭」；一般人看單調就夠）
   - **拉焦**：對焦距離 2 m → 10 m（2 s，easeInOutSine）。每格最清楚的條 = 以屈光度（1/Z）最接近該格對焦距離的條；「最清楚條切換」的格與理論切換格差 ≤ 2 格。**必要**
   - 景深強度加倍 → 失焦條模糊量 ×2 ±15%；強度 0 → 全部條增寬 ≤ 0.5 px。**加分**
5. **運動模糊 180° 快門**（LINE）：等速 truck 使 NEAR 線每格移 20 px（FAR 線約 2 px）。快門 180° → NEAR 線拖影長 10 px ±20%，FAR 線 ≤ 1.5 px（深度相依，不是全畫面同一模糊）；快門 0° → 兩線增寬 ≤ 1 px；靜止攝影機 → 無拖影。**必要**
6. **補洞與撕裂**（truck Δx = 0.05 m 與 orbit 1.5°）：出題者由幾何算出去遮擋區遮罩。
   - 無黑、無透明：輸出 RGBA 時 alpha 全 255；任一格 Y < 20 的像素數 = 0（調色盤 Y ≥ 40）。**必要**
   - 去遮擋區像素 ≥ 95% 與其**後方層**調色盤 ΔE2000 ≤ 12；NEAR 調色盤顏色出現在去遮擋區 ≤ 2%（前景沒有被拉成橡皮布塗進背景）。**必要**
   - **撕裂帶寬**：沿 NEAR 卡左右輪廓逐列量「不屬於任一層調色盤（ΔE > 12）的連續像素數」：中位 ≤ 2 px、最大 ≤ 4 px。**必要**
   - 補洞時間穩定：去遮擋區逐格 mean \|ΔY\|（扣除幾何位移後）≤ 4（不閃爍、不每格換紋理）。**必要**
7. **可信範圍與拒絕**：視差量 P = 起訖間「最近可見深度與最遠可見深度的影像位移差最大值」÷ W，文件寫明公式與上限 B（agent 自訂、依量測校準，寫校準依據）。
   - 建造者自報 P：truck 0.05 m 時理論 (23.33 − 2.33)/960 = **2.19%**，自報值差 ≤ 5%（相對）。**必要**
   - 以文件 B 反推 truck 量：要求 0.8·B → 正常產出；1.25·B → **拒絕**（報錯定義）且訊息建議「改用生成（Grok 等，先問使用者）或真實素材」；truck 1.0 m（P ≈ 44%）、orbit 30° 無論 B 為何都必須拒絕。**必要**
   - 拒絕判定看**整段路徑的累積**，不是單段 keyframe（見另卷）。**必要**
8. **不是 Ken Burns**：同 CARDS3 push-in，與「整張等比放大」版比較：NEAR 與 FAR 縮放差 ≥ 0.25（理論 0.308）。**必要**（理由：spec 點名的未抵達樣子，獨立一條方便報告）
9. **效能**：960×540 2 s push-in（60 格）含補洞與景深 ≤ 30 s；1080×1920 6 s ≤ 5 分鐘（開發機）。**加分**（理由：可反覆試；不影響正確性）

## S-102 手持與穩定器質感 —— 必要（理由：spec 未抵達「手持像隨機抖」；頻譜結構是可量的分界）
量法：`cam_handheld` 產 120 s、30 fps（3600 格）軌跡，pan、tilt、roll 各通道 Welch PSD（nperseg = 512，Hann）；能量占比以 0.02–15 Hz 總能量為分母。
**頻帶定義（出題者固定）**：
| 帶 | 頻率 | 意義 |
|---|---|---|
| D 漂移 | 0.02–0.15 Hz | 持機者重心慢飄、構圖修正 |
| B 呼吸 | 0.15–0.45 Hz | 呼吸（約 9–27 次/分） |
| G 步伐 | 1.4–2.4 Hz（＋諧波 G2 2.8–4.8 Hz） | 走路步頻 |
| T 顫動 | 5–12 Hz | 手部生理顫動、微震 |
1. **目標剖面文件化**：每個強度層級（locked／steadicam／handheld／run-and-gun）寫明 D、B、G(+G2)、T 的目標能量占比與各通道 RMS（°），並寫**來源**（量了哪些真實手持片、誰拍、授權；只用文獻值或手調則明標「未經實拍校準」）。**必要**
2. **符合剖面**：每層級每帶實測占比與目標差 ≤ max(0.05, 目標 ×25%)。**必要**
3. **不是白雜訊**：handheld 與 run-and-gun 在 0.02–12 Hz 的頻譜平坦度（幾何平均／算術平均）≤ 0.35（白雜訊約 0.9）。**必要**
4. **步伐峰**：handheld（行走變體）與 run-and-gun 的 PSD 最大值落在 G 帶，且比 1.0–1.4 Hz 與 2.4–2.8 Hz 的中位 PSD 高 ≥ 6 dB。**必要**
5. **層級排序**：locked 軌跡全為 0（逐位元）；RMS steadicam < handheld < run-and-gun，相鄰比 ≥ 1.8×；steadicam 的 T 帶占比 ≤ 2%（穩定器沒有手抖）。**必要**
6. **seed 可重現**：同 seed 兩次逐位元相同；seed 7 與 8 軌跡 Pearson \|r\| < 0.3，且兩者各帶占比差 ≤ 0.05。**必要**
7. **畫出來真的是這樣抖**：handheld seed 7 套在 TEX 靜態圖上算繪 10 s，出題者全域追蹤得逐格 tx/ty/rotation，換算為角度（文件化 FOV）後與軌跡 Pearson r ≥ 0.9；畫面四邊無黑邊或拉伸外露（每格四邊 4 px 帶 Y ≥ 20、無重複邊緣條紋）。**必要**
8. 可從參考片抽剖面（S-104 第 5 條）並以具名預設套用。**必要**（spec 明列）

## S-103 運鏡語言庫（動機→運鏡）—— 必要（理由：spec「每鏡都在動沒有理由」的解藥；導演查得到才會用）
1. **覆蓋**：至少 spec 列出的 7 個意圖：reveal、intimacy、tension、energy、isolation、awe、follow；每條欄位非空：**動機**（為什麼動）、運鏡（S-60 具名，單一）、**速度範圍**（數值＋單位，例 m/s、°/s、畫寬%/s）、時長範圍、**焦距建議**（mm 範圍）、相關角度（tension 的荷蘭角、awe 的仰角，數值範圍）、**常見失敗**（≥ 1 條，具體，例「推太快變成逼近感」）、**出處**。**必要**
2. **出處可查**：每條出處 = 檔案路徑＋節（例 `~/.claude/skills/wow/references/vocab/3d-vfx-game-av.md §I`、`cinematic-lighting.md`、`scene-staging-layout.md`）或業界來源 URL／書名頁；腳本檢查路徑存在且引用的詞條／標題字串出現在該檔（grep）。100% 通過。**必要**
3. **語意正確**（出題者規則，對 cam_query 產出的候選軌跡計算）：intimacy = 朝主體前進（Δz > 0）且速度上限 ≤ energy 類位移速度下限的 1/3；isolation = 後拉（Δz < 0）；tension = 慢推＋\|roll\| ∈ (0°, 15°]；awe = tilt 向上或機位低於主體且慢升；reveal = 升降或後拉；follow = 主體在畫面中位置標準差 ≤ 0.03 畫寬（以 SUBJ 移動版驗證）；energy = 含手持層級 ≥ handheld 或甩鏡。**必要**
4. **`cam_query --intent reveal --duration 3s`**：輸出 1–5 個候選；每個是合法 S-100 camera.json、時長 3.000 s、一鏡一運動、出題者由軌跡算得的速度落在該條速度範圍內、通過 S-100 預設 jerk 上限、附動機與出處。**必要**
5. **決定性**：同指令兩次、`PYTHONHASHSEED=0/1` 輸出逐位元相同；候選排序穩定。**必要**
6. **邊界**：未知意圖 → 報錯列有效意圖；`--intent intimacy --duration 0.3s`（慢推不可能在 0.3 s 成立）→ 報不可行或候選標 `feasible:false` 並說明，**不得**靜默給出超速軌跡；`--duration` 單位缺失或負值 → 報錯。**必要**
7. 給 `--scene`（深度）時，超出 S-101 可信範圍的候選被濾除或標記。**加分**（理由：導演少踩一次拒絕）
8. 每條附 1 個 3 s 示範片（CARDS3 或剪影卡）。**加分**
9. cam_query 回應 < 200 ms。**無感**（理由：導演不會因此改變決策）

## S-104 從參考片抽運鏡 —— 必要（理由：spec 驚豔時刻「抽出它的運鏡手感套到自己的素材」；同時不得搬運畫面）
出題者設定門檻（960×540；更高解析度按畫寬等比換算）：
| 量 | 門檻 |
|---|---|
| pan／tilt（X） | 逐格位移誤差 RMS ≤ **0.3 px/格**、最大 ≤ **1.0 px/格**；段末累積位移誤差 ≤ 行程 2%（REFMOVE 為 3.6 px） |
| zoom（Y） | 每格累積縮放 \|s_est/s_true − 1\| ≤ **1%**；逐格 \|log s 誤差\| ≤ 0.002 |
| roll（Z） | 每格累積角度誤差 ≤ **0.2°**；逐格 ≤ 0.03° |
| static | 平均 \|v\| ≤ 0.05 px/格、逐格 \|log s\| ≤ 0.0005、\|roll\| ≤ 0.005°/格，且標籤 = static |
1. REFMOVE 全 12 s：上表全成立；每段分類標籤正確（pan、tilt、zoom-in、roll、static、複合段列出 pan＋roll＋zoom-out 三分量）。報告單位 px/格＋畫寬正規化＋（文件化 FOV 換算的）°/s。**必要**
2. STATIC10（雜訊＋亮度閃爍＋壓縮）：整鏡標 static，全片累積漂移 ≤ 1 px，無假的 zoom（閃爍不得被當成縮放）。**必要**
3. REFCUT：剪點偵測在格 120 ±1；兩鏡各自的曲線符合門檻，第 2 鏡為反向 pan。**必要**
4. REFMOVE 以 1920×1080 重產：正規化曲線與 960×540 版差 ≤ 2%。**必要**（理由：參考片什麼解析度都有）
5. **手持頻譜抽取**（REFHAND）：抽回的抖動軌跡與真值 Pearson r ≥ 0.9；D/B/G/T 帶占比各差 ≤ 0.07；存成具名預設後 `cam_handheld --preset 名稱` 重新合成，帶占比與原剖面差 ≤ 0.07。**必要**
6. **只抽曲線**：預設檔只含曲線與統計（每 10 s 參考片 ≤ 256 KB），不含影像、縮圖、base64、或可還原畫面的陣列（出題者掃描：無 > 4096 元素的 2D 陣列、無 PNG/JPEG magic bytes）；文件寫明。**必要**
7. **來回**：把 REFMOVE 抽得的預設套到 TEX 另一區域的靜態圖算繪，出題者追蹤輸出，與 REFMOVE 真值曲線符合上表門檻。**必要**
8. 抽取速度 ≥ 2× 即時（960×540）。**加分**

## S-105 跨鏡運鏡連貫 —— 必要（理由：spec 未抵達「跨鏡方向打架」；專業剪輯一眼看出）
夾具（storyboard.json，spec-7 S-90 格式；方向以**畫面內容運動方向**記，文件寫明約定）：
| 夾具 | 內容 | 期望 |
|---|---|---|
| CC-OPP | 鏡 1 truck 右、鏡 2 truck 左，皆運動、無理由 | 報 `opposite_direction` 於剪點 1→2；建議 ⊆ {換鏡序、反轉鏡 2、鏡 2 改靜止}，每條建議套用後重跑 lint = 0 條 |
| CC-OPP-EX | 同上＋鏡 2 `continuity_exception: {reason: "主角回頭逃離，方向反轉是劇情"}` | 不報錯；報告列為「已接受例外」並顯示理由原文 |
| CC-OPP-EMPTY | 同 CC-OPP-EX 但 reason = `""` 或全空白 | 仍報錯（空理由不算理由） |
| CC-SPEED | 同向 push 0.3 m/s → 1.5 m/s | 報速度突變（倍率門檻文件寫明）；0.3 → 0.45 m/s 不報 |
| CC-MATCH | pan 右 12°/s → pan 右 12°/s | 0 條；可標 match move |
| CC-STATIC | 運動 → 靜止（任何方向） | 方向規則 0 條 |
| CC-FIGHT | 鏡 1 pan 右＋鏡 2 tilt 下且鏡 2 也 truck 左（兩鏡都在動且主方向相反） | 報方向打架 |
| CC-EYE | 鏡 1 末主體視線位置 x = 0.80 W，鏡 2 首 x = 0.25 W，剪點標 `match` | 報視線位置不接（門檻文件寫明，建議 ≤ 0.3 W）；x = 0.70 → 0.65 不報 |
1. 上表正例全報、反例 0 誤報；每條含剪點位置（鏡號、時間）、規則 id、具體建議。**必要**
2. 例外**看得見**：被接受的例外出現在 lint 報告與 S-106 分鏡本；不得有全域關閉連貫 lint 而不在報告顯示的開關。**必要**
3. **量測版**：對算繪後成片（用 S-104 抽得的曲線）跑同規則，與分鏡版判定一致（CC-OPP、CC-MATCH、CC-STATIC 三組）。**加分**（理由：抓出「分鏡寫對、算出來不對」）

## S-106 分鏡本與俯視機位圖 —— 必要（理由：spec 驚豔時刻「像專業分鏡師交的」；且 agent 要能檢查）
以 SB-6 與 SB-6-CROSS 產出 HTML 與 PDF。
1. **每鏡一格**：HTML 面板數 = 6（選擇器文件寫明，例 `[data-shot]`），順序與分鏡一致；每格含鏡號、景別、時長、運鏡名＋箭頭（SVG）、why（理由原文）、縮圖（素材縮圖或剪影卡；像素標準差 > 5，非空白）。第 5 鏡無素材 → 依景別畫剪影卡，不缺格。**必要**
2. **框線變化**：push-in 鏡畫起訖框，結束框面積 / 起始框 < 1；pull-out 鏡 > 1；truck 鏡框水平平移方向與箭頭一致；static 鏡無箭頭。**必要**
3. **俯視平面圖可機讀**：每場一張（SVG 內 data 屬性或旁附 `plan.json`，文件寫明）：主體位置、各鏡攝影機位置與朝向、運動路徑、180° 軸線端點。**必要**
4. **軸線一致**（出題者檢查）：SB-6 全部機位在 A–B 軸線同側（叉積號一致）；對每個同時含 A、B 的鏡，以平面圖機位與朝向投影 A、B 得畫面左右順序，與分鏡的畫面方向欄位一致（100%）。路徑箭頭方向與 truck 方向號一致。**必要**
5. **越軸**：SB-6-CROSS 平面圖中第 4 鏡機位在另一側（叉積號相反），且分鏡 lint（spec-7 SB-AXIS 規則）在第 4 鏡報越軸；平面圖上該機位有醒目標示。**必要**
6. **PDF**：`pypdf` 可開、頁數 ≥ 1；擷取文字含全部 6 條 why 原文（CJK 不缺字、不成豆腐框）；字型嵌入。**必要**
7. **自足**：HTML 不引用外部網址（離線可看）。**必要**
8. 面板版面隨畫幅（16:9／9:16）正確，縮圖不被拉伸（圓形圖案長短軸比 1 ±3%）。**必要**
9. 箭頭、框線、平面圖用統一視覺語言（顏色／線型圖例）。**加分**（理由：專業感；見「看完整成品」）
10. 面板配色、紙張尺寸可選。**無感**

## S-107 運鏡→生成控制（motion_pack 相容引導片）—— 必要（理由：同一份運鏡要能接 Grok 等生成路線；repo 既有驗證器是唯一閘門）
1. **通過既有驗證器**：`cam_export` 以 CARDS3 場景與 3 s push-in camera.json 產 `guide.zip`；`python scripts/motion_pack.py guide.zip` 印 `"valid": true`、`frames` = **90**（3 s × 30 fps）、`size` = 文件化尺寸。**不得修改 motion_pack.py 來放寬檢查**（出題者以第八輪前 commit 的 motion_pack.py 再跑一次，結果相同）。**必要**
2. **camera-only**：pack 寫 `controlOwnership: "camera-only"`；`motion_pack.py guide.zip --output guide.mp4` 成功，`guide.verification.json` 的 `controlOwnership` = `camera-only`、`frames` = 90、`creativeApproval` = `pending`。（漏寫會被預設成 `camera-body` → 不過。）**必要**
3. **引導片內容 = 那條路徑**：出題者對引導片各層（灰模／深度卡片）追蹤，縮放與位移符合 S-101 第 1 條的針孔數值（同容差）；深度卡片的亮度約定（近亮或近暗）文件寫明並與深度一致（NEAR 層平均亮度序與深度序一致）。**必要**
4. **灰模**：引導片平均 HSV 飽和度 ≤ 0.08（不把素材紋理、顏色帶進控制片；spatial-previs「不要把灰模複製進成片」的反面）。**必要**
5. **24 與 30 fps**、**1 格**、**最大格數** 邊界：24 fps 3 s = 72 格通過；atSec 全部 = i/fps（驗證器容差 0.00011 s）；超過 1800 格（或 white-model 900 格）→ `cam_export` 自己先報錯，不產出會被驗證器拒的包。**必要**
6. **不呼叫生成**：匯出與編碼全程付費哨兵 = 0；生成指令仍走 SKILL.md「先問使用者」（假客戶端：未確認前呼叫次數 = 0）。S-93 提示詞中的運鏡詞與此路徑的運鏡名一致。**必要**
7. 包內只有 `pack.json`、`control/frame-NNNN.png` 與可選 `camera.json`（來源記錄）；無可執行內容。**必要**
8. 另可輸出 `laceframe.white-model.frame-pack.v1`（clay 或 depth pass）且通過同一驗證器。**加分**（理由：接 companion white-model 工作流；非唯一路線）

## S-108 運鏡量測與品味檢查 —— 必要（理由：spec 第一原則「可量測」；接進 spec-7 taste_report 才會影響決策）
量測全部從**成片**（出題者全域追蹤），不得只讀 camera_track 自報。
| 夾具 | 內容 | 期望 |
|---|---|---|
| M-SMOOTH / M-JOLT | TEX 上 pan 200 px、2 s easeInOutCubic；JOLT 在格 31 加 1 格 8 px 水平踢 | JOLT 報 jerk 超限於格 31 ±1；SMOOTH 0 條；兩者 jerk 數值與出題者三階差分差 ≤ 15% |
| M-HORIZON | HORIZ 疊 roll 0°、1.5°、4°（靜止） | 地平線傾角 ±0.3°；0° 不報；1.5°、4° 超過文件化門檻（建議 1°）時報；分鏡標 tension＋dutch 時接受並顯示理由 |
| M-FRAME-S / -D | SUBJ：主體穩定於 x = 0.667 W（±0.5% 微動）／3 s 內無意間漂到 0.50 W | 構圖穩定度（主體中心正規化標準差）與出題者差 ≤ 0.003；D 報漂移、S 不報；三分點距離 ±0.01；頭頂空間（bbox 頂到畫頂 ÷ H）±0.01 |
| M-SPEED | 等速 pan 4 px/格 vs 4 ± 1.2 sin(2π·1Hz·t) px/格 | 速度 CV = 0 ±0.02 ／ **0.212** ±0.03；後者報速度不一致 |
| M-2MOVE | 同鏡 pan＋zoom 同時都超過運動門檻 | 報「一鏡兩運動」；分鏡宣告 S-60 允許的複合運鏡（例 follow）時依文件規則 |
| M-MOTIVE | 鏡有運動但 why 空白 | 報「運動無動機」 |
1. 上表每列正反例全對，數值在容差內。**必要**
2. **接進 taste_report**：spec-7 taste_report JSON 有 `camera` 段（每鏡：jerk 峰值、速度 CV、地平線傾角、構圖穩定度、頭頂空間、運動分類、動機有無），數值與獨立工具逐位元相同；無 NaN；報告 PNG／HTML 標出違規鏡。**必要**
3. 量測只從成片時（無 camera_track）也能跑（參考片、外部素材）。**必要**
4. 「每鏡都在動」整體統計：運動鏡占比與連續運動鏡最長串列出（另卷有對應檢查）。**加分**

## S-109 測試 —— 必要
1. `python -m unittest discover -s tests`：failure 0；新測試覆蓋 S-100（KF 三個數值、SMOOTH／STEP strict／smooth）、S-101（push-in 比例、truck、dolly zoom、rack focus 單調、補洞無黑、拒絕）、S-102（帶占比、平坦度、seed）、S-103（欄位與出處腳本、cam_query 決定性）、S-104（REFMOVE X/Y/Z 門檻、STATIC10）、S-105（CC-* 全表）、S-106（面板數、軸線一致、CROSS）、S-107（真的呼叫 motion_pack.py 驗證）、S-108（M-* 全表）。測試數多於第七輪結束時。**必要**
2. 合成素材產生器入庫（不入庫影片）；測試不需模型權重；需 ffmpeg 者無 ffmpeg 時 skip 並寫理由，其餘不得 skip。**必要**
3. 共通規則的舊計畫 sha 對照通過；`grep -nE "for (y|x|row|col|px) in range" scripts/` 新檔無逐像素迴圈。**必要**

---

## 看完整成品（第八輪；獨立評審原速看運鏡示範片＋翻分鏡本，不看建造過程）
示範：3 張真實或擬真靜態照（人像＋前景花、街景、室內）＋1 支參考片；導演用一句話意圖產 4–6 鏡（含 1 個 push-in、1 個 rack focus、1 個 dolly zoom 或 orbit、1 個手持、1 個套用參考片抽出的運鏡、至少 1 個靜止鏡），附分鏡本與俯視圖。並排「整張等比放大」的 Ken Burns 版。原速各看兩次。

| 項目 | Kano | 理由 |
|---|---|---|
| **像穩定器拍的，不像 Ken Burns**：盲評雙順序（2.5D 版 vs Ken Burns 版）2.5D 版勝；評審說得出「前景和背景移動不一樣」 | 必要 | spec 驚豔時刻與未抵達樣子的分界 |
| **無撕裂、無補洞穿幫**：原速與逐格（每鏡抽 5 格放大到 200%）都找不到前景邊緣拉絲、背景重複紋理、黑邊、透明洞 | 必要 | spec 未抵達「視差撕裂或補洞穿幫」 |
| **起停有重量**：加減速自然、不會一開始就全速或戛然而止；沒有「漂」的感覺（結束後不殘留飄移） | 必要 | 物理感是穩定器質感的核心 |
| **rack focus 像真鏡頭**：焦點從花移到臉，焦外隨深度變化；人臉清楚時花是柔的，沒有「整層一刀切」的硬邊模糊 | 必要 | spec 驚豔時刻原句 |
| **手持像人拿的，不像隨機抖**：評審看得出呼吸／步伐節奏；steadicam 版沒有手抖 | 必要 | spec 未抵達「手持像隨機抖」 |
| **每個運動都有動機**：評審抽 3 鏡讀分鏡理由，與畫面意圖相符；至少有靜止鏡讓片子呼吸 | 必要 | spec 未抵達「每鏡都在動沒有理由」 |
| **跨鏡接得上**：剪點前後方向、速度、視線不打架；有例外的地方報告寫了理由，且看起來是刻意的 | 必要 | spec 未抵達「跨鏡方向打架」 |
| **參考片手感有被學到但沒搬畫面**：評審說得出「推進節奏／手持感像那支」，找不到參考片任何畫面 | 必要 | 驚豔時刻＋反抄襲 |
| **分鏡本像專業分鏡師交的**：一頁看懂每鏡景別、運鏡、框線變化、理由；俯視圖主體、機位、路徑、軸線清楚，與畫面方向一致 | 必要 | spec 驚豔時刻原句 |
| 拒絕時說人話：要求過大的 orbit 時，導演回覆「這個角度 2.5D 會穿幫，建議生成或實拍」並提供可行的較小替代 | 必要 | 防止硬做出爛鏡頭 |
| 地平線水平（除非刻意荷蘭角）、主體構圖穩、頭頂空間合宜 | 必要 | 業餘感最常見來源 |
| dolly zoom 一看就有「暈眩感」，主體不跳動 | 加分 | 炫技鏡頭；做好很驚豔 |
| 引導片丟進生成路線後，生成結果的運鏡方向與引導片一致（使用者同意下抽查 1 次） | 加分 | 驗證「同一份運鏡、多處可用」 |
| 分鏡本配色、字型美觀 | 無感 | 不影響決策 |

## 不算通過的樣子
- 視差比 ≈ 1（等比縮放）、或量得的層縮放與針孔理論差 > 5%；dolly zoom 主體大小漂 > 2%。
- 補洞出現黑／透明像素，或前景顏色被拉進背景；撕裂帶 > 4 px。
- 超出可信範圍時仍硬算出結果；拒絕只看單段而被拆段繞過。
- 平滑把 SMOOTH 也改了，或 jerk 上限只在某一 fps 成立；STEP 被靜默接受。
- 手持頻譜平坦（白雜訊）、無步伐峰、seed 不可重現；剖面無來源。
- 運鏡庫出處路徑不存在或詞條找不到；cam_query 不決定或給出超出速度範圍的候選。
- 參考片抽取在靜止片報運動、把亮度閃爍當 zoom；預設檔含可還原畫面的資料。
- 連貫 lint 接受空理由例外，或例外不在報告顯示。
- 分鏡本缺格、俯視圖與畫面方向矛盾、越軸未標示；PDF 中文缺字。
- 引導片要靠修改 motion_pack.py 才能通過，或 `controlOwnership` 不是 camera-only。
- 運鏡量測只讀建造者自報軌跡、不從成片量；taste_report camera 段與獨立工具數值不一致。
