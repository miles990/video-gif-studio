# Batch 2 驗收答案卷 — video-gif-studio 輕量交付（W5 過關 + 像素風 X 展示）

- 角色：獨立驗收者（Claude Opus），建造者為 Codex。本卷寫於建造前，**不修改也不放寬 spec**；本卷與 spec 有衝突時，以較嚴者為準。
- 日期：2026-11-22（Asia/Taipei）。建造基準提交為 `064c675`（記作 `BASE`）。
- **Batch 1 答案卷（`wow/batch1/acceptance.md`）全部規則仍有效**：1.1–1.6 的不變式、C1–C3 合成對照組、S-1 到 S-7 的必須和禁止條件都要守住。本卷只新增規則或收緊門檻；Batch 1 的條文若和本卷衝突，以本卷為準（例如 S-1 的 `magenta_share_max ≤ 0.02` 在 Batch 1 的 chibi 實作沒有達成，本批要補上）。
- 成本：$0。驗收全程以 `env -u XAI_API_KEY -u FAL_KEY` 執行，不得呼叫 Grok、fal 或其他付費 API。驗收輸出一律寫到 `/tmp/vgs-acc2/…` 的新目錄，不寫入 repo。

## 0. 樣本基線（驗收者於 2026-11-22 在本機以 BASE 實測）

Python：`/home/box/.codex/skills/video-gif-studio/.venv/bin/python`（repo 內沒有 `.venv`，下文記作 `$PY`）。

### 0.1 保留（held-out）真實影片，本機可用、成本 $0

| 代號 | 路徑 | 規格 | 邊框中位色／信心／飽和度 `(max−min)/max` | 性質 |
|---|---|---|---|---|
| chibi（可見樣本） | `examples/chibi-running-dash/source.mp4` | 720×720、24 fps、145 幀、6.04 s | (251,1,248)／1.000／0.996 | 飽和洋紅；首幀等於尾幀生成；尾端定格 |
| robot | `examples/robot-wave-no-reference/source.mp4` | 960×960、24 fps、145 幀、6.04 s | (250,3,248)／1.000／0.988 | 飽和洋紅；**不回位**的非循環片 |
| seated | `examples/stylized-redraw-seated/final.mp4` | 640×640、30 fps、299 幀、9.97 s | (243,234,219)／1.000／**0.099** | 低飽和米黃純底 |
| idle | `/workspace/wizardx07-dist/agent-avatar/media/idle_cute.mp4` | 784×1170、24 fps、124 幀、5.17 s | (240,235,232)／1.000／**0.033** | 低飽和米白純底；直式；高度在像素化後可能是奇數 |
| gufeng | `/workspace/liu/gufeng.mp4` | 720×1280、30 fps、361 幀、12.03 s | (96,89,90)／**0.127**／0.073 | 複雜、非純色背景；直式 |

### 0.2 BASE 的 `vgs make <video> --out <new>`（不加任何旗標）

| 代號 | exit | 結果 | 量測（`measure2.py`，見 §2） |
|---|---|---|---|
| chibi | 0 | 去背；93 幀／3.88 s；`loop FAIL: speed mismatch` | `ring_opaque_max 0`、**`magenta_share_max 0.3481`（第 54 幀）**、`opaque_max 0.136` |
| robot | 0 | 去背；145 幀／6.04 s；`loop FAIL`（position 與 speed 都 FAIL） | `ring 0`、**`magenta_share_max 0.0399`（第 55 幀）** |
| seated | **1** | stderr 只有 `No visible foreground`；留下空的輸出目錄 | 色度距離把整個主體判成背景 ← §1.2 的直接反例 |
| idle | **1** | 同上，`No visible foreground` | 同上 |
| gufeng | 0 | 未去背，非透明交付；360 幀／12.03 s；**41.16 MB**；牆鐘 24.2 s | `ring 1.0` |

### 0.3 驗收者的離線探測（只作佐證，不是建造者實作的規格）

- **chibi 的自然回位點確實存在。** 以 key 去背後在 320 寬下逐一嘗試結尾幀，再用 `qa_media.qa` 判斷：結尾落在第 84 到 90 幀（3.50 到 3.75 s，位於最後移動幀 3.42 s 之後）時，loop 的 position 與 speed 都是 PASS，seam_ratio 約 0.15。結尾落在第 70 到 74 幀（2.92 到 3.08 s）時 loop 也會 PASS，但那會**切掉收招**，屬於 §1.1 反例 B。BASE 的 3.88 s 結尾則是 speed FAIL（ratio 0.088 到 0.18 附近）。
- **robot 沒有任何可通過的接縫。** 結尾落在第 100 到 145 幀時，`position_pass` 全部是 false（seam_ratio 3.9 到 6.5）。這是誠實的反例：預設流程只能如實報 `loop FAIL`。
- **以連通判斷找出的「不與邊框連通」的鍵色島**（以 key 色度距離 < tolerance+softness 判定）：chibi 第 54 幀佔「前景＋島」的 **34.8%**（劍弧內的封閉洋紅袋）；robot 第 33 幀佔 **3.7%**。所以在 robot 上改用全域色鍵時，同樣要觸發內島警告。

## 1. Batch 2 新增的領域規則、不變式與反例

### 1.1 迴圈接縫：自動偵測自然回位點 vs. 默默 crossfade

