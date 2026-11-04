# 主 agent 沙盒外實測（2026-11-04）
- S-11 Beat This!（repo 外 venv C:\Users\User\src\fx-optdeps\venv）：`music_sync.py examples/neon-zen-pv/soundtrack.flac --engine beat_this` 9.8 s → 82 拍、20 重拍（beat_this-neon.json）。
  修正一後重跑（22:50）：bpm 163.636、downbeats_ms 取整到 ms（原缺陷：bpm 寫 82、浮點雜訊）。
- S-12 BiRefNet：同一格 neon 魚（matte-compare.jpg：原圖｜u2netp｜birefnet-general，綠底）。
  u2netp 10.6 s，霓虹燈柱滲進主體＋零星殘塊；birefnet-general 61.6 s（含模型載入，CPU），邊緣乾淨、無殘塊。定格只摳一格，建議定格摳像用 birefnet-general。
- 選用 venv 需要 opencv-python-headless（gif_pipeline 匯入 cv2）；文件應寫明。
- 工作樹沒有 .runtime：ffmpeg 用 VIDEO_GIF_FFMPEG/FFPROBE 指向安裝目錄的 static_ffmpeg。
