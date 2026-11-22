# Batch 1 驗收答案卷 — video-gif-studio 輕量交付

- 角色：獨立驗收者（Claude Opus），建造者為 Codex（不同廠商）。本卷建造前寫成，**不修改 spec，也不放寬 spec**；若本卷與 spec 有衝突，以較嚴者為準。
- 日期：2026-11-22（Asia/Taipei）
- 成本：$0。驗收全程不得呼叫 Grok／fal 或任何付費生成；驗收指令一律輸出到 `/tmp/vgs-acc/…` 新目錄，不寫入 repo。
- 樣本：可見樣本為 `examples/chibi-running-dash/source.mp4`。之後的批次應優先使用建造者沒看過的保留（held-out）輸入；本輕量批次可只用此範例來源，必要時加上下面定義的合成洋紅純色對照組（ffmpeg lavfi 產生，免費）。由於建造者看得到 chibi 來源，**只靠 chibi 通過不能證明泛化**，所以合成對照組（C1 至 C3）在 S-1 和 S-2 屬於必驗。

## 0. 樣本基線（驗收者 2026-11-22 本機實測，免費路徑，輸出在 /tmp）

| 項目 | 值 |
|---|---|
| `source.mp4` | 720×720、24 fps、145 幀、6.04 s、1.64 MB |
| 背景色 | 洋紅，解碼 RGB ≈ (244,20,247)／(251,0,249)，不是精確的 `FF00FF` |
| 舊預設 `gif_pipeline.py source.mp4 --out X --width 320`（不帶 `--key`） | 4.21 MB，每幀 100% 不透明，邊框 4 px 全不透明，不透明像素中洋紅佔比最高 94.8%；`technical_pass: true` ← 這就是 spec 要消滅的反例 |
| `--key FF00FF --tolerance .2 --softness .18 --width 320` | 1.12 MB、145 幀、alpha mismatch 0；每幀不透明面積最多 9.4%；邊框 4 px 不透明為 0；洋紅佔比 0 |
| `qa_media.py` 對上列透明 GIF | exit 1；`freeze WARN f85/3.540 s 到 f144/6.040 s`；`loop FAIL`（`position_pass: true`、`speed_pass: false`，speed_ratio 0.088）；pops WARN f38、f53、f54 |
| `qa_media.py` 對未去背 GIF | exit 1，但 FAIL 理由**只有 loop**，沒有任何一項指出「背景未去除」 ← S-2 的直接反例 |

本表只作為對照參考。建造後的數字可以不同，但下列不變式不得違反。

## 1. 領域規則、不變式、邊界與反例（專家先看這些）

### 1.1 色鍵與主體顏色
- **規則**：只有在證據顯示背景是均勻純色時，才可以自動色鍵。證據至少包含：四邊或角落取樣的顏色一致，且在時間上穩定。估得的鍵色、容差與信心值須寫進 manifest 和摘要。
- **不變式**：自動色鍵不得把主體內部大片區域變透明而不告知。
- **邊界**：來源洋紅不是精確的 `FF00FF`，而且有壓縮噪聲；硬寫 `FF00FF` 加窄容差會殘留邊框，驗收時要看實測顏色。chibi 劍光是亮粉紫色的合法前景，不能把它當背景刪掉來追求「零洋紅」。
- **反例 1**：前景含有和背景同色的封閉區塊（C1 的洋紅內框）。全域色鍵會把它挖空。可接受的結果有兩種：保留該區塊（例如只移除和邊框連通的背景），或在摘要中**明確警告**「前景含鍵色，可能被挖空」。默默挖空不可接受。
- **反例 2**：背景不是純色（C2 的 testsrc2）。不得自動套用色鍵並宣稱透明。應不套用色鍵（或拒絕），並在摘要明說「未去背，原因：背景非純色」。
- **反例 3**：背景是綠幕而不是洋紅（C3）。若宣稱能自動偵測背景色，就不能把洋紅硬寫死。若只支援洋紅，摘要須說明此限制，不得宣稱已透明。