- **規則**：`--loop auto`（預設）只能**裁切**。它在動作結束附近搜尋一個真實存在的來源幀當結尾，條件是首尾接縫同時通過 `qa_media` 的 position 門檻（`seam < 0.5` 或 `seam ≤ 2×median_step`）和 speed 門檻（`0.5 ≤ ratio ≤ 2`）。輸出的每一幀都必須是來源幀本身，內容不能改動。
- **為什麼自然回位點是誠實的**：輸出幀的集合只是來源的一段連續子區間，觀眾看到的每一幀都真實存在，迴圈本身就是素材固有的性質；只要把裁切區間記錄下來，任何人都能從 `source_indices` 重現。
- **為什麼未要求的 crossfade 或倒放違反 Batch 1 §1.4**：crossfade 會合成出來源沒有的半透明疊影幀（在 GIF 的二值透明下，常出現殘影或鬼影的硬邊）。倒放（ping-pong）會讓動作的物理方向反轉，例如揮劍的動作變成收劍。兩者都會讓 loop QA 變成 PASS，卻掩蓋了「素材本身不循環」這個事實，等於用 QA 分數換來對使用者的不實陳述。所以只有使用者明確傳了 `--loop crossfade` 才可以混合，而且 manifest 與摘要必須同時揭露方法、混合幀數或秒數，以及受影響的區間。
- **不變式**：
  1. 預設輸出的 `source_indices` 必須嚴格遞增、連續（步長全為 1，或與 `gp.timing` 的抽幀規則一致），而且不得出現反向段。
  2. 自動選出的結尾不得早於「最後移動幀」（也就是收招動作要保留）。結尾之後保留的靜止 guard 不得超過 0.5 s（承接 Batch 1 §1.3 的邊界）。
  3. 找不到符合條件的點時，必須退回不做迴圈處理（保留原本的尾端裁切結果），並如實報 `loop FAIL`，同時寫出原因（position 或 speed）。
- **反例 A**：robot 的 position 本來就不可能通過，輸出卻是 `loop PASS`。查證發現加入了 crossfade 或倒放，manifest 和摘要都沒有揭露。→ FAIL。
- **反例 B**：為了取得 PASS，把結尾選在 chibi 的 2.92 到 3.08 s，切掉收招。→ FAIL。
- **反例 C**：沒有傳 `--loop crossfade`，manifest 卻出現 `crossfade`、`blend`、`reverse`、`pingpong` 等字樣，或輸出幀和來源幀逐像素比對不一致（重新解碼來源、套用相同的 key 與縮放後比較，容許 GIF 量化誤差）。→ FAIL。

### 1.2 低飽和純底：色度距離會丟掉亮度，自動去背會毀掉主體

- **規則**：`vgs.py` 的色鍵距離是「RGB 減去自身平均後的色度向量」距離。這個距離會把亮度資訊去掉：米白 (240,235,232) 的色度向量接近 0，和白、灰、黑、膚色、淺色衣服的色度向量幾乎一樣，因此整個主體都會落在容差內被挖空。BASE 對 seated 與 idle 輸出 `No visible foreground` 並以 exit 1 結束，就是這個原因。
- **不變式**：自動色鍵要求邊框均勻穩定（`confidence > 0.95`），**而且**鍵色飽和度 ≥ 0.35，兩者缺一不可。低於 0.35 時一律不自動去背。manifest 須記錄 `key_saturation`（或同義欄位）及實際值，摘要須寫出原因（例如「背景為低飽和純色（飽和度 0.10 < 0.35），未自動去背；這是非透明交付。若確定要去背，請加 `--key F3EADB`」）。`--key` 後面附的 HEX 須是實測估得的邊框色，讓使用者可以直接複製。
- **邊界**：飽和度的定義必須寫進 manifest 或 `--help`（例如 HSV 的 S，或 `(max−min)/max`）。chibi 與 robot（約 0.99）必須自動去背；seated（約 0.10）與 idle（約 0.03）必須不去背。C3 綠幕（飽和度 1.0）仍可以自動去背。
- **明確 `--key` 路徑的不變式**：使用者對低飽和底傳 `--key <HEX>` 時，不得以未捕捉例外或英文的 `No visible foreground` 收場。可接受的結果有兩種：(a) 產出 GIF，且主體保留（中段任一幀的不透明比例 ≥ 0.05）；(b) exit ≠ 0，並給出人話錯誤，內容包含發生什麼（鍵色和主體太接近，會挖空主體）、影響（不寫入檔案，或輸出目錄保持空白）、下一步。不論哪種結果，都不得留下非空的半成品目錄卻沒有說明。
- **反例**：seated 不帶旗標時 exit 1，訊息是 `No visible foreground`，並留下空目錄。這是 BASE 的現況，本批必須消除。另一個反例：seated 被自動去背，主體只剩輪廓碎片，摘要卻寫「已去背」。

### 1.3 全域色鍵＋內島警告 vs. 只移除連通區時留下的受困背景

- **兩種失敗互為對照**：
  - **只移除連通區時留下的受困背景（chibi 第 54 幀）**：揮劍時劍弧與身體圍出一塊封閉的洋紅區域。那塊是**背景**，只是剛好被前景包住。只移除和邊框連通的背景會把它留成不透明的洋紅色塊（BASE 的 `magenta_share_max = 0.3481`），違反 S-1 的 `≤ 0.02`。
  - **全域色鍵造成的挖空（C1 的洋紅內框）**：C1 白方塊裡的洋紅框是**前景設計的一部分**。全域色鍵會把它挖成洞。
  - 單看像素無法分辨這兩種情況（兩者都是「不與邊框連通的鍵色區塊」），必須由人判斷語意。因此 spec 的折衷是：**預設全域去背，以滿足 `≤ 0.02`；一偵測到內島就大聲警告；另提供 `--keep-interior-key` 讓使用者改回保留。**
