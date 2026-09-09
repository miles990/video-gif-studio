# Video GIF Studio

支援有／無參考圖的角色動畫製作 skill：透過 **Grok 產生動作參考影片**，再由 **Codex 搭配 GPT-Image-2.5** 製作以角色一致性為目標的透明背景 GIF。

授權：[MIT](LICENSE)

## 安裝方法

把下面這段交給 Codex 或其他具備本機操作能力的 AI：

> 請幫我安裝 https://github.com/miles990/video-gif-studio 的 Codex skill。請先讀取 references/install.md，完成 skill 註冊、Python 依賴安裝與 doctor 驗證；保留既有安裝和資料，並分別告知本機 GIF 工具與 Grok 影片生成是否就緒。

AI 安裝流程見 [references/install.md](references/install.md)。此 repo 若為私人狀態，安裝者需具備存取權。安裝後在 Codex 下一次對話回合使用 `$video-gif-studio`。

## 需求

- **Codex + GPT-Image-2.5**：Codex 負責流程執行、動作安排、去背與 GIF 輸出；GPT-Image-2.5 用於角色圖生成與外觀一致性。執行環境需提供該圖片模型；模型可用性以實際環境為準。
- **Grok**：已登入且具備影片生成權限與額度；repo 已內建影片提交、查詢與下載功能，使用官方 Grok CLI 登入，詳見 [Grok 使用方式](references/grok.md)。
- **本機環境**：Python 3.11 或以上、`requirements.txt` 套件，以及 FFmpeg／ffprobe。

已有影片或透明 PNG 畫格時，可直接轉檔，不必再次呼叫 Grok。

## 使用方法

製作流程：**Grok 動作參考影片 → Codex 與 GPT-Image-2.5 角色製作 → 連續畫格、透明背景與 GIF 輸出**。以相同角色設定與參考圖維持外觀一致，並檢查動作銜接。

提供參考圖：

> 使用 $video-gif-studio，參考這張人物圖，製作自然連續動作的透明 GIF。

不提供參考圖：

> 使用 $video-gif-studio，設計原創小機器人揮手，生成連續影片並製作透明 GIF。

調整既有影片：

> 使用 $video-gif-studio，把這段影片製成透明 GIF，調整動作速度並驗證輸出。

完整流程見 [SKILL.md](SKILL.md)，工具參數見 [輸出說明](references/export.md)。

## 成功範例

**坐姿換腿：Grok 影片 → 透明 GIF。** 實際成品為 9.93 秒，保留人物與椅子的連續動作。此既有範例直接擷取 Grok 影片畫格製作，並非 GPT-Image-2.5 逐格重繪。

![坐姿換腿透明 GIF](examples/seated-leg-switch/final.gif)

[下載 GIF](examples/seated-leg-switch/final.gif) · [參考圖](examples/seated-leg-switch/reference.png) · [提示詞](examples/seated-leg-switch/prompt.txt) · [來源影片](examples/seated-leg-switch/source.mp4) · [製作紀錄與驗證](examples/seated-leg-switch/README.md)
