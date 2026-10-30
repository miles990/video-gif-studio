# progress — wow 輕量：video-gif-studio 吸收 video-director 量測（2026-10-30）
## 工具就緒（開工前）
- Python：已安裝技能的 venv（~/.codex/skills/video-gif-studio/.venv）有 numpy、Pillow、OpenCV；測試用內建 unittest（python -m unittest discover tests），沒有 pytest。
- ffmpeg：PATH 上沒有；venv 有 static_ffmpeg 可提供。GIF／APNG／PNG 檢查不得依賴 ffmpeg（acceptance.md）。
- 截圖／錄影：本次以報告與三張檢視圖為主，不需 Playwright。
## 步驟
- [x] 1 規格（spec.md，Opus）＋驗收條目（acceptance.md，獨立評審 Claude 子代理）
- [x] 2 建造：qa_media、文件、授權、doctor、17 個新增測試已實作；完整指定環境回歸仍待驗（詳下）
- [x] 3 審查一 → 修正 → 審查二（Claude 子代理，異模型）
- [x] 4 首次使用＋示範：wow/demo/ 已產生並檢視圖像；獨立首次使用仍交原流程執行
## 計時（驗證輕量預估 3 小時）
- 規格與驗收條目：18:55 → 19:48

## 建造者交回（2026-10-30；尚非獨立驗收通過）
- 依使用者本次明確指派直接擔任 builder，未另派 agent 或冒充獨立評審；交付報告見 `wow/DELIVERY.md`。
- 指定 Python `C:\Users\User\.codex\skills\video-gif-studio\.venv\Scripts\python.exe` 無法存取（WinError 5）。未更動安裝技能、權限或安裝任何套件。已提出環境資訊問題。
- 使用既有 `C:\Users\User\miniforge3\python.exe`（numpy/Pillow；缺 cv2）與現有 imageio FFmpeg 7.1 完成可執行驗證。偏離指定 Python 是因原路徑遭環境拒絕，不能視為指定回歸已通過。
- 工具補強：qa_media 經 media_runtime 取 ffmpeg/ffprobe；只有 FFmpeg 時以 showinfo 讀實際 PTS/duration，額外 decode 不猜固定 FPS。此備援已用於 neon 與三個音訊整合測試。
- 17 個新增測試全過（核心 14 個不使用 ffmpeg；3 個音訊實測），牆鐘 15.994 秒。完整 discover 在替代環境跑 73 tests：16 errors、1 skipped、0 failures；只跑既有測試也是相同 16 errors、1 skipped、0 failures（56 tests）。錯誤包含 cv2 缺失和既有 runtime/Windows 問題，不等同答案卷允許的 5-error 環境基準。S-5 完整回歸仍未驗收。
- GIF/APNG 實際可變延遲、透明隱藏 RGB、部分 hold 扣除、長時間單格 hold、重複編碼格、位置/速度接縫與 continuation timeline 已納入回歸。
- 示範牆鐘：chibi GIF 2.251 s、APNG 2.327 s、neon（含 timeline）10.224 s、neon（無 timeline）10.281 s、robot 2.234 s、seated 5.097 s。全部低於 30 s。正反例回傳碼符合預期；詳 `wow/demo/run-times.json`。
- 已觀看 chibi contact sheet 與 neon hook sheet，確認縮圖、透明棋盤與格號/秒數標籤；未聲稱完整播放/聆聽或獨立藝術品質認證。
- `wow/acceptance.md` SHA256 保持 `21A3F0C43873A83319BB7903166D2508856289B5AC292727A8944A7B93254A1F`。examples/、requirements.txt 未改。未 commit、push、publish。
- 下一步：原協調者在可存取的指定 venv 執行 `python -m unittest discover tests`，確認僅原 5 個環境錯誤或更少；再由獨立評審執行答案卷與首次使用。本建造交付目前標記為「待完整回歸的候選」。
- 建造（Codex）：19:50 → 約 21:00；回歸（Opus，技能 venv）：142 tests，與改前相同 2 個既有錯誤，0 退步
- 審查一（Claude 子代理）READY＋6 點；修正（Codex）；審查二（Opus 逐點驗證）通過；回歸 146 tests／2 既有錯誤／0 退步
- 首次使用（全新 clone、只照 README）：GIF 3 s、MP4 12 s，五個輸出齊全
