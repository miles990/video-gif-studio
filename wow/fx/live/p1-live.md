# P1 協調者沙盒外實測（2026-11-05）
- 語音素材：Windows SAPI TTS（Microsoft Zira en-US、Microsoft Hanhan zh-TW）產生 tests/fixtures/live/speech-{en,zh}.wav；faster-whisper small（int8, CPU）原始輸出 tests/fixtures/live/whisper-raw-{en,zh}.json（19／29 字，無空字或零長度字）。
- 缺陷 1：faster-whisper 1.2.1 與 PyAV 19 不相容（av.open() 不接受 metadata_errors）。選用 venv 暫以 av<16 繞過；產品應改為 captions 以 ffmpeg 自行解碼成 16 kHz float32 陣列餵給 transcribe，不依賴 PyAV 版本。
- 缺陷 2：captions.py --audio 對真實輸出報「words require nonempty text and finite 0 <= start_ms < end_ms」並 exit 2（en、zh 皆然）；原始輸出本身合法 → 秒轉毫秒後的浮點／取整或驗證邏輯有誤。
- 缺陷 3：中文輸出為簡體（画），未傳 language；繁中使用者需要 language/initial_prompt 或 OpenCC（Apache-2.0）簡轉繁選項。
- 缺陷 4：model 參數要求的是快照目錄（models--Systran--faster-whisper-small/snapshots/<hash>），給 download_root 會報 model.bin 找不到；應接受 cache 根目錄或模型名＋本機 cache。
- Kenney：kenney.nl 對自動下載回 403（站方阻擋自動化）；不繞過。download_kenney_audio.py 應明確改為「使用者手動下載後 --zip」，並在缺包時退回程序合成。

## 修正後重跑（2026-11-05）
- `captions.py --audio speech-en.wav --model small --model-cache <whisper root> --language en` 5 s；`--language zh --traditional` 6 s；皆 exit 0，輸出 captions.json／srt。
- 中文已為繁體（畫、彈、現）；ASR 本身把「每一格」聽成「每一個」（模型誤差，非程式問題）。
- 剩餘小缺陷：中文逗號輸出半形「,」（繁中排版應為全形「，」）；英文字首帶空白（" Every"）。
