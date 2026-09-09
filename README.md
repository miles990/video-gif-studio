# Video GIF Studio

支援有／無參考圖的 Codex skill，從連續影片製作透明 GIF，包含動作設計、速度調整、去背與破圖檢查。

授權：[MIT](LICENSE)

## 安裝方法

將 repo 安裝到 Codex 的 skills 目錄（需具備此 repo 的存取權）：

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone git@github.com:miles990/video-gif-studio.git "${CODEX_HOME:-$HOME/.codex}/skills/video-gif-studio"
cd "${CODEX_HOME:-$HOME/.codex}/skills/video-gif-studio"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

安裝後，在 Codex 開啟新對話並使用 `$video-gif-studio`。執行本機工具時使用上述 `.venv/bin/python`。

## 需求

- **Codex**：執行 skill、設計動作、處理參考圖及製作 GIF；建立新圖時需有可用的圖片生成功能。
- **Grok**：已登入且具備影片生成權限與額度；本版需要既有 MV Studio `motiongen.py` OAuth adapter，詳見 [Grok 使用方式](references/grok.md)。
- **本機環境**：Python 3.11 或以上、`requirements.txt` 套件，以及 FFmpeg／ffprobe。

已有影片或透明 PNG 畫格時，可直接轉檔，不必再次呼叫 Grok。

## 使用方法

提供參考圖：

> 使用 $video-gif-studio，參考這張人物圖，製作自然連續動作的透明 GIF。

不提供參考圖：

> 使用 $video-gif-studio，設計原創小機器人揮手，生成連續影片並製作透明 GIF。

調整既有影片：

> 使用 $video-gif-studio，把這段影片製成透明 GIF，調整動作速度並檢查破圖。

完整流程見 [SKILL.md](SKILL.md)，工具參數見 [輸出說明](references/export.md)。

## 成功範例

**坐姿換腿：Grok 影片 → 透明 GIF → 透明色破圖修復。** 實際成品為 9.93 秒，保留人物與椅子的連續動作。

![坐姿換腿透明 GIF](examples/seated-leg-switch/final.gif)

[下載 GIF](examples/seated-leg-switch/final.gif) · [參考圖](examples/seated-leg-switch/reference.png) · [提示詞](examples/seated-leg-switch/prompt.txt) · [來源影片](examples/seated-leg-switch/source.mp4) · [製作紀錄與驗證](examples/seated-leg-switch/README.md)

修正前後對照：左側為透明色誤判造成的黑點，右側為修復後。

![GIF 修正前後對照](examples/seated-leg-switch/before-after.png)
