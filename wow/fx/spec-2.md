# wow 輕量 第二輪 — fx 效果擴充（2026-11-04）

來源：使用者 2026-11-04「好都做, 看還有沒有更好的做法?用最好合適的做法做」，針對主 agent 列的三批效果＋2.5D 視差。
前提：第一輪（spec.md S-1～S-14）通過審查二後才開建；同一 worktree C:\Users\User\src\vgs-fx、分支 fx-framework。
每個新效果仍是一個短小可讀的函數，沿用 registry、包絡、驗證、--list／--preview。

## 框架擴充（先做，新效果依賴它）
- S-15 **時間重映射層**：段落可寫 `"speed"`（常數、keyframes、或節拍包絡），也可用 `"ramp": {"into_beat": n, "slow": 0.3, "hit_ms": …}`
  做「拍前慢、拍上衝」；剪點仍落在指定拍上（輸出時鐘不變，只改來源取樣時鐘）。manifest 記錄每格的來源時間。
- S-16 **慢動作補格**：來源取樣落在兩格之間時，預設用 OpenCV DIS 光流雙向補格（零新依賴）；
  選用 `--interpolate rife`：RIFE v4.25 lite ONNX（MIT，onnxruntime CPU，權重放 .runtime/models，不入庫）。
  `--interpolate none|blend|flow|rife`。補格只用在慢動作，不偷偷改正常速度的格。量測：同一段 0.25× 慢動作三種方法的時間與觀感比較（並排圖）。
- S-17 **畫格歷史**：效果可宣告 `history: N`，在 ctx 取得前 N 格（輸出時鐘），供殘影／拖影；決定性、段落邊界行為寫明。

## 新效果（全部可節拍包絡、保留 alpha、有預設值與說明）
- S-18 第一批：`shake`（seed、重拍大）、`rgb_split`（色差，方向／距離包絡）、`radial_blur`（縮放／徑向模糊衝擊）、
  `echo`（殘影拖尾，用 S-17）、`text`（花字：字串、字型、大小、描邊、陰影、進場彈出／縮放隨拍；
  字型找系統字型——Windows 微軟正黑體、macOS 蘋方、Linux Noto CJK——找不到就清楚報錯，不內建字型檔）。
- S-19 轉場：`shape_wipe`（circle／diamond／star／heart，可柔邊，與 hex_shutter 共用遮罩工具）、
  `luma_wipe`（任意灰階圖當遮罩，附 2–3 張程序產生的遮罩：線性、放射、雲狀噪聲）、`push`／`slide`（四方向）、
  `spin`、`zoom_through`、`glitch`（區塊錯位＋掃描線，seed 決定）。
- S-20 質感／風格：`film_grain`、`vignette`、`light_leak`（程序生成、隨時間漂移）、`dust_scratches`、
  `invert_flash`、`black_flash`、`split_screen`（1→2→4 格隨拍）、`mirror`／`kaleidoscope`、`posterize`、`halftone`、
  `multi_cutout`（同一主體 3 張錯位卡片，定格摳像進階）。
- S-21 **2.5D 視差**（選用）：Depth Anything V2 **Small** ONNX（Apache-2.0；Base/Large 為 CC-BY-NC，**不得使用**），
  onnxruntime CPU。定格照片 → 深度圖 → 前後景分層位移（鏡頭微推／平移），邊緣以深度擴張＋inpaint 補洞，不露黑邊。
  深度圖可快取；模型不在時清楚報錯並建議改用 `beat_bounce`/`zoom_punch`。

## 品質與驗證
- S-22 每個新效果／轉場：形狀、dtype、alpha、決定性、在拍點的包絡值的離線測試；--preview 原圖對照格中每個效果肉眼可分辨。
- S-23 效能：每個新效果在 720p 的單格耗時寫進 fx.md；最慢的 3 個若 > 50 ms／格，嘗試 cv2 化並記錄前後數字。
- S-24 文件：fx.md 補新效果、時間重映射、補格方法比較、2.5D、授權（RIFE MIT、Depth Anything V2 Small Apache-2.0、系統字型不散布）；THIRD_PARTY 更新。
- S-展示2 第二支示範（同樣可 fresh clone 重現）：一支 15–25 秒、節奏明顯的「卡點混剪」，至少用到：拍前慢動作衝拍（補格）、
  shake＋rgb_split 打重拍、花字隨拍、形狀擦除或亮度擦除、split_screen、2.5D 視差定格、film_grain＋light_leak 收尾；
  qa_media 量得到重拍事件落在 ±1 格；看片判定由獨立評審做。

## 比清單更好的做法（調查結果，2026-11-04）
- 慢動作不用「重複格」或「交叉溶」：重複格會頓、溶接會鬼影；光流補格是剪輯軟體「光流慢動作」的同等做法，RIFE 是目前開源補格的實用標準（MIT、有 CPU 可跑的 lite ONNX）。
- 2.5D 用單張深度模型而不是手動分層：一張定格就能做；只用 Small（唯一可商用授權的尺寸）；onnxruntime 已隨 rembg 安裝，不需 torch。
- 亮度擦除一次給「無限種轉場」：換一張灰階圖就是新轉場，比逐一手寫形狀更划算。
- 花字用系統字型：避免散布字型授權問題，同時支援中文。

## 不做
GPU／GLSL 轉場（gl-transitions 轉接器仍為之後候選）；語音轉字幕；臉部／人體追蹤貼紙；Base/Large 深度模型。

## 限制來源
- 「全部做」：使用者原話。效果清單：主 agent 提出、使用者同意。
- 50 ms／格、示範 15–25 秒：agent 自訂儀器。

## 已就緒的選用模型（主 agent 2026-11-04 22:10 下載並確認 I/O；在 C:\Users\User\.codex\skills\video-gif-studio\.runtime\models，gitignored，不入庫）
- depth-anything-v2-small.onnx（99 MB，onnx-community，Apache-2.0）：輸入 `pixel_values` [B,3,H,W]（H、W 為 14 的倍數，ImageNet 正規化），輸出 `predicted_depth` [B,H',W']（相對深度，越大越近）。
- rife_v4.25_lite.onnx（22.5 MB，latentdivergence/fixflix-rife-lite，MIT，源自 hzwer/Practical-RIFE）：輸入 `input` [B,7,H,W]＝img0 RGB(3)＋img1 RGB(3)＋timestep(1)，0–1，H、W 建議補到 32 的倍數；輸出補出的那一格。
- 執行環境：C:\Users\User\src\fx-optdeps\venv（onnxruntime、opencv-python-headless、rembg、torch、beat_this）。技能 venv 沒有 onnxruntime：選用功能在缺件時要清楚報錯，測試用假引擎離線跑。