- **不變式**：
  1. 預設輸出中，chibi 與 robot 的 `magenta_share_max ≤ 0.02`，且 `ring_opaque_max ≤ 0.01`。
  2. 只要偵測到內島（例如面積比例 > 0.1% 的不透明候選像素，門檻寫入 manifest），摘要就須在**終端輸出中**印出警告，內容包含最大面積比例、對應幀號，以及 `--keep-interior-key` 的完整用法。manifest 須有對應欄位（例如 `interior_key_islands: {max_share, frame, action: "removed"}`）。
  3. 加上 `--keep-interior-key` 時，內島須保留：C1 的內框不透明，chibi 第 54 幀的封閉洋紅袋也會保留（此時 `magenta_share_max` 會回到約 0.3，這是預期行為）。摘要須寫明「已保留內部鍵色區，殘留鍵色比例 X」，不得同時宣稱 `≤ 0.02` 達標。
  4. 不得用「調高 `magenta_share` 量測門檻」或「把劍光一起當背景刪掉」的方式達標。劍光（亮粉紫色、非背景色）必須保留，以 contact 或 preview 圖人工比對第 54 幀附近的劍光是否仍在。
- **反例 1**：預設輸出的 chibi `magenta_share_max ≤ 0.02`，但摘要和 manifest 都沒有任何內島警告。這就是默默挖空。→ FAIL。
- **反例 2**：在 BASE 的 `apply_key_connected` 中，`if interior.any() and False:` 讓 `punched` 永遠為 False，所以警告永遠不會出現。建造後若仍有任何類似的「條件寫死為 False」的死碼，即使測試全過也判 FAIL。
- **反例 3**：`vgs qa` 只檢查邊框 4 px，於是整幀中央有大片洋紅的 GIF 也拿到 PASS。spec 要求 `vgs qa` 和 `vgs make` 同時回報 `border_opaque_max` 與殘留鍵色比例。

### 1.4 像素風：最近鄰縮放與無抖動的限制色盤

- **規則**：像素風的本質是「每個邏輯像素是一個硬邊方塊，顏色來自少量固定色盤」。
  - 降採樣到網格（預設 96 px 寬）時使用 `NEAREST`（或者先用面積平均取色、再做無抖動量化也可以，但**放大**一律用最近鄰）。不得在放大時使用 Lanczos、bilinear 或 bicubic。這些插值會在方塊邊緣產生中間色，邊緣變糊，也會讓色盤膨脹。
  - BASE 的 `gif_pipeline.load_frames` 降採樣時使用 `LANCZOS`。若 `--pixel` 走同一路徑，必須證明最終網格仍然只用限制色盤（見下面的量測方式）。
  - 量化時一律不抖動（`Dither.NONE`）。Floyd-Steinberg 抖動會在平坦色塊中撒點，放大後變成雜訊格紋。
- **不變式（可量測）**：設放大倍率為 s、網格大小為 w×h：
  1. 每幀解碼後的尺寸恰好是 (w·s)×(h·s)，s 為整數。在預設情況下，w·s ≥ 288，且 w = 96（`--pixel-width` 指定時以指定值為準）。
  2. **方塊一致性**：把每幀切成 s×s 的方塊，每個方塊內的 RGBA 值完全相同（違反的方塊數 = 0）。
  3. **色盤上限**：整個 GIF 所有幀中，不透明像素的相異 RGB 數量 ≤ `--colors`（預設 32），透明另占 1 個索引。
  4. 透明邊緣也是硬邊：alpha 只有 0 或 255（GIF 本來就是如此）；sprite 的 PNG 也只能有 0／255 兩種 alpha，不得出現半透明的羽化邊。
- **反例**：GIF 的不透明相異色超過 32 種（例如沿用 `encode()` 的 255 色 median cut，卻自稱 32 色）；放大後出現 1 px 寬的中間色帶；用 `--pixel-scale 3` 卻輸出 290 px 寬（不是整數倍）；MP4 為了湊偶數高度而用 bicubic 縮放（應改用補邊）。

### 1.5 X 用 MP4 的邊界

- H.264、`yuv420p`，寬與高都必須是偶數。idle 是直式影片，網格高度約為 96×1170/784 ≈ 143（奇數），放大 3 倍後是 429，仍是奇數。正確作法是**補邊**（在深色底上加 1 px 列），不得用非最近鄰的縮放修正尺寸。
- 合成到深色底後，畫面中不得殘留棋盤格或洋紅底板。
- 時長 8 到 15 s 是透過重複完整迴圈達成（`--loop-count`）。不得把單次迴圈拉慢來湊時長，因為那會改變速度，違反 Batch 1「不得改 FPS」的精神。

## 2. 共用準備（驗收者執行）

```sh
cd /workspace/src/video-gif-studio
PY=${PY:-/home/box/.codex/skills/video-gif-studio/.venv/bin/python}   # 以 README 寫法為準
A=/tmp/vgs-acc2; rm -rf $A; mkdir -p $A
CHIBI=examples/chibi-running-dash/source.mp4
ROBOT=examples/robot-wave-no-reference/source.mp4
SEATED=examples/stylized-redraw-seated/final.mp4
IDLE=/workspace/wizardx07-dist/agent-avatar/media/idle_cute.mp4
GUFENG=/workspace/liu/gufeng.mp4
export -n XAI_API_KEY FAL_KEY; alias vgs="env -u XAI_API_KEY -u FAL_KEY $PY scripts/vgs.py"
sha256sum examples/*/final.gif > $A/final-gif.before.sha256
# 依 Batch 1 §2 產生 C1、C2、C3，放在 $A/
```

