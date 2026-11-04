# progress — wow 輕量：fx 程式化特效／轉場框架（2026-11-04）

## 決定
- 交付模式：輕量（使用者只說「使用 wow 技能」；需求已指定、單一核心情境、同 repo 上輪也用輕量）。撤回：改說「做成品」即從步驟 3 接續。
- 開發副本 C:\Users\User\src\video-gif-studio，分支 fx-framework；已安裝 skill 不動。
- 建造者 Codex（wow-agent），出題與評審 Claude 子代理（跨廠商）。一次只跑一個重任務（16 GB 機器，見 agent-conduct 5）。
- 摳像：Windows 無 Mac「拷貝主體」，沿用 repo 既有 alpha／background_remove（spec「不做」）。

- 18:25 使用者：「吸收 改善…用最好的做法做」→ spec 加 S-10～S-13（onset 包絡、Beat This! 重拍、BiRefNet 摳像、使用者層級效果庫）。
- 18:35 使用者貼第二則推文（rea-video，無授權）→ spec 加 S-14 逆向（只吸收概念、自行實作）。範圍擴大，3 小時預算可能不足：超過時先保核心 S-1～S-9＋S-展示，S-10～S-14 依序取捨並如實回報。
- 選用依賴裝在 repo 外 C:\Users\User\src\fx-optdeps\venv（torch CPU、beat_this、rembg），不污染技能 venv。

## 工具就緒
- 開發副本 .venv 存在；已安裝 skill venv：numpy 2.5.4、Pillow 13.0.0、OpenCV 5.0.0。Codex CLI 0.166.0。磁碟 C: 剩 30 GB。

