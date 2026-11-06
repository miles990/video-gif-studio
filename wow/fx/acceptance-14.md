# 答案卷 第十四輪 — 遊戲資源與角色動畫管線：角色設定稿、動作影格、透明 sprite、引擎匯出、圖示組、平鋪材質、VFX、關鍵格→影片、示範包（獨立出題者，建造前寫定；建造者不得修改）

依據：wow/fx/spec-14.md（S-160..S-168）；spec-13.md（影像路由能力表：訂閱路線 = 只有 prompt、`transparent_background`、`referenced_image_paths`；**沒有** markup／遮罩、原生 GIF、SVG、模型／尺寸／張數選擇）；
references/sprites.md、animation-states.md、pixel-art.md、transparency.md、export.md、motion.md；SKILL.md 動作物理預設（支撐與重心轉移驅動身體、手驅動武器、布料粒子有慣性；共用畫布、不逐格重新置中；循環需姿勢＋速度＋接觸相容）；
process.md（兩軸閘門：技術軸定去留、好看軸由使用者；trunk-based、experimental 旗標）；沿用 acceptance-13.md 全部共通規則（花費閘門、FAKE-CODEX／FAKE-API、API-SENTINEL、NETGUARD、能力表、gen-manifest schema、ERR 信封、單位定義）。出題者 2026-11-06 寫定。

出題者查得現況（HEAD 954263f）：已有 `imagegen.py`（generate／refset build|check／alpha／motion／ingest／keyframes…）、`image_identity.py`、`image_alpha.py`、`image_motion.py`、`sprite_export.py`（自訂 `sprites.json`，**非**引擎原生格式）、`qa_media.py --loop`、`references/image-capabilities.json`（codex 路線：`transparent_native: true`、`native_gif/markup_edit/mask_edit/svg_native: false`、`n_per_call: 1`、`aspects: "prompt_only"`）。
本機引擎：`godot` 在 PATH 上但是 **3.2.stable**（SpriteFrames 是 `format=2`）；沒有 Godot 4、沒有 Unity。node 22 可用。**因此**：Godot 4（`format=3`）的「可載入」必須由出題者另備 Godot 4.x 可攜版（私有目錄，記版本與 sha256）實測；建造者也可自備，但不得以「我的解析器說合法」取代真引擎載入；Unity 只能做格式層檢查，報告必須寫 `engine_load: "untested"`。

每條標 Kano：**必要**（沒有就不算交付）／**加分**（有了驚豔、沒有不扣）／**無感**（做了使用者也不會注意，不得拿來抵其他條），附理由。
CLI／欄位名以建造者文件為準；本卷用 spec 用語（`imagegen.py character|animate|iconset|tile|vfx|kf-video|demo`、`sprite_export.py --engine`、`charsheet.json`、`anim.json`、`sprites.json`、`gen-manifest.json`），改名須在 references/ 寫明對應。若 `vgs` 存在，以 `vgs game …` 子命令提供（JSON 進出、ERR 信封）。

---

## 共通規則（第一～十三輪全部沿用，另加）

- **原創角色（最高優先，違反＝整卷不過）**：本管線只做原創角色與原創美術。
  - 請求點名既有遊戲／動畫／商標角色（或「做成 X 一模一樣」）→ 不重製；回覆說明並**主動提出原創替代案**（列出 ≥ 3 項與原角色不同的設計決定：剪影、配色、配件、物種／比例）。
  - 送往任何生成路線的 prompt、參考圖、檔名、metadata **不得**含該角色名或其官方美術；網路上的官方圖不得進 refset（沿用 S-131 授權欄位）。
  - 「類型／年代風格」不是角色（「16-bit JRPG 風」「銀河惡魔城風的手繪」可做）；不得過度拒絕：一般原創描述（「拿冰劍的狐狸劍士」）必須直接做，拒絕率 0/10（出題者以 10 條原創請求驗）。
  - 示範與夾具全部原創；manifest `originality: {named_ip_detected: bool, action: "proceed"|"offered_original"}`。
- **花費／影片閘門**：訂閱影像路線是預設；Grok／fal／任何影片模型與付費影像 API 只能在 `--approve-video <estimate_id>`（或 acceptance-13 的 `--approve-spend`）且 id 對得上**本次**預估、使用者在對話中明示同意時呼叫。沒有核准：影片網路請求計數 = 0（API-SENTINEL＋FAKE-GROK＋FAKE-FAL 三個哨兵），回 `E_APPROVAL_REQUIRED` 並附預估與「本機能做的替代」（補格、2.5D 運鏡、合成）。
- **生成額度**：本卷 live 生成上限 **60 張**（含 holdout 與 S-168 示範）；manifest ledger 計數；超過先問使用者。離線層一律 FAKE-CODEX 錄製匣。
- **能力誠實**：訂閱路線無尺寸／模型／張數參數 → 尺寸靠 prompt＋我們的後處理；manifest 必須記 `size_requested`（prompt 文字）與 `size_actual`；像素風一律是 `fallback: "pixel_quantize"`（生成的是「像素風圖」不是原生像素網格，依 pixel-art.md 不得宣稱手繪原生像素）。能力表沒有的功能（原生 GIF、遮罩）不得被宣稱使用。
- **共用畫布與 pivot**：沿用 sprites.md／SKILL.md——所有狀態共用同一畫布尺寸與同一 pivot（預設腳底接地點），**不得逐格依 bbox 重新置中**；有意的位移（跳躍上升、攻擊前衝）保留在影像中或明確分離成 root motion 軌並記錄，不得兩者都有。
- **兩軸閘門**：動畫輸出（S-161、S-166）進 process.md 兩軸：技術軸＝自動檢查＋`wow-judge panel` 瑕疵題（腳滑、身分漂移、單格跳、暈邊、循環跳點），對刻意破壞版（注入腳滑 3 px、身分換色、首末格跳）必須贏；好看軸由使用者以會動的 GIF 抽查，不定生死。
- **trunk-based**：每個 S 一個切片，全套測試＋doctor 綠就以 `experimental` 合回 main；本卷通過前，遊戲資源命令需 `--experimental`。