基線雜湊（BASE，驗收者已記錄）：

```
ef52534aa867baf2d14ff04f12eb0c9fc61dfefe8b757e2f419ebf3ca88038a0  examples/chibi-running-dash/final.gif
90ae27fa9db6673d96b02325b0c721c9a1ec4b6caafb449955b94e2e887f4586  examples/robot-wave-no-reference/final.gif
ad60a4a17dea967cac52780631046888872a8a5c08f9b399a251116ee23c110b  examples/seated-leg-switch/final.gif
```

`$A/measure2.py`（放在 `/tmp`，不放進 repo）。它擴充了 Batch 1 的 measure，加上第一個透明幀、各幀不透明比例的最小值與最大值，以及洋紅殘留最嚴重的幀號：

```python
import sys, numpy as np
from PIL import Image, ImageSequence
g = Image.open(sys.argv[1]); op, ring, mag = [], [], []
for f in ImageSequence.Iterator(g):
    a = np.array(f.convert('RGBA')); al = a[..., 3] > 0
    op.append(al.mean())
    ring.append(np.concatenate([al[:4].ravel(), al[-4:].ravel(), al[:, :4].ravel(), al[:, -4:].ravel()]).mean())
    c = a[..., :3].astype(int)
    m = (c[..., 0] > 180) & (c[..., 2] > 180) & (c[..., 1] < 90) & al
    mag.append(m.sum() / max(al.sum(), 1))
print(dict(size=g.size, frames=g.n_frames, loop=g.info.get('loop'), opaque_min=round(min(op), 3),
           opaque_max=round(max(op), 3), ring_opaque_max=round(max(ring), 4),
           magenta_share_max=round(max(mag), 4), mag_argmax=int(np.argmax(mag))))
```

`$A/pixelcheck.py <gif> <scale> <colors>`：

```python
import sys, numpy as np
from PIL import Image, ImageSequence
g = Image.open(sys.argv[1]); s = int(sys.argv[2]); k = int(sys.argv[3])
bad, cols, alphas = 0, set(), set()
for f in ImageSequence.Iterator(g):
    a = np.array(f.convert('RGBA')); H, W = a.shape[:2]
    assert H % s == 0 and W % s == 0, f'size {W}x{H} not multiple of {s}'
    b = a.reshape(H // s, s, W // s, s, 4)
    bad += int((b != b[:, :1, :, :1]).any(axis=(1, 3, 4)).sum())
    alphas |= set(np.unique(a[..., 3]).tolist())
    op = a[a[..., 3] > 0][:, :3]; cols |= set(map(tuple, op.tolist()))
print(dict(size=g.size, frames=g.n_frames, nonuniform_blocks=bad, opaque_colors=len(cols),
           alpha_values=sorted(alphas), pass_=bad == 0 and len(cols) <= k and alphas <= {0, 255}))
```

## 3. S 條目驗收

判定方式：每一項「必須」都成立才算 PASS；出現任何一項「禁止」即 FAIL。證據（指令、stdout／stderr、exit、量測輸出）由建造者或協調者存放到 `wow/batch2/evidence/`，驗收者不寫入 repo。

### S-8 旗艦 loop 通過 QA（`--loop auto` 預設，誠實的接縫）

- **指令**：
  ```sh
  vgs make --help | grep -nE -- "--loop|auto|crossfade|off"
  vgs make $CHIBI --out $A/s8; echo "exit=$?"
  $PY $A/measure2.py $A/s8/animation.gif
  $PY scripts/qa_media.py $A/s8/animation.gif --out $A/s8_qa; echo "qa exit=$?"
  $PY -c "import json;m=json.load(open('$A/s8/manifest.json'));print({k:m[k] for k in m if 'loop' in k or 'tail' in k});i=m['source_indices'];print(len(i),i[:3],i[-3:],all(b>a for a,b in zip(i,i[1:])))"
  grep -nE '"loop"' -A12 $A/s8_qa/report.json | grep -E 'level|position_pass|speed_pass|speed_ratio|seam_ratio'
  vgs make $ROBOT --out $A/s8_robot; echo "exit=$?"
  vgs make $ROBOT --out $A/s8_robot_xf --loop crossfade; echo "exit=$?"
  grep -rniE "crossfade|blend|reverse|ping" $A/s8/manifest.json $A/s8_robot/manifest.json; echo "hits=$?"
  ```
- **必須**：
  1. `--help` 中列出 `--loop`，至少包含 `auto`（預設）與 `crossfade`。最好也提供 `off`；若提供，須在 help 說明其行為。
  2. chibi：exit 0；獨立執行的 `qa_media` 中，**`loop` 等級為 PASS**（`position_pass` 與 `speed_pass` 都為 true）。依 §0.3 的探測，合理的結尾約落在 3.50 到 3.75 s（輸出長度約 84 到 90 幀）。實作找到其他點也可以，只要符合下列第 3、4 項。
  3. 結尾不早於最後移動幀（manifest 的 `last_detected_motion_source_seconds`，約 3.42 s）。最後移動幀之後保留的靜止時間 ≤ 0.5 s。殘留的 freeze WARN 段不得覆蓋原本 3.54 到 6.04 s 的長靜止。
  4. manifest 記錄迴圈處理：方法（`auto-trim` 或同義詞）、搜尋區間、選定的結尾幀與秒數、該點的 position／speed 量測值（`seam_ratio`、`speed_ratio`），以及原時長與新時長。`source_indices` 嚴格遞增，且不出現反向段。
  5. chibi 的摘要可寫「loop 量測通過（未經視覺核准）」，但必須保留「視覺核准：未評估，需人看」。
  6. robot（預設）：如實報 **`loop FAIL`** 並寫出原因（position）；exit 碼依 Batch 1 慣例（loop FAIL 本身不強制非零，但摘要必須照寫）。manifest 須記錄「搜尋過，未找到自然回位點」及搜尋區間。`grep` 不得命中 crossfade、blend、reverse 或 ping（`hits=1`）。
  7. robot 加上 `--loop crossfade`：若產出成功，摘要**和** manifest 都須揭露「已混合接縫」、混合幀數或秒數，以及受影響的來源區間；摘要不得寫「無縫」或「seamless」，只能寫「loop 量測通過（經 crossfade 處理，未經視覺核准）」之類的字樣。若實作選擇不支援 crossfade，`--help` 不得列出這個選項，否則就必須能用。
