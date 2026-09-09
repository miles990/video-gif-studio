# Video GIF Studio

可重用的 Codex skill：從參考圖、原創人物或既有影片，製作動作連續、時長可調、透明色正確的 GIF。

## 使用需求

**完整的 AI 生成流程需要 Codex + Grok。**

- **Codex**：執行此 skill、設計動作與提示詞、建立或處理參考圖，以及製作和驗證 GIF。需要建立新圖片時，須有可用的圖片生成功能。
- **Grok**：生成連續動作影片。需要已登入的 Grok 帳號，以及可用的影片生成權限與額度；本版透過既有 MV Studio `motiongen.py` OAuth adapter 連接，詳見 [Grok 設定與使用方式](references/grok.md)。
- **本機處理環境**：Python 3 與 `requirements.txt` 中的套件；檢查、轉換影片時需要 FFmpeg／ffprobe。

已有影片或透明 PNG 畫格時，可以只執行本機轉檔工具，不必再次呼叫 Grok。此 repo 不包含 Codex／Grok 帳號、訂閱或生成額度。



## 成功範例

**坐姿換腿：Grok 影片 → 透明 GIF → 透明色破圖修復。** 下方是實際交付的 9.93 秒透明 GIF，保留人物與椅子的連續動作。

![坐姿換腿透明 GIF 成功範例](examples/seated-leg-switch/final.gif)

[下載 GIF](examples/seated-leg-switch/final.gif) · [生成參考圖](examples/seated-leg-switch/reference.png) · [完整提示詞](examples/seated-leg-switch/prompt.txt) · [來源影片](examples/seated-leg-switch/source.mp4) · [完整製作紀錄與驗證](examples/seated-leg-switch/README.md)

**修正前後對照：左側是透明色誤判造成的黑點，右側是修復後。**

![GIF 透明色修正前後對照：左側破圖，右側修復](examples/seated-leg-switch/before-after.png)

289 格逐格驗證沒有新增透明破洞。此範例展示已驗證的輸出修復；首尾尚非完全無縫，人體結構與自然度仍須視覺審看。

## 使用

把此 repo 放到 Codex 的 skills 目錄，或建立指向此 repo 的 symbolic link，再呼叫：

> 使用 $video-gif-studio，參考這張人物圖製作自然動作的透明 GIF。

也可不提供參考圖：

> 使用 $video-gif-studio，設計原創小機器人揮手動作，先生成連續影片，再輸出 GIF。

已有影片可以直接處理，不必重新生成。詳見 [SKILL.md](SKILL.md)。

## 工具

```sh
python3 -m pip install -r requirements.txt
python3 scripts/gif_pipeline.py source.mp4 --key FF00FF --out output/example --apng
python3 -m unittest discover -s tests -v
```

- [動作與速度設計](references/motion.md)：依動作階段調速，區分移動與停留。
- [輸出工具](references/export.md)：去背、透明 PNG、GIF、APNG、色盤與逐格檢查。
- [Grok 生成](references/grok.md)：連接既有 OAuth adapter；提交一次、記錄 job ID、可恢復查詢。
- [問題診斷](references/failure-modes.md)：定位原影片、遮罩或 GIF 編碼哪個階段出錯。

## 已驗證與邊界

此工具沿用一個實際完成的 Grok 影片轉 GIF 案例，將「皮膚陰影誤用透明色而破圖」修正為專用透明索引。回歸測試涵蓋不透明洋紅色、皮膚陰影、alpha 門檻、重複畫格、分段時長與 provider job 恢復。

技術驗證不等於自然動作、人體結構或藝術品質驗收。原始動作仍須審看，生成後也可能需要重做。Grok adapter 是選用依賴，需使用者環境中的既有 motiongen.py；repo 不含認證資料。新建立的 wrapper 使用模擬回應測試，沒有為測試額外付費生成。

除了使用者指定收錄的成功範例，其餘每次製作的資料留在獨立 output 目錄。沒有參考圖的路線為「建立原創起始圖 → 檢查 → 影片」，不宣稱已驗證所有 provider 的純文字生成影片功能。