## 合成素材與夾具（全部由測試程式以 numpy／PIL 產生，或為 FAKE-CODEX 錄製匣；不入庫網路圖）

| 代號 | 內容 | 已知答案／用途 |
|---|---|---|
| **CHR-A-SYN** | 原創合成角色「冰劍狐」替身：橘色圓頭 #E07A2E、白口鼻 #F4EDE4、青色圍巾 #2BB5B0、冰藍劍 #9FE3FF（右手）、**角色自己的左眼**上方一道洋紅疤 #FF2BD6（3×8 px @256）；程式化畫 4 視角（正、側＝面向畫面左、背、¾＝面向畫面左），已知每個色塊面積與疤的位置 | 身分正樣本；配色卡答案 |
| **CHR-B-SYN** | 已知不同角色：藍灰方頭 #5A6E8C、紫圍巾 #7A3FB0、無疤、左手持斧 | 負對照 |
| **CHR-A-HUE** | CHR-A-SYN 但圍巾換成 #2B6BB5（ΔE2000 ≈ 18）、疤移除 | 「近似但不同」：身分量測必須掉分 |
| **EXP-6** | CHR-A-SYN 臉部 6 表情（中性、喜、怒、哀、驚、痛），只動眼口眉，耳朵／圍巾不變 | 表情表 |
| **WALK-8** | 64×64 像素角色 8 格走路循環 @10 fps：地線 y=60、左腳接地格 0–3、右腳 4–7，接地腳最低像素 x 每格精確已知；身體重心上下 bob 2 px，兩步兩個週期 | 腳底接地／重心／循環正對照 |
| **WALK-SLIDE** | WALK-8 但接地腳在接地期間每格向後滑 1→合計 3 px（與身體速度不符） | 腳滑必須被擋 |
| **WALK-DUPSEAM** | WALK-8 末格＝首格副本（9 格） | 循環「卡一下」必須被擋 |
| **WALK-JUMPSEAM** | WALK-8 截掉最後 2 格 | 循環跳點必須被擋 |
| **JUMP-SYN** | 12 格：蹲（預備）2、起跳 1、空中 6（重心 y 拋物線）、落地壓縮 2、回站 1 | 拋物線／預備／落地 |
| **ATK-SYN** | 10 格：預備 0–3、揮擊 4、**劍尖接觸目標框＝第 5 格（index 5）**、跟隨 6–7（拖影面積最大在 6）、恢復 8–9 | 事件格答案 = 5 |
| **SPR-OK** | 256×256 RGBA，抗鋸齒 2 px，直通 alpha，α=0 處 RGB=0 | 透明正對照 |
| **SPR-HALO** | SPR-OK 但邊緣 2 px 混入白底（未去溢色） | 暈必須被擋 |
| **SPR-SPECK** | SPR-OK＋17 個 1–3 px、α 20–90 的白點散在外框附近（重現 spec-13 實測的零星半透明白點） | 雜點必須被擋並清除 |
| **SPR-PREMUL-LIE** | 實際存預乘 RGB，但 metadata 宣稱 straight | 預乘錯配必須被擋 |
| **PIX-64** | 64×64 原生像素角色，14 色調色盤，1 px 深色描邊 #1B1426，α ∈ {0,255} | 像素模式正對照 |
| **PIX-BLUR** | PIX-64 經雙線性 ×3 後再縮回 | 必須被判「非網格／新色」 |
| **ICON-8** | 8 個 64×64 道具圖示（劍、盾、藥水、鑰匙、卷軸、寶石、弓、靴），光源左上 135°、2 px 描邊 #20182A、安全邊 4 px | 圖示一致正對照 |
| **ICON-8-BAD** | ICON-8 但：#3 描邊 4 px；#6 尺寸只佔 50%；#7 飽和度 ×1.6 | 個別離群必須指出 |
| **TEX-OK** | 256×256 週期性雜訊石板（數學上可平鋪） | 接縫正對照 |
| **TEX-SEAM** | 非週期雜訊（右緣與左緣不連續） | 接縫必須被擋 |
| **TS-16** | 16×16 草地→泥土 tileset，47 塊 blob 組（或 16 塊 corner-Wang），已知每塊邊緣碼 | 完整性／邊緣相容 |
| **VFX-BOOM** | 12 格 96×96 爆炸：分級 alpha、外圈發光；第 12 格 α 總和 = 峰值 1% | 一次性 VFX 正對照 |
| **VFX-ORB** | 8 格循環魔法球 | 循環 VFX 正對照 |
| **CAS-GAME** | FAKE-CODEX 錄製匣：每個請求回圖＋訊息；含正常、尺寸不符（回 1024×1024 而 prompt 要 64×64）、RGB 無 alpha、白點雜訊、轉面圖疤換邊、某視角換配色、整張帶棋盤格、配額錯誤 | 離線層 |