### 1.2 GIF 是二值透明
- GIF 每個像素只有透明或不透明。半透明邊緣在 GIF 中一定是取捨後的結果，邊緣殘留的洋紅色環屬於品質問題，不能用 `alpha_mismatch_pixels: 0` 掩蓋。alpha mismatch 只證明編碼和來源閾值一致，不證明去背正確。
- **不變式**：「透明 GIF」至少要求每幀邊框 4 px 的不透明比例 ≈ 0（主體可能碰邊時另行說明），且不透明像素中不得有整片背景色。
- **反例**：`technical_pass: true` 但每幀 100% 不透明，即舊預設的情況。

### 1.3 定格與設計停頓
- 尾端長時間靜止（3.54 至 6.04 s，佔全片約 41%）是生成來源的收招殘留，不是設計停頓。
- **不變式**：自動裁切或壓縮尾端時，須在摘要和 manifest 記錄「原長度、處理後長度、裁掉或壓縮的時間範圍與方法」。不得用 `--holds` 把定格標成設計停頓，只為讓 WARN 消失。
- **邊界**：收招後保留短暫的 guard 姿勢（例如 ≤ 0.5 s）是合理的設計；把收招動作本身也裁掉則屬破壞內容。
- **反例**：只把 QA 參數改成 `--holds 3.5-6.04`，定格仍然整段在場，摘要卻寫「已處理」。

### 1.4 循環接縫與「生成時首幀等於尾幀」
- chibi 是用同一張圖當首幀和尾幀生成的，所以 `position_pass: true`，但這不代表循環無縫。首尾兩幀幾乎相同時，循環播放會出現一次重複幀（卡一下）；尾端定格則讓速度在接縫處跳變，這就是 speed FAIL 的原因。
- **不變式**：只要 loop 檢查仍是 FAIL，摘要必須照寫，不得出現「無縫」「seamless」「loop OK」等字樣。若因裁掉重複的末幀而讓 loop 通過，須記錄為處理動作。
- **反例**：為了讓 loop PASS，加入淡入淡出、倒放或插幀卻沒有揭露。原範例聲明沒有 crossfade 或倒放，新流程同樣須揭露任何這類處理。

### 1.5 QA 與視覺核准
- `technical_pass` 和 QA PASS 只代表量測的閾值過關。動作自然度、意義、無縫感都需要人看，摘要須保留「視覺核准：未評估（需人看）」或同等字樣。
- **反例**：摘要只印出「PASS」或「✅ Done」，讓人以為可以交付。或者 QA 等級是 FAIL，摘要的第一行卻寫成功。

### 1.6 其他 spec 不變式（每個 S 都要順帶確認）
- 本機路徑不得連網呼叫 Grok／fal。驗收時以 `env -u XAI_API_KEY -u FAL_KEY` 執行，並可在斷網環境（例如 `unshare -n`）重跑 S-1，結果須相同。
- 不改 `.github/workflows/`（`git diff --stat <base>..HEAD -- .github/workflows` 須為空）。注意：工作樹開工前已有一處未提交的 `test.yml` 修改，那不是建造者的變更，但建造者的提交不得包含它。
- Sprite metadata 不得宣稱原生 Unity／Godot／TexturePacker 格式。
- 不得宣稱已驗證的市場節省；相容 agent 只列 Codex 和 Claude Code。

## 2. 共用準備（驗收者執行）