- **禁止**：預設路徑出現 crossfade、倒放、插幀或重新排序；robot 預設輸出 `loop PASS`；為了讓 loop 通過而切掉收招（結尾早於約 3.42 s）；用 `--holds` 壓掉 WARN；摘要寫「seamless」「無縫」「loop OK」或「視覺通過」。
- **非退化**：S-1 的所有量測（尤其是 `ring_opaque_max ≤ 0.01`、`loop == 0`、`alpha_mismatch_pixels == 0`、牆鐘 ≤ 15 s）在 `$A/s8` 上仍須成立。

### S-9 全域鍵＋內島警告、低飽和保護、QA 回報殘留鍵色

- **指令**：
  ```sh
  vgs make --help | grep -nE -- "--key|--keep-interior-key"
  vgs qa --help
  # 9a 飽和洋紅：全域去背加警告
  vgs make $CHIBI --out $A/s9_chibi > $A/s9_chibi.txt; echo "exit=$?"; cat $A/s9_chibi.txt
  $PY $A/measure2.py $A/s9_chibi/animation.gif
  vgs make $ROBOT --out $A/s9_robot; echo "exit=$?"; $PY $A/measure2.py $A/s9_robot/animation.gif
  vgs make $A/c1_magenta_flat.mp4 --out $A/s9_c1; echo "exit=$?"
  # 9b 保留內島
  vgs make $CHIBI --out $A/s9_chibi_keep --keep-interior-key; echo "exit=$?"; $PY $A/measure2.py $A/s9_chibi_keep/animation.gif
  vgs make $A/c1_magenta_flat.mp4 --out $A/s9_c1_keep --keep-interior-key; echo "exit=$?"
  # 9c 低飽和：不自動去背
  vgs make $SEATED --out $A/s9_seated; echo "exit=$?"
  vgs make $IDLE   --out $A/s9_idle;   echo "exit=$?"
  # 9d 低飽和但明確指定 --key（HEX 取自 9c 的摘要）
  vgs make $SEATED --out $A/s9_seated_key --key F3EADB; echo "exit=$?"; ls $A/s9_seated_key
  # 9e QA 回報殘留鍵色
  vgs qa $A/s9_chibi/animation.gif; echo "qa exit=$?"
  vgs qa $A/s9_chibi_keep/animation.gif; echo "qa exit=$?"
  $PY scripts/gif_pipeline.py $CHIBI --out $A/s9_legacy --width 320 >/dev/null; vgs qa $A/s9_legacy/animation.gif; echo "qa exit=$?"
  ```
- **必須**：
  1. **9a**：chibi 與 robot 的預設輸出都要 `magenta_share_max ≤ 0.02` 且 `ring_opaque_max ≤ 0.01`；`opaque_max` 不得比 BASE 明顯下降（chibi 約 0.136 以上的量級，用來防止主體被誤刪）。chibi 的摘要**必須**出現內島警告：寫出最大面積比例（約 0.3 的量級）與幀號（約第 54 幀，抽幀後幀號可能不同，須和 manifest 一致），並附上 `--keep-interior-key` 的完整用法。robot 若偵測到內島（§0.3 約 3.7%），也須警告。C1 的摘要須警告內框被移除。manifest 須有對應欄位。
  2. **劍光保留**：以 Read 檢視 `$A/s9_chibi/preview.png`、`contact.png`，第 54 幀附近的亮粉紫劍光仍然看得見，封閉洋紅袋已去除。驗收者人工比對並記錄。
  3. **9b**：`--keep-interior-key` 下，C1 內框保留不透明（檢查 contact 圖或量測內框區域的 alpha）；chibi 的 `magenta_share_max` 回到約 0.3 的量級。摘要寫明已保留內部鍵色，**不得**宣稱鍵色殘留達標。
  4. **9c**：seated 與 idle 都**不自動去背**。exit 0，產出非透明 GIF（`ring_opaque_max ≈ 1.0`）；或者 exit ≠ 0 並給出人話說明。兩種情況都必須在摘要寫出：「未去背」、原因為**低飽和**（附實測飽和度，以及門檻 0.35）、「非透明交付」，並附可直接複製的 `--key <實測 HEX>`。manifest 記錄 `background_flat: true`、`background_removed: false`、飽和度與門檻。**不得**出現 `No visible foreground`、Traceback，也不得在 exit ≠ 0 時留下空的輸出目錄卻不說明。
  5. **9d**：依 §1.2 的「明確 `--key` 路徑」判定，結果只能是 (a) 主體保留，或 (b) 人話拒絕。
  6. **9e**：`vgs qa` 與 `vgs make` 的輸出都要同時列出 `border_opaque_max`（或同義名稱）**和**殘留鍵色比例（`key_share_max`／`magenta_share_max`，附幀號）。對 9a 的成品，`vgs qa` 判 PASS（不得把劍光誤判為殘留）。對 9b 的保留版，至少要 WARN，或 FAIL 並指明殘留鍵色比例。對 legacy 未去背 GIF，判 FAIL 並指出背景未去除（Batch 1 S-2 非退化）。另以 Python 構造一個「邊框透明、中央 40% 為 #FF00FF 不透明」的 GIF，`vgs qa` 不得給 PASS。
  7. C2、C3（Batch 1）非退化：C2 不去背並說明原因為非純色；C3 綠幕（飽和度 1.0）可正確自動去背，或明說不支援。