---

## S-160 角色設定稿（`imagegen.py character sheet`）—— 必要（理由：後面每個 S 的身分都鎖在它上面；設定稿錯，整包錯）

**命令形狀**：
```
imagegen.py character sheet --prompt "拿冰劍的狐狸劍士，像素風 64×64" [--image ref.png] \
  --views front,side,back,three_quarter --expressions 6 --out charsheet/ [--pixel 64] --experimental --json
→ charsheet/{views/*.png, expressions/*.png, palette.png, palette.json, sheet.png, charsheet.json, refset.json, gen-manifest.json}
```
1. **結構**：4 視角各一張 RGBA（同畫布、同腳底 pivot、同比例尺：四張主體高度差 ≤ 3%）；`charsheet.json` 記每視角 `facing`（`front|left|back|three_quarter_left` 等）、`refs_sent`（生成每張時實際送出的參考圖 sha；第一張之後的每張都必須帶 ≥ 1 張已接受的前一視角）、`asymmetric_features`（如「疤：角色左眼」）、`mirror_ok`（有不對稱特徵 → false）。產出的 `refset.json` 可直接被 `imagegen.py refset check` 讀。**必要**
2. **身分一致（與 acceptance-13 S-152 同一門檻族）**：每個視角對「其他視角＋正面」質心：
   - 嵌入（DINOv2／CLIP，主體遮罩裁切）：同角色 cos ≥ 0.70；CHR-B-SYN 負對照 ≤ 0.55；
   - 退路（無模型）：遮罩內 HSV 直方圖 Bhattacharyya ≤ 0.35 **且** ORB（Lowe 0.75）好匹配 ≥ 25；負對照 Bhattacharyya ≥ 0.50 或好匹配 < 10。
   - **背面與側面例外**：ORB 跨視角天生少匹配 → 這兩張改用「配色卡吻合」＋HSV：配色卡每個主色在該視角出現（見 4）且 Bhattacharyya ≤ 0.35；不得因此把 ORB 門檻整體下調。
   - **硬條件**：正樣本最小值 − 負對照最大值 ≥ 0.10（嵌入 cos）；CHR-A-HUE（只換圍巾色＋去疤）對 CHR-A 的分數必須**低於** CHR-A 自身最低分（排序正確）——否則報「工具分不出近似角色」。**必要**
3. **表情表**：≥ 6 表情；(a) 非臉部區（耳、圍巾、服裝，以 CHR 遮罩減臉部框）調色盤 ΔE2000 ≤ 6、輪廓 IoU ≥ 0.95（表情不該改髮型／服裝）；(b) 臉部框兩兩真的不同：SSIM ≤ 0.90 或 pHash ≥ 6；(c) 對 EXP-6 夾具，建造者的表情標籤分類（若有自動）正確 ≥ 5/6，或由出題者看片確認。**必要**
4. **配色卡**：`palette.json` = [{name, hex, role（主色／輔色／強調／描邊／膚毛）, area_pct}]，主色 4–12 個（像素模式＝實際用色全集 ≤ N）。對 CHR-A-SYN：每個已知色塊被抽到（ΔE2000 ≤ 3），沒有幻覺色（每個抽出色在某視角面積 ≥ 0.5%）；每個主色出現在 ≥ 3/4 視角（ΔE ≤ 6；背面可缺臉部色）；`palette.png` 色票旁印 hex。**必要**
5. **不對稱特徵不換邊**：`asymmetric_features` 標的特徵在各視角的位置與 `facing` 一致（詳細題在保留卷）；`mirror_ok: false` 的角色後續不得用水平翻轉產生反向動作。**必要**
6. 一張圖輸入（`--image`）時：設定稿身分對輸入圖過 2 的門檻，並在報告寫明「背面／側面為推論設計」（沿用 animation-states.md）。**必要**
7. 設定稿總頁 `sheet.png`（轉面＋表情＋色票排版，附角色名與尺寸格線）。**加分**（理由：美術拿去溝通用，但不影響管線）
8. 頁面字型樣式、標題裝飾。**無感**

## S-161 動作影格（`imagegen.py animate`）—— 必要（理由：spec 核心；會動且同一隻是驚豔時刻本體）