## 步驟
- [x] 1a 規格 spec.md（18:09）
- [x] 1b 驗收條目 acceptance.md（獨立 Claude 出題者，18:50 完成）＋保留樣本 14 條（repo 外 scratchpad/fx-holdout.md）
- [x] 2 建造（Codex fx-build2，完成）
- [ ] 3 審查一 → 修正 → 審查二
- [ ] 4 首次使用＋示範
- 19:10 選用依賴實測（repo 外 venv）：Beat This! final0 CPU 在 neon soundtrack 17.1 s → 82 拍、20 重拍（≈164 BPM、4/4；與既有 tempo 候選 82/164 一致）。BiRefNet 下載遇 SSL 抖動，改 curl 續傳中。
- 19:40 建造派工 fx-build 在共用佇列等待時，Claude Code 因系統記憶體不足（可用約 3.6 GB，其他工作階段的 probes／competitors 佔用）把它收掉；建造尚未開始，repo 無半改檔。等使用者同意後用 `wow-agent --resume 20261104-101808-fx-build` 續跑。
- 19:20 BiRefNet-general 模型（973 MB）已下載到 .runtime/models（gitignored），rembg 載入成功。
- 19:50 發現 C:\Users\User\src\video-gif-studio 是已安裝 skill 的 junction（spec 的「已安裝 skill 不動」原本不成立，fx-framework 分支其實切在安裝目錄上）。已把安裝目錄切回 main，改用獨立 worktree C:\Users\User\src\vgs-fx。上一次續跑因 --resume 沒帶寫入權限而唯讀、零改檔；重新派工 fx-build2 並明示 --sandbox workspace-write。
- 20:55 建造（Codex fx-build2）完成：172 tests／0 failures／2 既有環境錯誤；建造者自評「未完成候選」（S-2 zoom 條紋條件、S-展示 --expect-cuts、S-7 720p 3.27 fps < 10）。commit 723abd6（中間影格與 14 MB GIF 不入庫，wow/fx/.gitignore）。
- 21:10 主 agent 沙盒外實測 S-11／S-12（wow/fx/live/）：Beat This! 可用但 bpm 欄位錯成 82、重拍浮點雜訊；BiRefNet 明顯優於 u2netp。
- 21:15 審查一（獨立 Claude 子代理，含 14 條保留樣本）進行中。
- 21:40 審查一（獨立 Claude）判「未達成」：框架本體過（S-1/3/4/6/9/13），但成片沒有記憶點（定格不是摳原鏡頭主體、卡片沒隨拍彈、甩鏡接縫、太暗）；S-10 成片中重輕拍隨機；fx_reverse 拆不了自己的片；示範無法 fresh clone 重現；保留樣本 6/14 不過。完整審查留在 scratchpad/review1/review.md（含保留樣本細節，不給建造者、不入庫）。
- 21:45 修正一（Codex fx-fix1）派工：8 點修正清單（保留樣本只以一般化描述轉達）。
- 22:00 修正一（fx-fix1）跑到 11m43s 時被 Claude Code 因系統記憶體不足收掉（BiRefNet 摳像＋Numba 編譯＋其他工作階段）。已改 12 檔、未完成；殘留程序已確認無。半成品以 WIP commit 保存，待使用者同意後 `--resume 20261104-125709-fx-fix1 --sandbox workspace-write` 續跑。
- 22:10 使用者：「好都做, 看還有沒有更好的做法?用最好合適的做法做」→ 第二輪規格 spec-2.md（S-15～S-24＋S-展示2：時間重映射、光流／RIFE 補格、畫格歷史、約 25 個新效果與轉場、2.5D 視差）。模型已下載：depth-anything-v2-small.onnx（Apache-2.0）、rife_v4.25_lite.onnx（MIT）。
- 22:25 第二輪獨立答案卷 acceptance-2.md＋保留樣本 12 條（scratchpad/fx-holdout-2.md）完成。第二輪建造排在第一輪修正＋審查二之後。
- 22:45 審查二（另一位獨立 Claude）判「未達成，差距很小」：成片已是定格摳像卡點、S-10 修好、fresh clone 位元一致重建；剩 H7/H10/H13、縮放偵測退步、S-12 traceback、示範定格不是原地浮起等 8 點。決定：併入第二輪建造的 A 部分（省一輪往返），第二輪審查同時重驗 A 部分＋保留樣本 1。偏離 lite「審查 ≤ 2 輪」：因使用者追加第二輪範圍，審查輪次按輪別各自計。
- 22:50 第二輪建造（Codex fx-build3：A1–A8＋S-15～S-24＋S-展示2＋效能）派工。
- 23:00 使用者再問「還有沒好的效果、更好的做法」→ 第三輪規格 spec-3.md（S-25～S-35＋S-展示3：主體感知錨定與主體轉場、程序合成音效層、音樂段落／drop 與自動草稿、模板轉移、LUT、快速預覽、運動模糊）。獨立出題者寫 acceptance-3 中。排在第二輪審查通過之後建。
- 23:10 使用者：「我要效果多 同時也效果好 不夠好的不要 然後是trunk based」→ process.md：每個效果過品質閘門（自動檢查＋兩位跨廠商評審取低分 ≥ 4 才 stable；3 分重做一次；不夠好就刪）；改 trunk-based（短命切片、experimental 旗標、過審即合回 main）。進行中的 fx-build3 不中斷，完成後依此流程拆切片合回。
- 23:25 第三輪獨立答案卷 acceptance-3.md＋保留樣本 14 條（scratchpad/fx-holdout-3.md）完成。
- 23:40 使用者 /wow「ai 導演…找到適合最好的做法」＋「做」→ 第四輪規格 spec-4.md（S-36～S-46＋S-展示4）：素材索引（量得到的品質用程式量）、處理方案＋分鏡表、效果文法 lint、風格包、選鏡對拍、9:16 重構圖、多版本＋盲評選片、評論修訂迴圈 ≤3、缺鏡處理、導演報告。調查依據：L-Storyboard、EditDuet、CineCut-Agent、agentic-video-editor、arXiv 2509.16811（只吸收概念）。獨立出題者寫 acceptance-4 中。順序：第二輪→第三輪→第四輪，各自切片合回 main。
- 23:55 第四輪獨立答案卷 acceptance-4.md＋保留樣本 12 條完成。三位研究員（競品／開源與研究＋可吸收清單／懷疑論）調查中。
- 00:15 調查三份（競品／開源＋可吸收／懷疑論）完成並整合為 research/synthesis.md；路線修訂 spec-5.md：P0 交付層（串流、30fps、平台預設、響度、手機素材、效能）→ P1 字幕／音效／節拍分層／音樂裁長／具名運鏡／9:16／proxy → P2 gl-transitions 移植＋閘門 → P3 導演精簡 → P4 進階。偏離：lite 預算早已超過，改以可交付切片推進並誠實記錄。
- 00:30 spec-5 獨立答案卷 acceptance-5.md＋保留樣本 13 條完成。
- 01:05 第二輪建造（fx-build3）完成：A1–A8 與 S-15～S-24 皆標完成；198 tests／0 failures；720p 3.34→10.12 fps；demo2 20.5 s QA PASS。示範 MP4 6.4 MB 以 --allow-large 提交（交付示範，L11 要求在交付物內）。
- 01:35 審查三：第一輪可合回 main（附條件：分支帶著第二輪程式）；第二輪未達成（保留題 6 條不過、demo2 不像卡點混剪、light_leak 等多個效果預設廉價）。決定：先做「功能旗標＋fx_reverse 誤報」切片 → 合回 main＋push；再做第二輪修正與逐效果品質閘門。
- 01:00(11-05) 功能旗標＋fx_reverse 切片完成（繞過被 oab 任務占滿的佇列，使用者同意）：第二輪功能全部 experimental；neon 誤報縮放 17→0；閃白 740/2200 偵測到；協調者複驗 211 tests／2 既有環境錯誤／0 新失敗。合回 main。
- 01:20 第一輪＋功能旗標合回 main（ea2e790）並 push：合回前 doctor 通過、安裝目錄以合成計畫實跑 fx_render（GIF＋MP4，QC 通過）。開短命分支 p0-delivery 做 P0 交付層。
- 02:15 P0 交付層（Codex p0-delivery2，44 分）完成：串流峰值 500 MB、30fps CFR、5 個平台預設、−14 LUFS／ducking 9.9 dB、手機進件、proxy 29%；234 tests／0 failures。清掉建造者留在 repo 根的 8 個暫存腳本。commit cb3f2d5 推到 origin/p0-delivery。獨立審查 P0 進行中（含 holdout-5 的 P0 項）。注意：720p 7.25 fps vs 先前 10.12，待審查判斷是否退步。
- 02:45 使用者 /wow「可以讓AI導演影片用的效果…」→ spec-6.md（S-70～S-77）：效果卡（意圖、觀感強度、需求、搭配音效、成本、閘門分數、預覽）、觀感強度校準、意圖配方、可見度／刺眼度（WCAG 2.3.1）自動檢查、效果預算、關鍵時刻候選、fx_query。排在 P2 之後、P3 導演之前。獨立出題者寫 acceptance-6 中。
- 03:00 使用者 /wow「…並讓影片專業有品味」→ spec-7.md（S-80～S-89 品味系統）：吸收使用者 wow 詞彙檔（mood-pacing-arc §E M1–M16、喚起度代理曲線、mastery-signals、Murch Rule of Six）成 taste_report 量測、設計曲線對照、大師訊號 lint、剪輯文法 lint、風格 token、鏡頭配色一致、參考片校準、使用者品味校準。獨立出題者寫 acceptance-7 中。
- 03:10 使用者：「還有分鏡 也能用的」→ spec-7 加 S-90～S-94：分鏡格式含鏡頭語言＋意圖配方、算繪前分鏡品味 lint（預測強度曲線、景別遞進、30°/180°、一鏡一運動、預算）、動態分鏡（無素材用剪影卡）、由分鏡產生成提示詞（含 coverage）。
- 03:25 使用者 /wow「…規劃設計分鏡運鏡…專業有品味」→ spec-8.md（S-100～S-109）：虛擬攝影機模型（jerk 上限）、2.5D 運鏡算繪（推拉、dolly zoom、rack focus）、真實手持頻譜、運鏡語言庫＋cam_query、從參考片抽運鏡、跨鏡運鏡連貫 lint、分鏡本＋俯視機位圖、運鏡→生成控制引導片（接 motion_pack）、運鏡量測。acceptance-6 完成（含實測校準，保留樣本 11 條＋參考排序）；acceptance-7、-8 撰寫中。
- 03:35 acceptance-7 完成（S-80～S-94，約 25 支已知答案合成片；保留樣本 12 條）。
- 02:45 更正：本檔 02:45～03:35 幾筆時間是預估值寫早了，實際都在 02:20～02:45 之間；以 git commit 時間為準。
- acceptance-8 完成（針孔幾何精確答案、手持頻帶、運鏡回推門檻；保留樣本 10 條）。