- **禁止**：默默挖空（有內島卻沒有警告）；死碼讓警告永遠不出現（§1.3 反例 2）；低飽和底被自動去背；`vgs qa` 只看邊框；為了量測達標而刪掉劍光。

### S-10 `--pixel` 預設、Sprite、X MP4 與首發素材包

- **指令**：
  ```sh
  vgs make --help | grep -nE -- "--pixel|--pixel-width|--pixel-scale|--colors|--sprite|--mp4|--loop-count"
  vgs make $CHIBI --out $A/s10 --pixel --sprite --mp4; echo "exit=$?"
  ls -l $A/s10 $A/s10/sprites
  $PY $A/pixelcheck.py $A/s10/*.gif 3 32            # 預設：96 寬 ×3 = 288
  $PY $A/measure2.py $A/s10/*.gif
  vgs make $CHIBI --out $A/s10b --pixel --pixel-width 64 --pixel-scale 5 --colors 16; echo "exit=$?"
  $PY $A/pixelcheck.py $A/s10b/*.gif 5 16           # 須為 320 寬
  vgs make $IDLE --out $A/s10_idle --pixel --mp4 --key F0EBE8; echo "exit=$?"   # 直式＋奇數高度＋明確 key
  for m in $A/s10/*.mp4 $A/s10_idle/*.mp4; do ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,pix_fmt,width,height -show_entries format=duration -of compact $m; done
  $PY -c "import json;d=json.load(open('$A/s10/sprites/sprites.json'));print(d['schema_version'],d['engine_validation'],d['frame_size'],len(d['frames']),d['qc'])"
  grep -niE "unity|godot|texturepacker" $A/s10/sprites/sprites.json $A/s10/*.md 2>/dev/null
  for c in 1 256 abc; do vgs make $CHIBI --out $A/s10_bad$c --pixel --colors $c; echo "colors=$c exit=$?"; done
  # 首發素材包
  X=/workspace/money-radar-team/2026-11-22/x-pixel-media; ls -l $X
  for m in $X/*.mp4; do ffprobe -v error -show_entries stream=codec_name,pix_fmt,width,height -show_entries format=duration -of compact $m; done
  for g in $X/*.gif; do ls -l $g; $PY $A/measure2.py $g; done
  ```
- **必須**：
  1. `--help` 列出所有 7 個旗標，並寫明預設值（96 寬、32 色、放大到 ≥ 288、最近鄰、無抖動）。
  2. **像素不變式**（§1.4）：`pixelcheck` 對預設輸出顯示 `nonuniform_blocks == 0`、`opaque_colors ≤ 32`、`alpha_values ⊆ {0,255}`、寬度為 288（96×3）。自訂輸出為 320 寬、≤ 16 色、方塊一致。manifest 記錄網格大小、倍率、色數、`resample: nearest`、`dither: none`。
  3. 透明不退化：預設 `--pixel` 輸出的 `ring_opaque_max ≤ 0.01`、`magenta_share_max ≤ 0.02`（網格縮小後，洋紅邊緣的混色像素不得因無抖動量化而變成一圈洋紅色環。若超標，須在摘要中揭露並說明原因）。loop 與內島的規則與 S-8、S-9 一致。
  4. `--sprite`：`$A/s10/sprites/sheet-000.png` 與 `sprites.json` 存在，透過既有的 `sprite_export.export` 產生（`schema_version 1`、`engine_validation: "not performed"`、`qc.rgba_mismatches == 0`）。`frames` 的數量等於 GIF 的輸出幀數；`frame_size` 和 GIF 的網格大小或放大後大小一致，並在說明中寫明是哪一種。sheet 的 alpha 只有 0 和 255。
  5. `--mp4`：`codec_name=h264`、`pix_fmt=yuv420p`，寬高為偶數；未指定 `--loop-count` 時，時長落在 8 到 15 s（或者 help 寫明預設值，且實際時長和寫的一致）。抽第 0 幀檢查：四角為深色（平均亮度 ≤ 64），不得有棋盤格或洋紅底板；以 Read 看 1 張抽幀，像素硬邊清楚。idle 直式的高度須以**補邊**處理成偶數，manifest 或摘要需記錄。時長 = 單次迴圈時長 × 次數（誤差 ≤ 1 幀），單次迴圈的速度不變。
  6. 錯誤路徑：`--colors 1`、`256`、`abc` 都 exit ≠ 0，訊息為人話（指出允許範圍 2 到 255，並給出修正指令），不得出現 Traceback，不得留下半成品。
  7. **首發素材包** `/workspace/money-radar-team/2026-11-22/x-pixel-media/`：包含 1 個 MP4（h264／yuv420p／8 到 15 s）、1 個透明像素風 GIF（< 15 MB，`ring_opaque_max ≤ 0.01`，`pixelcheck` 通過）、1 份 Sprite Sheet（`sheet-000.png` 加 `sprites.json`），以及 1 份說明檔（中文或中英對照，寫明來源影片、產生指令、各檔規格，並註明「未發布，需人看核准」）。說明檔中的指令須以 `vgs make` 實際重跑一次，並得到同規格的結果（尺寸、色數、時長一致）。
