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
- 03:30 P0 獨立審查：未可合回（ducking 只降 5.74 dB、起點偏移＋時間跳躍的手機片被拒、舊 100fps 路徑 PSNR 42.7 dB、真奇數尺寸失敗，另 4 小項）；S-50 串流 527 MB、3 分鐘長片 580 MB、平台預設、HDR、proxy 皆過；720p 7.25 vs 10.12 非回歸（量法不同，同法重跑 10.78 vs 10.69）。派 P0 修正（繞過佇列，延續使用者對 P0 的「繞過，繼續做」）。
- 03:46 P0 修正（p0-fix）跑 5.5 分、改 6 檔時被 Claude Code 因系統記憶體不足收掉；WIP commit 保存，等使用者同意再續跑。
- 04:00 使用者：「繼續，重啟修正， 全部做完」→ 視為持續授權：依序完成 P0→P1→P2→spec-6→spec-7→spec-8→P3；被記憶體收掉時直接續跑並回報。保留樣本、brief、審查報告移到 repo 外 C:\Users\User\src\vgs-fx-private（舊 scratchpad 停用）。
- 04:45 P0 複審：8 項中 7 項過；但固定增益正規化造成退步（MUS＋CLIP-A、只有說話被擋在 −17～−26 LUFS）、立體聲被收成單聲道、底音觸發語音偵測、長片 ducking 失敗、intake 未記跳躍。派修正二。
- 05:30 P0 第三次獨立審查：可合回（所有響度情境 −14.0 LUFS 並發布、立體聲保留、無抽吸、長片 ducking、舊路徑位元相同）。合回 main 584987f 並 push；安裝目錄 doctor 通過、合成計畫實跑輸出 30/1 CFR。刪除 p0-delivery 分支，開 p1-edit。剩 2 個非阻擋文件項（低 SNR 不 duck、跳躍長度含前一丟格）併入 P1。
- 06:20 P1 建造完成（292 tests／0 failures）commit d1f3d92；協調者實測發現 faster-whisper 路線 4 個缺陷、Kenney 403（wow/fx/live/p1-live.md），真實輸出存為 tests/fixtures/live。開 P1 獨立審查。
- 06:45 P1 獨立審查：可以 experimental 身分合回，但 P1 驗收不過（重構圖黑邊 46–57%、主體在框 20%/94%；whip 停在鏡像；字幕像電視字幕；斷行不看句界；emoji 直接失敗；點綴不分檔、白閃過多；協調者實測 4 缺陷皆確認，根因 np.float64 型別比對）。派 P1 修正。
- 07:35 P1 修正（Codex 21 分）完成 310 tests；誤提交 10 MB 審查影片已 untrack（P1 將 squash 合回避免 main 歷史膨脹；協調者 commit 指令改為 preflight 失敗即停）。實測 whisper：繁中可用，剩全形標點、英文前導空白。開 P1 複審。
- 08:20 P1 複審：可 experimental 合回；驗收不過（字幕內容完整性、空白／標點、關鍵字、crash_out、qa 誤判運鏡、pop 單字）。fx.md 加已知問題後 squash 合回 main 7f392cf（main 不含 10 MB 審查影片）；安裝目錄全套 310 tests／2 env errors、doctor 通過；push。開 p1b-fix。
- 10:05 P1b 獨立審查：可合回；字幕完整性 408 項 0 失敗、快語速過；新缺陷 2（長字中止、拉丁詞內標點誤轉全形）＋3 小項。squash 合回 main ca62445（安裝目錄 323 tests／2 env errors、doctor 通過）並 push。剩餘 5 項併入 P2 Part A；fx.md 補 Open defects。字幕預設閘門分：pop 4（修長字後過）、bounce 4 過、typewriter 3、clean 2。
- 10:30 使用者 /wow「門檻是否合適?…」→ 依 wow 規則（數字是儀器、正負對照、錨點重定基線）派獨立門檻稽核員：盤點 acceptance-1～9 與品質閘門的所有門檻、分類來源、對 agent 自訂者用錨點與正負對照校準（能現在跑的就實跑），並重設計品質閘門（wow-judge 混合評審團 sonnet/opus/codex、雙順序、聯絡單、金標、檢定力＋使用者抽查）。輸出 wow/fx/thresholds.md。
- 10:45 使用者 /wow「門檻是否可以動態自動調整?」→ spec-10.md：門檻登錄檔＋四類（F 固定／R 棘輪只收緊／C 好壞錨點分布校準／U 使用者品味）＋防作弊護欄（同輪改動延後生效、錨點重判、步幅上限、漂移偵測、審計）＋產品執行期同用＋錨點庫。已請門檻稽核員把每個門檻分類並提出 registry schema。
- 11:20 門檻稽核完成（wow/fx/thresholds.md，約 230 個門檻、四類分法、registry schema）：實驗證實 spec-6 可見度單一門檻不可能同時過正負對照、舊品質閘門近擲硬幣、3 筆抽查 70% 規則會誤判、Kendall τ≥0.6 在 5–6 項太鬆、jerk 平滑 fixture 算錯（實為 690–1770°/s³）。process.md 品質閘門改為成對比較＋wow-judge 混合評審團＋正負對照＋預先登記判定。答案卷修正交由獨立出題者核實後寫 acceptance-amendments.md。
- 12:10 答案卷修正（acceptance-amendments.md）：獨立出題者逐條驗算稽核旗標，約一半成立（品質閘門、Kendall、jerk 夾具、幾何必敗條目、量法錯誤、記憶體改棘輪）、一半推翻（±10 ms、follow 文字等維持原文），拒絕會放寬外部標準的建議；可見度等列待校準。process.md 補：每批 10–12 格、平手＝兩順序不一致。