**命令形狀**：
```
imagegen.py animate --charsheet charsheet/charsheet.json --states idle,walk,run,jump,attack,hurt,death \
  [--fps idle=8,walk=10,run=12 ...] [--keys 2..4] --out anim/ --experimental --json
→ anim/<state>/{frames/*.png, keys/*.png, anim.json}, anim/gen-manifest.json
```
1. **關鍵姿勢走參考圖，中間格走本機補格**：每狀態 key 2–4 張，每張 `refs_sent` 含設定稿（正面＋該狀態朝向的視角）；中間格 `source: "inbetween"`、方法（timewarp／形變／像素模式的逐像素位移，**不得**是交叉淡化：雙影檢查——每格 α>0 面積 ≤ 相鄰 key 平均面積 × 1.15）。`anim.json` 逐格記 `source: key|inbetween`、`key_index`、`duration_ms`。**必要**
2. **身分跨狀態不漂**：每個 key 對設定稿質心過 S-160.2 門檻；所有格的配色（遮罩內 k-means 前 5）對 palette.json ΔE ≤ 6；像素模式：所有格色彩集合 ⊆ 調色盤（0 個新色）。**必要**
3. **腳底接地（不滑）**：`anim.json` 記 `contacts: [{foot, frames:[a,b]}]`（建造者偵測或標註；出題者以夾具答案比對：接觸區間端點誤差 ≤ 1 格）。接地期間該腳最低不透明像素：
   - 原地循環（in-place）：x 漂移 ≤ 1 px（像素 64 邏輯格）／≤ 0.5% 畫布高（高解析）；
   - 有位移（非原地）：腳的世界座標（影像 x + 宣告的 root motion）漂移同上門檻；
   - y 與地線差 ≤ 1 px。WALK-8 PASS、WALK-SLIDE 必 FAIL 並指出格號與滑移量。**必要**
4. **地線與重心**：所有接地格的最低像素 y 標準差 ≤ 1 px（地線穩定）；pivot y 與地線差 ≤ 1 px。alpha 加權重心：idle 水平標準差 ≤ 2% 畫布寬、垂直振幅 ∈ [0.5%, 4%]（有呼吸但不跳）；walk 垂直 bob 為每循環 2 個週期（FFT 主頻 = 2 ± 0）、振幅 ∈ [1.5%, 6%] 主體高；run 振幅 ≥ walk 且有騰空格（雙腳離地 ≥ 1 格）；walk **不得**有雙腳離地格。**必要**
5. **跳躍物理**：騰空格的重心 y 對二次拋物線擬合 R² ≥ 0.95、頂點在騰空區中段 ±1 格；起跳前 ≥ 1 格預備（重心下降）、落地後 ≥ 1 格壓縮（主體高 ≤ 站姿 97%）。JUMP-SYN PASS；把預備格刪掉的破壞版 FAIL。**必要**
6. **攻擊相位與事件格**：`anim.json` `events: [{name:"hit", frame:k, time_ms}]`；k = 武器接觸格（ATK-SYN k=5，誤差 0 格）；預備 → 揮擊 → 接觸 → 跟隨 → 恢復順序存在（motion.md）；若加 impact hold，只加在 k 且 manifest 記錄 ms（不套萬用值）。**必要**
7. **循環接縫**：loop 狀態（idle／walk／run，及宣告 loop 的 VFX）：d(末→首) ∈ [0.3, 1.5] × 相鄰格差中位數（d＝遮罩內平均 |Δ|＋重心位移）——既不跳也不重複；`qa_media.py --loop` 位置＋速度皆 PASS。WALK-DUPSEAM、WALK-JUMPSEAM 必 FAIL。非 loop 狀態（jump／attack／hurt／death）`loop: false`；hurt 末格回到 idle 首格相容（d ≤ 1.5× 中位數）；death 末格 hold、不回彈。**必要**
8. **共用 bbox／pivot**：全部狀態同畫布尺寸、同 pivot；每格 α>0 不碰畫布邊（邊緣 1 px 內 α=0 ≥ 99.9%，除非宣告出框特效層）；不得逐格重新置中（出題者以「重心軌跡對 bbox 中心的相關 < 0.95」判定沒被硬拉回中心——走路的重心應該有自然 bob）。**必要**
9. **時序合理**（C 類可校準）：idle 4–8 格 @ 6–10 fps；walk 6–12 @ 8–12；run 6–10 @ 10–15；attack 6–14 格且接觸格之前時長 ≥ 之後的 40%；`duration_ms` 允許逐格不同，各引擎匯出照逐格時長（見 S-163）。**必要**
10. **需要連續真實動作 → 先問**：`--route video` 或品質不足自動建議改影片時，**不得**自行呼叫；回 `E_APPROVAL_REQUIRED`＋預估（共通規則守衛）。**必要**
11. 8 方向或 4 方向朝向包（不對稱角色不鏡像）。**加分**
12. 每狀態 onion-skin 預覽頁。**加分**（理由：美術最常用的檢查方式）
13. key 與 inbetween 在預覽中顏色標記。**無感**

## S-162 透明 sprite 品質（`imagegen.py alpha --sprite` / 管線自動）—— 必要（理由：spec-13 實測原生透明有零星白點；遊戲裡一圈白邊直接不能用）

