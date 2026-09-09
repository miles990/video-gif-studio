# 範例：無參考圖的原創機器人揮手

[English](README.md) | **繁體中文**

![原創機器人揮手透明 GIF](final.gif)

**沒有使用任何使用者提供的參考圖**，從文字設計原創機器人。成品是 6.04 秒、512×512、145 格的透明 GIF。

## 製作流程

1. Codex 設計角色與動作，內建圖片生成工具依 [image-prompt.txt](image-prompt.txt) 建立 [character.png](character.png)，沒有輸入圖片。工具未回報確切模型版本，因此不將此範例標示為 GPT-Image-2.5。
2. 原創角色圖作為 Grok 的唯一影片起始圖。「無參考圖」指沒有外部或使用者提供的視覺參考；實際路線為原創圖片轉影片，不是宣稱直接使用文字生成影片。
3. 透過 repo 內建 `grok_client.py`，將 [motion-prompt.txt](motion-prompt.txt) 提交給 `grok-imagine-video-1.5`，恢復查詢並下載 [source.mp4](source.mp4)。這次是真正使用內部連接程式生成，沒有外部專案 adapter。
4. 輸出工具去除洋紅背景，保留來源速度，以專用透明索引和全片統一色盤製作 GIF。沒有光流補幀、獨立姿勢重繪或反向播放。

## 驗證

145 格 GIF 解碼後的透明遮罩與來源 RGBA 二值遮罩完全一致，**新增透明破洞為 0**。已用[深淺背景抽幀圖](contact.png) 檢查角色外觀及動作過渡；未記錄完整正常速度播放審查。結尾朝向與起點略有差異，因此不標示為完全無縫循環。

[下載 GIF](final.gif) · [原創角色圖](character.png) · [來源影片](source.mp4) · [圖片提示詞](image-prompt.txt) · [動作提示詞](motion-prompt.txt) · [輸出與驗證](export.json) · [來源紀錄](manifest.json)

## 重現輸出

從 repo 根目錄執行，使用新的輸出目錄：

```sh
.venv/bin/python scripts/gif_pipeline.py examples/robot-wave-no-reference/source.mp4 \
  --key FF00FF --tolerance .32 --softness .24 --width 512 \
  --out output/robot-wave --apng
```

去背參數是依此機器人與背景選擇，不是通用預設。重新生成 AI 圖片或影片，即使使用相同提示詞也可能得到不同結果。