```sh
cd /workspace/src/video-gif-studio
PY=${PY:-.venv/bin/python}   # 或已安裝 skill 的 venv；以 README 寫法為準
SRC=examples/chibi-running-dash/source.mp4
A=/tmp/vgs-acc; rm -rf $A; mkdir -p $A
# C1：洋紅純色背景，白色移動方塊，內含封閉洋紅內框（前景含鍵色）與暗紫條
ffmpeg -v error -f lavfi -i "color=c=0xF414F7:s=320x240:r=24:d=2" -f lavfi -i "color=c=white:s=100x100:r=24:d=2" \
  -filter_complex "[1]drawbox=x=25:y=35:w=50:h=30:color=0xF414F7@1:t=fill,drawbox=x=0:y=88:w=100:h=10:color=0xC81EC8@1:t=fill[s];[0][s]overlay=x='20+t*60':y=60:shortest=1" \
  -pix_fmt yuv420p $A/c1_magenta_flat.mp4
# C2：非純色背景
ffmpeg -v error -f lavfi -i "testsrc2=s=320x240:r=24:d=2" -pix_fmt yuv420p $A/c2_busy.mp4
# C3：綠幕純色加白色方塊
ffmpeg -v error -f lavfi -i "color=c=0x00FF00:s=320x240:r=24:d=2" -f lavfi -i "color=c=white:s=100x100:r=24:d=2" \
  -filter_complex "[0][1]overlay=x='20+t*60':y=60:shortest=1" -pix_fmt yuv420p $A/c3_green.mp4
```

已驗證：C1 為 24 fps、48 幀，方塊從 x=20 移到 x=136，內框解碼為 (242,18,247)，和背景同色。

GIF 量測輔助（寫在 `/tmp/vgs-acc/measure.py`，不放進 repo）：

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
print(dict(size=g.size, frames=g.n_frames, loop=g.info.get('loop'), opaque_max=round(max(op), 3),
           ring_opaque_max=round(max(ring), 4), magenta_share_max=round(max(mag), 4)))