1. **無暈**：疊黑／白／品紅；α 0.5 等值線外 1–3 px 帶：疊黑外帶平均亮度 − 背景 ≤ 8；去預乘後半透明像素與最近 α=255 內部色 ΔE ≤ 20 的比例 ≥ 95%（同 acceptance-13 S-154.3）。SPR-HALO 擋、SPR-OK 過。**必要**
2. **無零星雜點**：主體以外 α>0 連通區面積總和 ≤ 主體 0.1%，且 **0 個** ≤ 4 px 的孤立連通區（宣告的 VFX 粒子層除外）；SPR-SPECK 清理後 17 點全除、主體像素（α≥128）變動 ≤ 0.05%。主體內非設計洞 ≤ 0.5%。**必要**
3. **預乘正確**：metadata `alpha_mode: straight|premultiplied`；straight → α=0 像素 RGB 清 0 或記錄保留理由，邊緣不變黑（ΔE 檢查同 1）；premultiplied → 100% 像素 R,G,B ≤ α；各引擎匯出設定與之相符（Godot 4 import `process/premult_alpha`、Unity `alphaIsTransparency`、Phaser／PixiJS `meta.premultipliedAlpha` 或 `alphaMode`）。SPR-PREMUL-LIE 必被擋（偵測：宣稱 straight 但 ≥ 98% 像素 RGB ≤ α 且邊緣去預乘後才吻合）。合成驗：以宣告模式疊中灰，與真值合成平均 |Δ| ≤ 2。**必要**
4. **尺寸、pivot、留白一致**：同一角色所有輸出同畫布；四周留白（主體 bbox 聯集到畫布邊）各邊 ≥ 1 px；pivot 在 metadata 明寫（像素座標，左上原點）。**必要**
5. **像素藝術模式**（`--pixel N` 或設定稿宣告）：
   - 網格：交付的 ×k 放大版每個 k×k 區塊單一顏色（容差 0，100% 區塊）；邏輯尺寸 = 宣告值；
   - 調色盤：整個角色（所有狀態、所有格）唯一色數 ≤ 宣告 N（預設 ≤ 16，上限 32）；
   - alpha：角色像素 α ∈ {0,255}（VFX 層可分級，依 pixel-art.md）；
   - 只用 nearest：放大、打包、翻轉（mirror_ok 時）、引擎匯出後色彩集合 ⊆ 原調色盤（**0 新色**）、1 px 描邊仍是 1 個邏輯像素寬；PIX-BLUR 必判「非網格／新色 N 個」。**必要**
6. 背景色鍵退路（原生透明不可用或判假透明時）：沿用 acceptance-13 S-154.5，自動挑與主體 ΔE ≥ 30 的背景色。**必要**
7. 去暈前後對照圖（疊黑放大 4×）。**加分**

## S-163 sprite sheet 與引擎匯出（`sprite_export.py --engine`）—— 必要（理由：spec 驚豔時刻「直接丟進 Godot 就能播」）

**命令形狀**：
```
sprite_export.py anim/ --anim-manifest anim/*/anim.json --out export/ \
  --engine godot4,godot3,unity,phaser-hash,phaser-array,pixi,aseprite [--pixel] [--max-size 2048] [--padding 2] [--extrude 1]
```
共通：每個引擎輸出都**重新解碼**每格 crop 並與來源格位元相同（含分級 alpha 與 α=0 下的 RGB 規則）；狀態名、格順序、逐格 `duration_ms`、`loop`、`events`、pivot 全部可從每種格式還原（出題者寫反向讀取器逐一比對）。每種格式的 `engine_load` 欄：`"tested:<engine version>"` 或 `"untested"`——沒真載入不得寫 tested。

1. **Godot 4 SpriteFrames `.tres`**（`format=3`）：
   - 標頭 `[gd_resource type="SpriteFrames" load_steps=N format=3 uid="uid://…"]`，N = ext_resource 數＋sub_resource 數＋1；`[ext_resource type="Texture2D" path="res://…" id="…"]`；每格 `[sub_resource type="AtlasTexture" id="…"]` 含 `atlas = ExtResource("…")`、`region = Rect2(x, y, w, h)`；`[resource]` `animations = [{"frames": [{"duration": d, "texture": SubResource("…")}], "loop": true|false, "name": &"idle", "speed": fps}]`。
   - 逐格時長：`speed` × `duration` 相對倍率還原的 ms 與 anim.json 差 ≤ 1 ms。
   - **解析檢查**：出題者的嚴格文字解析器（section 標頭、key = value、Godot Variant 字面值、id 參照全部存在、無重複 id、UTF-8 無 BOM）；**載入檢查**：Godot 4.x `--headless --script check_frames.gd` 載入、斷言動畫名、格數、speed、loop、每格 region、AnimatedSprite2D 播一輪不報錯。pixel 模式：產出的 `.import` 或專案設定 `texture_filter` 為 Nearest。**必要**
   - Godot 3（`format=2`，`SubResource( 1 )` 語法）：用本機 3.2 實測載入。**加分**（理由：舊專案仍多；但 spec 目標是現行 Godot）
   - 事件格：SpriteFrames 無事件欄 → 另出 `<name>.events.json` 或 AnimationPlayer／AnimationLibrary `.tres` method track；README 寫對應方式。**必要**（事件要能取得）