- **禁止**：在任何放大步驟使用 Lanczos、bilinear 或 bicubic；量化時抖動；宣稱 sprite 為原生 Unity、Godot 或 TexturePacker 格式；發布到 X（素材包只能停留在本機）；把 MP4 的單次迴圈放慢來湊時長；寫入或覆蓋 `examples/*/final.gif`。

### S-11 保留（held-out）真實影片實測

- **指令**（不帶任何自訂旗標）：
  ```sh
  for n in robot:$ROBOT seated:$SEATED idle:$IDLE gufeng:$GUFENG; do k=${n%%:*}; v=${n#*:}
    s=$(date +%s%N); vgs make $v --out $A/s11_$k > $A/s11_$k.txt 2>&1; echo "$k exit=$? wall_ms=$(( ($(date +%s%N)-s)/1000000 ))"
    cat $A/s11_$k.txt; [ -f $A/s11_$k/animation.gif ] && { $PY $A/measure2.py $A/s11_$k/animation.gif; ls -l $A/s11_$k/animation.gif; }
  done
  ls wow/batch2/evidence/
  ```
- **必須**：
  1. 建造者的證據（`wow/batch2/evidence/`）中至少有 3 支非 chibi 的真實影片：**至少 1 支飽和棚景**（robot）、**至少 1 支低飽和純底**（seated 或 idle）、**至少 1 支複雜背景**（gufeng）。每支都要記錄完整指令、stdout／stderr、exit、牆鐘、去背判定及其依據（信心值、飽和度）、loop 判定、QA 等級與主要原因、輸出大小。驗收者用同一指令重跑，**判定類別必須一致**（去背或不去背、loop PASS 或 FAIL、QA 等級）。數值允許小幅差異。
  2. 各片的預期判定：
     - robot：自動去背；`ring ≤ 0.01`、`magenta_share_max ≤ 0.02`；若有內島，給出警告；`loop FAIL`（position），不加 crossfade（S-8 第 6 項）。
     - seated、idle：不自動去背，理由為低飽和（S-9 第 4 項）；不得 crash。
     - gufeng：不去背，理由為非純色；loop 若 FAIL，就如實報告。**大小與時間**：BASE 輸出 41 MB、牆鐘 24 s，實作可以維持現況，但摘要必須醒目寫出檔案大小。若大於 15 MB，摘要須提示可用 `--width` 或 `--pixel` 等方式縮小（給出可複製的指令），不得在沒有任何提示的情況下交出 40 MB 的 GIF。牆鐘超過 15 s 時，須在證據中記錄，並說明原因是 12 s 直式來源（不得把這種情況誤報為 S-1 的 15 s 目標已達成）。
  3. 4 支片都沒有 Traceback；結束碼與摘要的語氣一致（exit 0 卻寫 FAIL 時，第一屏須清楚寫明非透明或 FAIL 的原因）。
  4. 證據中如實區分「建造者看過的樣本」（chibi）和保留樣本。若建造者在建造期間曾用保留片調整參數（例如飽和度門檻），須在證據中自述。驗收者以 C1 到 C3 加上 4 支真實片交叉檢驗；門檻 0.35 是 spec 定值，不得為了個別影片而調整。
- **禁止**：只跑 chibi；帶自訂旗標跑 S-11；挑選只會成功的影片；證據內容與驗收者重跑的判定類別不一致。

### S-12 GitHub README 首屏截圖與同步更新

- **指令**：
  ```sh
  git fetch origin && git log --oneline BASE..origin/main 2>/dev/null || git log --oneline 064c675..origin/main
  git diff --stat 064c675..origin/main -- .github/workflows        # 須為空
  git show origin/main:README.md | grep -nE "vgs make|--pixel|hero\.gif|hero-preview\.png|--loop|--keep-interior-key"
  git show origin/main:README.zh-TW.md | grep -nE "vgs make|--pixel|hero\.gif|hero-preview\.png|--loop|--keep-interior-key"
  git show origin/main:SKILL.md | grep -nE "--pixel|--loop|--keep-interior-key|低飽和|saturation"
  for f in $(git show origin/main:README.md | grep -oE "\]\(([^)]+\.(gif|png|webp|jpg|mp4))\)" | sed -E 's/.*\(//;s/\)//' | head -3); do git cat-file -s origin/main:$f; done
  ls -l wow/batch2/evidence/*390* wow/batch2/evidence/*1440* wow/batch2/reviews/*design*
  # 驗收者自行截圖對照（免費、本機 Chrome）
  google-chrome --headless=new --disable-gpu --hide-scrollbars --window-size=390,844  --screenshot=$A/gh-390.png  https://github.com/miles990/video-gif-studio
  google-chrome --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 --screenshot=$A/gh-1440.png https://github.com/miles990/video-gif-studio
  ```
