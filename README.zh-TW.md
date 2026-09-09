# Video GIF Studio

[English](README.md) | **繁體中文**

支援有／無參考圖的角色動畫製作 skill：由 **Codex** 協調角色製作、**Grok** 動作與特效生成、去背及透明動畫輸出。角色圖或明確選擇的修復可使用環境提供的圖片工具；**GPT-Image-2.5 可用時亦可使用**。預設保留影片的連續畫格。

授權：[MIT](LICENSE)

## 安裝方法

把下面這段交給 Codex 或其他具備本機操作能力的 AI：

> 請幫我安裝 https://github.com/miles990/video-gif-studio 的 Codex skill。請先讀取 references/install.md，完成 skill 註冊、Python 依賴安裝與 doctor 驗證；保留既有安裝和資料，並分別告知本機 GIF 工具與 Grok 影片生成是否就緒。

AI 安裝流程見 [references/install.md](references/install.md)。此 repo 若為私人狀態，安裝者需具備存取權。安裝後在 Codex 下一次對話回合使用 `$video-gif-studio`。

## 需求

- **Codex**：負責生成協調、動作時長、去背與輸出。建立角色或 AI 修復另需可用的圖片生成工具；環境明確提供 **GPT-Image-2.5** 時可使用，實際模型與 Alpha 輸出能力須確認。既有素材轉檔不需要圖片模型。
- **Grok**：已登入且具備影片生成權限與額度；repo 已內建影片提交、查詢與下載功能，使用官方 Grok CLI 登入，詳見 [Grok 使用方式](references/grok.md)。
- **本機環境**：Python 3.11 或以上、`requirements.txt` 套件，以及 FFmpeg／ffprobe。

已有影片或透明 PNG 畫格時，可直接轉檔，不必再次呼叫 Grok。

## 使用方法

製作流程：**參考圖或原創角色 → Grok 連續動作與所需特效 → 去背 → RGBA PNG 畫格、選用 APNG 與 GIF 預覽**。既有影片可從去背階段開始。未指定時，動作遵循合理人體結構、重心轉移與位移；人物、武器和特效至消散都須完整留在畫面內。所需特效預設由 Grok 設計與生成；要求無縫循環時須檢查實際接點。

提供參考圖：

> 使用 $video-gif-studio，參考這張人物圖，製作自然連續動作的透明 GIF。

不提供參考圖：

> 使用 $video-gif-studio，設計原創小機器人揮手，生成連續影片並製作透明 GIF。

調整既有影片：

> 使用 $video-gif-studio，把這段影片製成透明 GIF，調整動作速度並驗證輸出。

可選擇透明處理方式，未指定時使用「**自動處理**」：

| 模式 | 處理方式 |
| --- | --- |
| **自動處理（預設）** | 保留來源畫格，使用既有 Alpha、色鍵或可用的時序去背工具，不自動逐幀重繪。 |
| **保留原畫優先** | 優先保留角色像素與動作，無法乾淨分離的部分會明確標示。 |
| **AI 修復／重繪** | 明確選擇圖片模型修復，接受外觀可能變動，並重新檢查跨幀一致性。 |

這些是流程選擇，不是命令列參數。內建色鍵適用純色背景；時序去背需要額外工具。更換檔案格式無法找回去背時已刪除的細節。

柔邊、髮絲、煙霧與消散特效應保留 **RGBA PNG／APNG** 主檔。**GIF 只能全透明或全不透明**，適合作為相容預覽。像素風也可以保留半透明；硬邊輪廓與透明光效應分別處理。

遊戲用途建議要求 **PNG 畫格與 Sprite Sheet／Atlas**，已知時請註明引擎。內建工具已提供 PNG 畫格與時長／來源紀錄；**圖集打包、遊戲事件／錨點／位移資料及引擎整合仍需另外實作**。已合成的影片不保證能可靠拆出角色與特效。

> 使用 $video-gif-studio，製作 Godot 用的角色攻擊動畫。保留原畫優先，保留半透明，輸出 PNG 畫格與 APNG 預覽，並規劃引擎適用的圖集；明確告知哪些內容已可匯入使用。

完整流程見 [SKILL.md](SKILL.md)，另見 [透明處理與交付選擇](references/transparency.md) 和 [輸出說明](references/export.md)。

## 成功範例

**坐姿換腿：Grok 影片 → 透明 GIF。** 實際成品為 9.93 秒，保留人物與椅子的連續動作。此既有範例直接擷取 Grok 影片畫格製作，並非 GPT-Image-2.5 逐格重繪。

![坐姿換腿透明 GIF](examples/seated-leg-switch/final.gif)

[下載 GIF](examples/seated-leg-switch/final.gif) · [參考圖](examples/seated-leg-switch/reference.png) · [提示詞](examples/seated-leg-switch/prompt.txt) · [來源影片](examples/seated-leg-switch/source.mp4) · [製作紀錄與驗證](examples/seated-leg-switch/README.zh-TW.md)

**無參考圖：原創機器人揮手。** 從文字設計原創角色，再用 Grok 生成動作影片，製成 6.04 秒、145 格的透明 GIF。

![無參考圖的原創機器人揮手](examples/robot-wave-no-reference/final.gif)

[下載 GIF](examples/robot-wave-no-reference/final.gif) · [製作流程、提示詞與驗證](examples/robot-wave-no-reference/README.zh-TW.md)