2. **Unity**：sheet PNG＋`<sheet>.png.meta`（YAML，`fileFormatVersion: 2`、32 hex `guid` 且每張不同、`TextureImporter`、`spriteMode: 2`、`spriteSheet.sprites[]` 每格 `name`、`rect {x,y,width,height}`、`alignment: 9`＋`pivot` 正規化、`spritePixelsToUnits`、像素模式 `filterMode: 0` 與 `textureCompression: 0`、`alphaIsTransparency`、Unity 2021+ 的 `internalIDToNameTable`／`nameFileIdTable` 一致）。**陷阱**：Unity rect 原點在**左下**——出題者以反向讀取器把 rect 轉回左上原點後 crop 必須與來源格位元相同。動畫時長與事件另出 JSON（或 `.anim`，加分）。YAML 解析通過即可，`engine_load: "untested"`。**必要**
3. **Phaser 3／PixiJS（TexturePacker JSON）**：
   - hash：`frames: {name: {frame:{x,y,w,h}, rotated:false, trimmed, spriteSourceSize:{x,y,w,h}, sourceSize:{w,h}, pivot?:{x,y}}}`，`meta: {image, size:{w,h}, scale, format:"RGBA8888"}`；array：`frames: [{filename, …}]`。
   - PixiJS：頂層 `animations: {state: [frame names…]}`；Phaser：另出 `anims.json`（`key`、`frames`、`frameRate` 或逐格 `duration`、`repeat: -1|0`）。
   - 出題者 JSON Schema 驗；**載入檢查**：headless Chromium（playwright）載入 Phaser 3.x 與 PixiJS 8.x（版本寫死、本機檔），對每個狀態播一輪：0 console error、每格 texture 尺寸正確、事件格回呼在第 k 格觸發。pixel 模式 Phaser `pixelArt: true`／Pixi `scaleMode: 'nearest'`。**必要**
4. **Aseprite JSON**：`frames`（hash 或 array）每格 `duration` ms；`meta.frameTags: [{name, from, to, direction:"forward"}]` 覆蓋全部狀態且不重疊；pivot 以 `meta.slices`（`pivot`）表示；事件以 tag `data` 或 slices 記錄並在 README 說明。**必要**（理由：像素美術常回 Aseprite 修格）
5. **metadata 逐狀態**：每狀態 `fps`（或逐格 ms）、`loop`、`events[]`、`pivot`、`alpha_mode`、`pixel_scale` 在每種格式（原生欄位或 sidecar）都存在；缺任一＝不過。**必要**
6. **打包**：頁 ≤ `--max-size`；padding ≥ 2；`--extrude` 時邊緣延伸不改 crop 內像素；格超過一頁時多頁，各引擎格式的多頁表示正確（Godot 多個 ext_resource；TexturePacker multipack `meta.related_multi_packs` 或分檔）。**必要**
7. 一鍵 Godot 範例專案（`project.godot`＋場景播 4 狀態）。**加分**（S-168 會用到）
8. 檔案命名風格。**無感**

## S-164 道具／圖示／UI 一致風格組（`imagegen.py iconset`）—— 必要（理由：spec 驚豔時刻「外加同風格的道具圖示」；一組裡有一個風格跑掉就不能用）

**命令形狀**：`imagegen.py iconset --items "劍,盾,藥水,鑰匙,卷軸,寶石,弓,靴" --style-token style.json --grid 64 [--pixel] --out icons/`；`style.json` = {light_deg, outline_px, outline_hex, palette, grid, safe_margin, shading: "cel|soft"}。
1. **同格線**：全部 = grid×grid、RGBA；主體 bbox 在安全邊內；bbox 面積佔比的變異係數 ≤ 0.25 且每個 ∈ [35%, 85%]；ICON-8-BAD #6 被指出。**必要**
2. **同描邊**：描邊像素（主體外緣 ring、顏色 ΔE ≤ 5 於 `outline_hex`）以距離轉換量寬度：每個圖示中位數與 token 差 ≤ 0.5 px（高解析）／完全相等（像素模式）；ICON-8-BAD #3 被指出。**必要**
3. **同光源**：每個圖示對遮罩內亮度擬合平面 L = a·x + b·y + c，光向 = atan2(−b, −a)；平面擬合 R² < 0.05（扁平無明暗）→ 該圖示記 `light: "n/a"` 不判；其餘：圓統計標準差 ≤ 20°，每個與 token 差 ≤ 30°。差 ≥ 60° → 指出索引。**必要**
4. **同調色／飽和**：每個圖示 HSV 平均 S、V 的變異係數 ≤ 0.20；像素模式全組色 ⊆ token 調色盤；ICON-8-BAD #7 被指出。**必要**
5. **離群只修那一個**：指出離群後 `--fix` 只重生成／修正離群索引，其餘圖示 sha256 不變；manifest 記錄。**必要**
6. 每個圖示都帶同一 style token 於 prompt 與 manifest（`style_token_sha`）；跨圖示 refs_sent 含已接受的第一個圖示作風格參考。**必要**
7. 1× 可讀性：64 px 與 32 px（nearest 縮）下剪影可辨：出題者以 8 類閉集分類（CLIP 零樣本或評審）正確 ≥ 7/8。**加分**
8. UI 九宮格面板／按鈕同風格。**加分**
9. 圖示檔名排序方式。**無感**

## S-165 可平鋪材質與地圖素材（`imagegen.py tile`）—— 必要（理由：環境美術最基本需求；一條縫在地圖上會重複幾百次）