```

## 3. S 條目驗收

每條的判定方式：每個「必須」都成立才算 PASS；任何一個「禁止」出現即 FAIL。須留證據（指令、stdout／stderr、結束碼、量測輸出），存到 `wow/batch1/evidence/`（由建造者或協調者存放，驗收者不寫入 repo）。

### S-1 一條指令、透明預設

- **核心輸入**：`$SRC`（chibi 洋紅來源）。對照組：C1、C2、C3。
- **指令**（不得手動傳 `--key`、`--tolerance`、`--width`）：
  ```sh
  s=$(date +%s%N); $PY scripts/vgs.py make $SRC --out $A/s1; echo "exit=$?"; e=$(date +%s%N); echo "wall_ms=$(( (e-s)/1000000 ))"
  $PY $A/measure.py $A/s1/*.gif
  for c in c1_magenta_flat c2_busy c3_green; do $PY scripts/vgs.py make $A/$c.mp4 --out $A/s1_$c; echo "$c exit=$?"; done
  ```
  若 README 寫的入口是 `vgs make`，兩種寫法都要跑，結果須相同。
- **必須**：
  1. chibi 執行的 exit 為 0，`$A/s1/` 內有一個透明 GIF（檔名需在摘要中印出）、manifest（記錄自動估得的鍵色、容差、信心值，以及尾端處理，見 S-3），以及 QA 報告（`report.md`／`report.json`）。
  2. 量測結果：`ring_opaque_max ≤ 0.01`；`opaque_max < 0.5`（基線為 0.094，主體不會佔滿畫面）；`magenta_share_max ≤ 0.02`（容許劍光等合法粉紫色，但不得有整片背景）；`loop == 0`；manifest 或 QC 的 `alpha_mismatch_pixels == 0`。
  3. 若輸出有 preview 或 contact 圖，須在淺色**與**深色（或棋盤）底上都能看出透明。棋盤底上看得到主體、看不到洋紅底板（以人眼或 Read 圖檢查）。
  4. 人話摘要（stdout，非僅 JSON）包含：寬×高、幀數、時長（秒）、檔案大小（MB）、是否去背（並附鍵色）、QA 等級（PASS／WARN／FAIL 加上主要原因）、輸出路徑，以及「視覺核准需人看」這類聲明。
  5. 編碼牆鐘 ≤ 15 s。以上面指令實測的 `wall_ms` 為準，並同時記錄輸出寬度（spec 的時間目標是在 ≤ 320 px 寬下訂的；若預設寬度大於 320，仍須 ≤ 15 s，不得因寬度而放寬）。牆鐘只是本機數字，首次使用的 30 秒須另由真人確認。
  6. C1：外部洋紅變透明，白色方塊保留；封閉的洋紅內框若被挖空，摘要須有明確警告（見 1.1 反例 1）。C2：不得宣稱透明，摘要須寫明「未去背」及原因；若 exit 為 0，摘要須清楚標示為非透明交付。C3：要嘛綠底正確去背，要嘛明說只支援洋紅、未去背。
- **禁止**：整片洋紅仍在卻 exit 0 且摘要寫「透明」或「PASS」；只輸出原始 JSON；連網呼叫 Grok／fal；為了達成牆鐘目標而預設輸出極小尺寸卻不在摘要中寫出尺寸；寫入或覆蓋 `examples/` 內的檔案。

### S-2 未去背不得通過 QA

- **核心輸入**：`$SRC`，強制保留背景。
- **指令**：用建造者在 `--help` 中提供的明確旗標（例如 `--no-key` 或 `--keep-background`；名稱以 `$PY scripts/vgs.py make --help` 為準），另外對舊產物也做一次 QA：
  ```sh
  $PY scripts/vgs.py make --help
  $PY scripts/vgs.py make $SRC --out $A/s2 --no-key; echo "exit=$?"     # 旗標名稱依 help 調整
  $PY scripts/gif_pipeline.py $SRC --out $A/s2_legacy --width 320; echo "legacy exit=$?"
  $PY scripts/qa_media.py $A/s2_legacy/animation.gif --out $A/s2_legacy_qa; echo "qa exit=$?"   # 若交付檢查改在其他入口，改跑該入口
  ```
- **必須**：
  1. 強制保留背景時，QA 或交付檢查的結果為 **FAIL**，且 make 的結束碼 ≠ 0；或者至少 QA 等級為 FAIL，摘要第一屏寫明「背景未去除，不是透明 GIF」。spec 寫的是「必須 FAIL 或同等非零結束碼」，兩者都不能缺少「指出背景未去除」這句。
  2. FAIL 的理由必須是背景／透明度本身（例如「邊框 100% 不透明且為洋紅」），**不能只靠剛好存在的 loop FAIL**。基線顯示舊 QA 對未去背 GIF 的唯一 FAIL 理由就是 loop，這不算達標。驗法：把 S-3 處理後 loop 能通過的版本在保留背景下重跑，仍須 FAIL。
  3. 舊路徑 `gif_pipeline.py` 單獨使用時，若仍輸出 `technical_pass: true`，那麼 make 摘要、交付檢查，或 `qa_media` 中至少一個使用者可見的關卡須對該檔判 FAIL 並指出背景。若 `gif_pipeline` 本身也改了，記錄其新行為。
- **禁止**：`technical_pass: true` 成為唯一可見的結論；摘要寫「已去背」；exit 0 且沒有任何 FAIL 或警告。
- **反例檢查**：對 S-1 的透明成品跑同一個背景檢查，**不得**誤判 FAIL（避免把合法劍光當成殘留背景）。

### S-3 尾端定格與循環

- **核心輸入**：`$SRC`。
- **指令**：
  ```sh
  $PY scripts/qa_media.py $A/s1/*.gif --out $A/s3_qa; echo "qa exit=$?"
  grep -nE "freeze|loop" -A4 $A/s3_qa/report.md
  ```
  另外檢查 S-1 的摘要與 manifest。
- **必須**：
  1. 處理後的 freeze 段不得再覆蓋「收招後約 3.54 s 起到結尾」的長靜止。判準：任何殘留的尾端 freeze 段 ≤ 0.5 s，或整段已被移除。時長須明顯短於 6.04 s，並列在摘要裡。
  2. 摘要與 manifest 寫明尾端處理：原時長、新時長、裁掉或壓縮的來源區間（例如「來源 3.54 到 6.04 s 裁切，保留 x.xx s guard」）及方法（裁切／加速／抽幀）。
  3. 收招動作本身須保留：處理後最後一個非靜止幀的來源時間 ≥ 基線 freeze 起點附近（約 3.5 s）。以 manifest 的 `source_indices` 對照驗證。
  4. loop：若 QA loop 為 PASS，摘要可寫「loop 量測通過（未經視覺核准）」。若仍是 FAIL，摘要須寫「loop FAIL」及原因（position／speed），不得只寫在 report.md 裡。
- **禁止**：用 `--holds` 或標記設計停頓來壓掉 WARN；不加揭露地使用 crossfade、倒放或插幀；loop FAIL 時摘要出現「seamless」「無縫」「loop OK」或「視覺通過」；裁切卻不記錄。

### S-4 人話錯誤

- **核心輸入與指令**（每一個都要記錄 exit、stdout、stderr）：
  ```sh
  $PY scripts/vgs.py make $A/does-not-exist.mp4 --out $A/s4a                      # 來源不存在
  mkdir -p $A/pngs && $PY -c "from PIL import Image;[Image.new('RGBA',(32,32),(255,0,0,255)).save(f'$A/pngs/{i:03d}.png') for i in range(3)]"
  $PY scripts/vgs.py make $A/pngs --out $A/s4b                                    # PNG 目錄缺 fps
  mkdir -p $A/s4c && echo keep > $A/s4c/keep.txt && sha256sum $A/s4c/keep.txt
  $PY scripts/vgs.py make $SRC --out $A/s4c; sha256sum $A/s4c/keep.txt; ls $A/s4c   # 輸出目錄非空
  $PY scripts/vgs.py make $SRC --out $A/s4d --fps 30                              # 誤標 FPS（來源 24）
  ```
- **必須**（每一案）：exit ≠ 0；stderr 或 stdout **不含** `Traceback (most recent call last)`；訊息包含三個部分：發生什麼（指名路徑或數值，例如「來源 24 fps，你指定 30」）、影響（例如「會改變動作速度」「不會寫入任何檔案」）、下一步（可直接複製的修正指令或旗標，例如「改用 `--fps 24` 或省略」「改用新的 `--out` 目錄」）。訊息以人話寫成，不能只是 argparse 的 usage 片段。
  - 非空目錄：`keep.txt` 的雜湊前後相同，目錄內不得多出檔案。
  - 來源不存在：不得留下半成品輸出目錄（若已建立，須是空的，或訊息中有說明）。
- **禁止**：未捕捉的 traceback；exit 0；只顯示「Error」；覆蓋或刪除使用者檔案。

### S-5 雙軌 README、How it works 與圖生影表

- **核心輸入**：`README.md`、`README.zh-TW.md`（建造後）。
- **指令**：
  ```sh
  for f in README.md README.zh-TW.md; do echo "== $f"; sed -n 1,40p $f; done
  grep -nE "vgs(\.py)? make|skill" README.md README.zh-TW.md | head -20
  grep -nE "How it works|運作方式|運作原理" README.md README.zh-TW.md
  grep -nE "0\.080|0\.020|0\.05|0\.08|0\.16|2026-11-16|2026-11-22|\\\$0" README.md README.zh-TW.md
  grep -nE "Measured delivery QA|qa_media" README.md | head -3      # QA 段落行號須在入口與 How it works 之後
  # 首屏 hero：取前 40 行引用的圖片並量大小
  grep -oE "\]\(([^)]+\.(gif|png|webp|jpg|apng))\)" README.md | head -5
  ```
- **必須**：
  1. 兩個 README 的開頭（前約 40 行內）都說明「這是獨立 CLI 工具，同時也是 Codex 與 Claude Code skill」，並各有一條人用入口（`vgs make …` 一條指令）和一條 agent 入口。中英內容須一致，不得一邊有、一邊沒有。
  2. 有一張 How it works 圖（mermaid 或圖片），清楚區分**本機路徑（$0，不需帳號）**與**生成 API 路徑（Grok／fal）**。
  3. 圖生影選項表的價格逐字符合 spec：本機 $0；Grok／X 方案使用網站額度；Grok API 標題價 1.5 為 $0.080／秒、lite 為 $0.020／秒，並註明「分級表可能不同、上架前再查」；fal H3 Max 自 2026-11-16 起 480p／768p／1080p 分別為 $0.05／$0.08／$0.16 每秒。表上標示核對日期 2026-11-22。不得出現其他未核對的價格或「最便宜」之類宣稱。
  4. 「Measured delivery QA」段落不得再是 README 的第一節，須移到入口與 How it works 之後。
  5. 首屏引用的每個 hero 檔案 ≤ 3 MB（目標 ≤ 2 MB），以 `ls -l` 實測。現況 seated 為 19.9 MB、robot 為 7.0 MB、neon preview 為 10.5 MB，皆不合格，若仍留在首屏須換成壓縮版。
- **禁止**：宣稱市場節省或已驗證的效益數字；列出 Codex／Claude Code 以外的相容 agent；宣稱 sprite 為原生 Unity／Godot／TexturePacker 格式；README 將 `technical_pass` 描述為視覺通過；為了壓縮 hero 而覆寫 `examples/*/final.gif`（壓縮版應另存新檔，原交付保留）。

### S-6 Claude Code 支援

- **核心輸入**：`scripts/install.py`、`scripts/doctor.py`、SKILL.md／README。注意：本機 `~/.claude/skills/video-gif-studio` 與 `~/.codex/skills/video-gif-studio` **已存在**，驗收時不得覆寫，應以暫時 HOME 或 `--skills-dir` 測試。
- **指令**：
  ```sh
  T=$A/home; mkdir -p $T/.claude
  HOME=$T $PY scripts/install.py --target claude --skip-deps; echo "exit=$?"; ls $T/.claude/skills/video-gif-studio/SKILL.md
  $PY scripts/install.py --skills-dir $A/sk --skip-deps; echo "exit=$?"; ls $A/sk/video-gif-studio/SKILL.md
  HOME=$T $PY scripts/install.py --target claude --skip-deps; echo "re-run exit=$?"   # 已存在且非同源時須保留並說明
  $PY scripts/install.py --help | grep -E "target|skills-dir"
  grep -rnE "/video-gif-studio|\\\$video-gif-studio" README.md README.zh-TW.md SKILL.md
  $PY scripts/doctor.py; echo "doctor exit=$?"
  ```
  另以 `HOME=$T`（只有 `~/.claude`、沒有 `~/.codex`）測試未帶旗標時的偵測行為。
- **必須**：
  1. `--target claude` 裝到 `$HOME/.claude/skills/video-gif-studio`；`--skills-dir` 可指定任意目錄；`--target` 的值和預設偵測規則須寫在 `--help` 與 README。原有「不覆寫既存安裝、以 staging 目錄避免半套安裝」的行為不得退化（重跑時 exit ≠ 0，並顯示人話說明）。
  2. 文件同時寫出 `/video-gif-studio`（Claude Code）與 `$video-gif-studio`（Codex）兩種呼叫方式。
  3. 文件說明：環境沒有內建生圖時，需要提供起始圖或既有影片。
  4. doctor 不連網、不登入；在已安裝 deps 的 venv 中 exit 0；輸出包含 `local_gif_runtime_ready: true`。若 doctor 新增了 Claude Code 安裝位置的回報，須與實際路徑一致。
  5. **本機 Claude Code 實跑**（spec 硬性要求，不可用「理論上可行」代替）：在乾淨的工作目錄以 Claude Code 載入 skill（`/video-gif-studio` 或 skill 清單中可見），讓它執行 doctor 和本機 `vgs make`（輸入 `$SRC`，輸出到新 `/tmp` 目錄）。證據包含 session 紀錄或 stdout、產出的 GIF 路徑與 S-1 量測結果，存到 `wow/batch1/evidence/`。整個過程不得呼叫 Grok／fal。
  6. 相容 agent 只宣稱 Codex 與 Claude Code。
- **禁止**：覆寫使用者既有的 `~/.claude/skills/video-gif-studio` 或 `~/.codex/skills/video-gif-studio`；只做 `--skip-deps` 註冊就宣稱「Claude Code 可用」；沒有實跑證據。

### S-7 壓縮 hero、示範圖庫與 Agensi 包

- **核心輸入**：README 示範圖；`/workspace/money-radar-team/2026-11-22/`。注意該目錄**已有**一份 `agensi-listing-pack.md`（建造前就存在），驗收時須確認它已為本批更新（內容提到 `vgs make`、Claude Code 支援與 S-5 的價格表），不能拿舊檔充數。
- **指令**：
  ```sh
  D=/workspace/money-radar-team/2026-11-22
  ls -l $D/agensi-listing-pack.md $D/video-gif-studio-agensi.zip $D/agensi-cover.png 2>&1
  grep -nE "vgs make|Claude Code|0\.080|2026-11-16" $D/agensi-listing-pack.md
  unzip -l $D/video-gif-studio-agensi.zip | tail -1
  unzip -l $D/video-gif-studio-agensi.zip | grep -E "\.git/|\.venv/|\.runtime/|__pycache__|\.pyc$|/output/|/run-|wow/|qa/|\.env|local-settings\.json" ; echo "excluded-hits=$?"
  unzip -l $D/video-gif-studio-agensi.zip | sort -k1 -n | tail -5
  mkdir -p $A/zip && unzip -q $D/video-gif-studio-agensi.zip -d $A/zip && ls $A/zip/*/SKILL.md $A/zip/SKILL.md 2>/dev/null
  # README 示範圖大小
  grep -oE "\]\(([^)]+\.(gif|png|webp|jpg))\)" README.md | sed -E 's/.*\(//;s/\)//' | xargs -I{} ls -l {}
  ```
- **必須**：
  1. 兩個檔案都存在且為本批產出；封面若 listing 需要則須存在。
  2. 壓縮包內含 `SKILL.md`、`requirements.txt`、`scripts/`（至少包含 `vgs.py`、`gif_pipeline.py`、`install.py`、`doctor.py`）及 README；解壓後 `$PY <解壓目錄>/scripts/vgs.py make $SRC --out $A/s7run` 可以跑出和 S-1 同樣通過的結果（若包內不含 chibi 來源，就用 repo 內的 `$SRC`）。
  3. 不含 `.git`、`.venv`、`.runtime`、`__pycache__`、`output/`、`run-*`、`.env*`、`local-settings.json`、`wow/` 建造紀錄或 QA 暫存（上面的 grep 不得有命中，即 `excluded-hits=1`）。包內最大的五個檔案須逐一說明保留理由。驗收者建議的紅線：整包 > 25 MB 須書面說明（這是審查提示，不是 spec 門檻）。
  4. README 示範圖全部可快速載入：首屏 hero ≤ 3 MB；圖庫中每張建議 ≤ 3 MB，超過的須改成連結，不要內嵌。
  5. listing 內容遵守 1.6 節（不宣稱市場節省、只列兩個 agent、價格與 S-5 一致並註明上架前再查）。
- **禁止**：實際提交到 Agensi 或對外聯絡；壓縮包內含憑證、token 或 `.env`；宣稱已上架。

## 4. 非目標守門（任一違反即整批 FAIL）

- `.github/workflows/` 有任何建造者提交的變更。
- 驗收或建造期間產生任何 Grok／fal 付費請求（檢查日誌與 `~/.codex`／fal 用量。若無法檢查，標**未知**，不得寫通過）。
- 宣稱原生引擎 importer、宣稱所有循環無縫、對外寄信或提交 listing。

## 5. 仍需真人的項目（本卷不判通過）

- README 入口到發出正確指令 ≤ 30 秒（L10，須真人計時）。
- 成品動作的自然度與循環的觀感（視覺核准）。
- 390／1440 寬度下 README 首屏的設計審查（W2／W4）。
