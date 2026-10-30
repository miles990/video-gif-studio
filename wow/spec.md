# wow 輕量 — video-gif-studio 吸收 video-director 的量測與審查（2026-10-30）

交付：輕量（wow references/lite.md）。分支 `absorb-video-director`，開發副本 C:\Users\User\src\video-gif-studio；
已安裝的 ~/.codex/skills/video-gif-studio 在驗收通過、合併前不動。
來源：https://github.com/win4r/video-director（MIT，© 2026 win4r；本地 C:\Users\User\src\video-director）。

## 核心情境（只做這一個）
做完一支 GIF／APNG／MP4／RGBA 序列後，一個指令就得到「量得到的品質報告＋三張檢視圖」，
不必逐格看就知道：第 0 格是否成形、有沒有單格閃爍、凍結、循環接縫跳動、硬切是否照計畫、聲音是否過大或爆音，
並把這份報告接進現有的「Final quality gate」。

## 驚豔時刻與未抵達的樣子
- 驚豔：對 examples/ 裡任一作品跑一次，30 秒內拿到 PASS/WARN/FAIL 報告，指出「哪一格、哪一秒」，附 contact sheet。
- 未抵達：報告只有籠統分數、沒有時間點；或對透明 GIF／APNG 報錯；或把設計好的停格判成凍結而沒有說明怎麼標記。

## 驗收條目（S-編號；核心輸入與預期結果由獨立評審在建造前補上）
- S-1 新腳本 `scripts/qa_media.py`：輸入 MP4、GIF、APNG 或數字命名的 RGBA PNG 資料夾；輸出 report.md、report.json、
  contact_sheet、phone_sheet（360 px 寬）、hook_sheet（0–3 秒）。結束碼：有 FAIL 為 1。
- S-2 檢查項：第 0 格黑／平；單格閃爍與小突波；凍結段（可用 --holds 或 timeline 標記為設計停格）；
  與計畫比對的硬切（讀 compose_timeline 產生的時間軸或 --expect-cuts）；循環接縫的位置＋速度（--loop 或 GIF 本身循環）；
  有音軌時：整合響度、true peak、最響 100 ms、靜音段。透明素材：只在 alpha 覆蓋區比較，不把背景透明當成黑格。
- S-3 SKILL.md「Final quality gate」與「Export and verify」接上這支腳本（何時跑、報告怎麼讀、數字證明不了什麼）；
  新增 references/quality-review.md：獨立評審（不帶建造歷史、預設拒絕、引用格號、只看畫面重述主旨）與完成定義清單，
  內容改寫自 video-director 的 Quality gates／Definition of done，適配 GIF 與 sprite（例如 sprite 不檢查響度）。
- S-4 授權：README 與新檔標註來源與 MIT 版權聲明；THIRD_PARTY 或 LICENSE 附註。
- S-5 測試：tests/ 加離線測試（合成短片：含 1 格閃爍、2 秒凍結、接縫跳動、正常循環各一），既有測試仍全過。
- S-6 doctor.py 檢查新腳本的相依（numpy、Pillow、ffmpeg/ffprobe 已有）不新增必要套件。
- S-展示 對 examples/ 至少兩個作品（一個透明 GIF、一個 MP4 含音樂）實跑，報告與三張圖放進 wow/demo/，交付對照表附路徑。

## 不做
程式碼算繪影片（HTML/Canvas/Remotion）路線、旁白轉錄、video-director 的 evals。另列為之後候選。

## 預算
3 小時、subagent ≤ 6；截止：2026-10-31 12:00 Asia/Taipei（A1 生成前完成或延後合併）。