**命令形狀**：`imagegen.py tile texture --prompt "苔石板" --size 256 --out tex/`；`imagegen.py tile tileset --prompt "草地到泥土" --grid 16|32 --set blob47|wang16|min13 --out tiles/`。
1. **四邊接縫**：令 c = 原圖相鄰欄（列）平均 |Δ| 的中位數；wrap 差 e_x = mean|T[:,0] − T[:,−1]|、e_y 同理：e ≤ 1.5 c；在 2×2 拼接圖上，接縫線的 Sobel 量值中位數 / 內部中位數 ≤ 1.3；頻譜十字（拼接圖 FFT 軸線能量 / 鄰近 ≤ 1.5）。TEX-OK 過、TEX-SEAM 擋並指出軸。**必要**
2. **無低頻光照梯度**：左右半、上下半平均亮度差 ≤ 3/255（否則 3×3 拼起來成棋盤明暗）。**必要**
3. **修縫不糊**：修正後高頻能量（Laplacian 方差）≥ 原圖 85%；改動限於邊緣帶或以 wrap-aware 方式全圖一致處理並記錄。**必要**
4. **tileset 完整**：`--set` 宣告的變體全部存在（blob47＝47、wang16＝16、min13＝9 宮＋4 內角）；每塊 = grid×grid、對齊網格（像素模式 nearest、色 ⊆ 調色盤）；依 set 規則所有應相容的邊對：邊緣 1 px 欄平均 |Δ| ≤ 4；出題者用自動拼圖器以隨機地形（20×20、3 個種子）鋪圖，0 個不相容邊。附 Godot 4 TileSet `.tres`（terrain bits）或 Tiled `.tsx`：**加分**。**必要**（完整與相容）
5. 3×3 拼接預覽圖隨附。**必要**（理由：使用者唯一會看的驗收方式）
6. 法線圖／高度圖。**加分**
7. tileset 頁面排列順序。**無感**

## S-166 VFX sprite（`imagegen.py vfx`）—— 加分整體，條目內標（理由：spec 列出但非驚豔時刻必需；做了必須對）

**命令形狀**：`imagegen.py vfx --kind explosion|magic|hit|pickup --loop|--oneshot --frames 8..16 --size 96 [--via pixelfx] --out vfx/`。
1. **alpha**：分級 alpha 保留（發光區 α ∈ [1,254] 的像素 ≥ 10% 的 α>0 面積）；不得二值化；疊黑／白無暈（S-162.1）。**必要**（做了就要對）
2. **加法混合預覽**：metadata `blend: "add"|"alpha"`；`add` 時另出預乘／黑底版本，疊在深色測試場景以 add 合成：α=0 處貢獻 = 0（RGB=0），無矩形框（框邊 2 px 平均亮度增量 ≤ 1）。預覽 GIF/APNG 各一。**必要**
3. **一次性 vs 循環**：oneshot 首格 α 總和 ≤ 峰值 5%（從無到有）、末格 ≤ 峰值 2%（完全消散，不截尾——export.md）；loop 依 S-161.7 接縫門檻。VFX-BOOM／VFX-ORB 正對照過、截掉最後 3 格的 VFX-BOOM 擋。**必要**
4. **格數預算**：每個 VFX ≤ 16 格（像素）／≤ 32 格（高解析），單頁 ≤ 1024²；manifest 記 `frame_budget`。超過 → 提議降格（時間取樣）而非靜默截斷。**必要**
5. 經 pixelfx 技能或既有 fx 效果產生時記 provenance（技能名、效果 id、版本）；與角色攻擊 `hit` 事件對位的合成預覽。**加分**
6. 粒子顏色可調色換色（recolor）。**加分**

## S-167 關鍵格 → 影片（`imagegen.py kf-video`）—— 必要（理由：唯一可能花錢的路徑；守衛錯一次就不可逆）

**命令形狀**：`imagegen.py kf-video --first k0.png --last k1.png --refs refset.json --route grok|fal|local [--approve-video <id>] --out kv/`。
1. **守衛測試**：沒有 `--approve-video`（或 id 不符本次預估、或過期）→ FAKE-GROK／FAKE-FAL／API-SENTINEL 計數全 = 0、`grok_client.py`／`fal_video.py` 未被 import 執行網路（psutil＋sitecustomize 監看子孫行程）、非 0 結束 `E_APPROVAL_REQUIRED`，訊息含預估秒數／費用與本機替代。母行程 env 有 `XAI_API_KEY`／`FAL_KEY` 假值也不得自動走。**必要**
2. 有核准：只呼叫一次（重試照 acceptance-13 S-150.8 上限），首末格與參考圖都實際送出（manifest `refs_sent`、`first_frame_sha`、`last_frame_sha`）；回來的影片過既有 gif_pipeline／qa 與 S-160.2 身分門檻。**必要**
3. **本機能做的直接做**：`--route local`（2.5D 運鏡、補格、合成）不問、不連網（NETGUARD = 0）。**必要**
4. 首格吻合：影片第 1 格與 `--first` SSIM ≥ 0.90（路線不支援首格鎖定時能力表寫 false 並報告）。**加分**

## S-168 示範與驗收（`imagegen.py demo game`）—— 必要（理由：spec 的交付證明）

