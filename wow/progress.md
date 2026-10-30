# progress — wow 輕量：video-gif-studio 吸收 video-director 量測（2026-10-30）
## 工具就緒（開工前）
- Python：已安裝技能的 venv（~/.codex/skills/video-gif-studio/.venv）有 numpy、Pillow、OpenCV；測試用內建 unittest（python -m unittest discover tests），沒有 pytest。
- ffmpeg：PATH 上沒有；venv 有 static_ffmpeg 可提供。GIF／APNG／PNG 檢查不得依賴 ffmpeg（acceptance.md）。
- 截圖／錄影：本次以報告與三張檢視圖為主，不需 Playwright。
## 步驟
- [x] 1 規格（spec.md，Opus）＋驗收條目（acceptance.md，獨立評審 Claude 子代理）
- [ ] 2 建造（Codex gpt-6-astra）
- [ ] 3 審查一 → 修正 → 審查二（Claude 子代理，異模型）
- [ ] 4 首次使用＋示範（wow/demo/）
## 計時（驗證輕量預估 3 小時）
- 規格與驗收條目：18:55 → 19:48