- **必須**：
  1. 變更已 push 到 `origin/main`（push 前檢查過 `origin/main`，沒有 force-push 覆蓋他人提交）。`.github/workflows/` 與 `scripts/run_ci_smoke.py` 沒有任何建造者造成的 diff。
  2. 證據中有 `390×844` 與 `1440×900` 兩張截圖。PNG 的實際像素尺寸要相符（若以 2x 截圖，則為 780×1688 與 2880×1800，並在證據中註明）。截圖時間晚於最後一次 push，畫面上可看到新的 hero（以 Read 檢視）。驗收者的對照截圖內容一致。
  3. `wow/batch2/reviews/` 中有一份獨立 W4 設計審查，由 Claude 撰寫（不是 Codex），內容涵蓋兩種寬度的首屏，以及每個指出問題的處置（已修改或延後並說明理由）。
  4. README（中英文版）在 origin/main 上包含：新的 `hero.gif` 與 `hero-preview.png`（首屏引用，每個 ≤ 3 MB，目標 ≤ 2 MB；BASE 為 0.73 MB 與 0.13 MB）、一段**真實** `vgs make` 輸出範例（必須和 S-8 或 S-9 的實際 stdout 一致，至少要能對上 chibi 的幀數、秒數、loop 判定與內島警告），以及 `--pixel` 的用法與一張像素風示範圖（≤ 3 MB）。英中內容一致。
  5. `SKILL.md` 寫明 `--loop auto/crossfade`、`--keep-interior-key`、低飽和不自動去背（附 `--key` 用法）以及 `--pixel` 系列旗標。
  6. Agensi 精簡包（`/workspace/money-radar-team/2026-11-22/video-gif-studio-agensi.zip` 與 `agensi-listing-pack.md`）已依本批更新：zip 內 `scripts/vgs.py` 的雜湊等於 origin/main 上的版本；listing 提到 `--pixel`。Batch 1 S-7 的排除規則仍成立（`excluded-hits=1`）。**未送出**。
  7. README 不宣稱「所有循環無縫」、不宣稱原生引擎格式、不宣稱市場節省；相容 agent 只列 Codex 與 Claude Code（Batch 1 §1.6）。
- **禁止**：截圖晚於 push 卻仍是舊 hero；README 範例輸出是手寫或美化過、和實跑不一致；由建造者自己撰寫 W4 審查；送出 Agensi。

### Batch 1 非退化（必驗）

依 `wow/batch1/acceptance.md` §3 原樣重跑 S-1 到 S-7（S-6 第 5 項的 Claude Code 實跑可引用 Batch 1 的證據，前提是 `vgs make` 的介面相容；若介面有破壞性變更，則須重跑）。特別注意：

- S-1：chibi 的 `magenta_share_max ≤ 0.02`（Batch 1 未達成，本批必須達成）；牆鐘 ≤ 15 s（迴圈搜尋不得讓牆鐘超標，BASE 為 4.6 s）。C1 到 C3 依 S-9 的新規則判定。
- S-2：`--no-key` 對 chibi 仍須 FAIL，且理由是背景本身（不能只依賴 loop FAIL，而且現在 loop 已可 PASS，這條變得更關鍵）。
- S-4：4 種人話錯誤仍然成立。新旗標的錯誤（`--colors`、`--pixel-width 0`、`--pixel-scale 0`、`--loop bogus`、`--key ZZZZZZ`）同樣適用 S-4 的三段式人話規則。
- 完整測試套件：`$PY -m pytest -q`（或 repo 既有的測試入口）全部通過；新增的測試須涵蓋 §1.1 到 §1.4 的反例（至少包括：robot 類不回位片預設不 crossfade、低飽和底不自動去背、內島警告出現、像素方塊一致性）。

## 4. 非目標守門（任一違反即整批 FAIL）

```sh
git diff --stat 064c675..origin/main -- .github/workflows scripts/run_ci_smoke.py   # 須為空
sha256sum -c $A/final-gif.before.sha256                                            # 三個 final.gif 都要 OK
git diff --name-only 064c675..origin/main | grep -E "examples/[^/]+/final\.gif$"; echo "hits=$?"   # 須為 hits=1
grep -rnE "api\.x\.ai|fal\.run|queue\.fal" wow/batch2/evidence 2>/dev/null; echo "hits=$?"        # 證據中不得有付費呼叫痕跡
```

1. `.github/workflows/` 或 `scripts/run_ci_smoke.py` 出現任何建造者的提交變更。
2. 任何 Grok 或 fal 呼叫（建造期與驗收期皆計）。檢查 `~/.codex` 的 session 日誌與 fal 用量；若無法檢查，標記為**未知**，不得寫通過。
3. 提交到 Agensi、發 X 貼文、對外寄信或聯絡。`x-pixel-media/` 只能留在本機。
4. 覆寫 `examples/*/final.gif`（雜湊必須和 §2 的基線一致）或其他官方紀錄（`examples/*/manifest.json`、`verification.json`）。新的 hero 或像素示範須另存為新檔。
5. 宣稱所有循環無縫、宣稱原生引擎 importer、宣稱市場節省。
6. 工作樹開工前已存在的未追蹤檔 `examples/chibi-running-dash/hero.png` 不是建造者的產物；若建造者要提交它，須在 progress 中說明用途。

## 5. 仍需真人判斷的項目（本卷不判通過）

- chibi 在 auto 迴圈點的觀感（量測 PASS 不代表看起來無縫）；`--loop crossfade` 的鬼影可否接受。
- 內島處理的語意判斷：每支片的內島是背景還是前景設計，須由人看過才能決定是否加上 `--keep-interior-key`。
- 像素風成品的美感（96 px 網格是否保留角色辨識度）；X MP4 在手機上的實際觀感。
- 390／1440 首屏設計的最終核准（W4 審查只是輸入，不等於核准）。