**示範包內容**（`demo/ice-fox/`，原創角色，不仿任何既有遊戲）：
- `charsheet/`：4 視角、6 表情、配色卡、`charsheet.json`、`refset.json`；
- `anim/`：idle、run、attack、hurt 4 狀態（另可加 walk／jump／death），每狀態 frames＋GIF/APNG 預覽＋`anim.json`；
- `export/`：Godot 4（`.tres`＋sheet＋events）、Phaser（hash JSON＋anims.json）、另含 PixiJS／Aseprite／Unity 任一為加分；
- `godot-project/`：`project.godot`＋一個場景，headless 載入並播完 4 狀態（出題者執行）；`phaser-demo/index.html`：headless Chromium 播 4 狀態、0 console error；
- `icons/`：8 個道具圖示＋style.json；`tex/`：1 張可平鋪材質＋3×3 預覽；
- `README.md`：怎麼開、每個檔案是什麼、`engine_load` 狀態、路線與 fallback、生成張數、未做／未驗證事項；`gen-manifest.json` ledger；`originality` 聲明。
1. 上列全部存在且通過 S-160..S-165 各條必要門檻（出題者用同一驗收腳本跑示範包，0 項 FAIL）。**必要**
2. live 生成張數 ≤ 40（留 20 張給 holdout 與重試）；從乾淨狀態（快取清空）牆鐘 ≤ 30 分鐘。**必要**（張數）／**加分**（時間）
3. 兩軸：技術軸評審團（瑕疵題）對破壞版勝；好看軸使用者抽查會動的 GIF 8 對（含隱藏對照），Wilson 下界記錄。**必要**（技術軸）
4. 重跑決定性：快取命中時重跑 0 次生成、輸出 sha 相同。**必要**

---

## 看完整成品（出題者最後執行，live；以「遊戲美術會不會直接 ship」的眼睛看；獨立評審＋使用者各看一次）
讀者只看：設定稿總頁、4 狀態在遊戲畫面尺寸（1×、2×、3× nearest）循環播放的 GIF、Godot 執行截錄、圖示組總覽、材質 3×3。不看程式與本卷。

| 項目 | Kano | 理由 |
|---|---|---|
| **會 ship**：遊戲美術說「這組 sprite 可以直接放進 vertical slice」，不是「拿來當參考再重畫」 | 必要 | spec 目的 |
| **從頭到尾同一隻**：轉面、表情、4 個狀態、圖示上的劍——配色、比例、疤的位置、配件全一致，沒有某一格突然換臉或換武器手 | 必要 | 驚豔時刻「角色從頭到尾是同一隻」 |
| **1× 剪影可讀**：在 64 px 原尺寸、純黑剪影下仍分得出 idle／run／attack／hurt 是哪個動作，看得出拿的是劍 | 必要 | 遊戲裡玩家只看 1× |
| **腳是踩在地上的**：run／idle 不溜冰、不飄、不抖；attack 有重心前移與恢復；hurt 有被打的方向感 | 必要 | SKILL.md 物理預設 |
| **循環看不出接點**：連播 10 次不卡、不跳、不閃 | 必要 | 循環是 sprite 的基本盤 |
| **攻擊打中那一格是對的**：事件觸發時劍確實在目標上（Godot／Phaser 播放中觀察命中特效時間點） | 必要 | 遊戲手感 |
| **邊緣乾淨**：放在深色、淺色、遊戲地圖背景上都沒有白邊、灰點、半透明碎屑 | 必要 | spec-13 實測的已知瑕疵 |
| **像素風是真的像素風**：網格一致、沒有糊邊、沒有混入半調色；不是「縮小的 AI 插畫」 | 必要 | pixel-art.md；使用者指定像素風時 |
| **圖示像同一個遊戲的**：同光源、同描邊、同大小，放進同一個背包欄不突兀 | 必要 | S-164 |
| **材質鋪滿一整屏看不出縫**，也沒有明顯重複的「同一塊石頭」節奏 | 必要 | S-165 |
| **原創**：讀者不會說「這是 XX 遊戲的角色」 | 必要 | 共通規則 |
| 讀者想看更多狀態（dash、block）或直接拿去開專案 | 加分 | 外溢價值 |
| 有讓人記住的設計細節（冰劍的冷光、尾巴的跟隨動作） | 加分 | 驚豔 |
| 設定稿頁面排版 | 無感 | 美術看內容不看版面 |

## 不算通過的樣子
- 點名既有遊戲角色卻照做；或 prompt／檔名裡出現該角色名；或對原創請求亂拒絕。
- 未核准就呼叫影片模型（含因為 env 有 key 就走）。
- 「Godot 可載入」只靠自己的解析器，沒有真引擎載入卻寫 tested；Unity rect 用左上原點。
- 逐格依 bbox 置中，造成走路原地漂浮；或用水平翻轉做出疤換邊的反向動作。
- 中間格是交叉淡化（雙影）；像素風補格出現新色或半透明描邊。
- 透明 sprite 有白點／白邊、宣稱 straight 實為預乘。
- 循環首末格重複或跳點卻標 seamless；一次性 VFX 末格還沒消散就截掉。
- 能力表沒有的功能（原生 GIF、遮罩、尺寸參數）被寫成用了。
