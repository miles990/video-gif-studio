# 懷疑論研究員報告 — fx 框架與「AI 導演」計畫（2026-11-04）

範圍：讀了 wow/fx/spec.md、spec-2.md、spec-3.md、spec-4.md、process.md、progress.md，以及 SKILL.md、references/fx.md、
references/timeline.md、references/music.md、scripts/video_export.py、scripts/qa_media.py、wow/fx/benchmark-latest.json。
立場：刻意找反證。只讀，不改程式。外部說法附來源；沒有官方來源的會註明。

---

## 0. 先講最重要的三個發現（都是在 repo 裡查得到的事實，不是意見）

1. **成片是 100 fps 的 MP4。** `scripts/video_export.py:27,52` 用 `-framerate 100` 編碼（重複格表達 10ms 網格）。
   短影音平台接受約 23–60 fps，常見建議 30 或 60 fps（第三方整理，TikTok 未見官方文件：
   https://ayrshare.com/docs/media-guidelines/tiktok 、https://www.heyorca.com/blog/tiktok-media-specs-best-practices-2026 ）。
   上傳後平台會重新取樣，**我們花大力氣做的「10ms 拍點插格」、精確落拍，會在平台端被丟格或被重排**；
   最壞情況是被拒收或被當成異常檔。這直接打到「qa_media 量得到落拍」這個驚豔時刻的意義：量的是本機檔，不是觀眾看到的。
2. **整支成片留在記憶體裡。** fx.md：「the existing exporter still retains the complete short output film in memory」；
   timeline.md：「It currently retains all images in memory…use a streaming editing pipeline for long/high-resolution」。
   算一下：1080×1920 RGBA uint8 ≈ 8.3 MB／格，30 秒 × 30 fps = 900 格 ≈ **7.5 GB**（若中間保留 float32 則 ×4 ≈ 30 GB）。
   這台 16 GB、共用、已經兩次因記憶體不足被收掉的 Windows 機器，**第四輪「20 段手機素材→一支 9:16 成片×3 版本」幾乎必然 OOM**。
   目前所有示範與基準都是 720p 以下的幾秒短片，沒有一次接近真實交付規格。
3. **效能數字只在最樂觀條件下達標。** 10.1 fps 是「720p、三個便宜效果（grade＋halation＋beat_bounce）＋crossfade、不含 PNG/編碼 I/O」。
   1080×1920 是 720p 的 2.25 倍像素；而 cutout_card 269 ms、multi_cutout 407 ms、echo 167 ms、halftone 134 ms、text 127 ms、
   光流補格 301 ms／格（皆 720p 單格，fx.md「Round 2 performance」），RIFE 在 480×270 一格 665 ms。
   一支 30 秒 1080p、含慢動作與摳像的片，粗估每版數分鐘到十幾分鐘；×3 版本 ×最多 3 輪修訂 → **「幾秒內 say yes or no」與現架構互相矛盾**。

---

## 1. 我們在哪些地方「比使用者現在就能拿到的東西差」

| 對手 | 他們已經有、我們沒有或更差的 | 來源 |
|---|---|---|
| CapCut | 模板一鍵套用（換素材即可）、官方模板創作者分潤計畫＝龐大且持續更新的「爆款節奏」庫；自動字幕；Beat Sync；Auto Cut（依音樂拍點或口播停頓切）；商用曲庫 | https://www.capcut.com/partners/template-creator-us 、https://www.capcut.com/help/how-to-use-auto-cut |
| DaVinci Resolve 20 | AI Music Editor（把歌自動剪到目標長度）、AI Detect Music Beats（拍點吸附）、AI Animated Subtitles（逐字動態字幕）、IntelliScript（依腳本組時間線）、AI Audio Assistant（自動混音）、Multicam SmartSwitch；免費版即可用多數功能 | https://www.engadget.com/apps/davinci-resolve-20s-latest-ai-feature-can-create-an-entire-timeline-based-on-a-script-120009351.html 、https://www.newsshooter.com/2025/05/27/davinci-resolve-20-final-release/ 、https://www.provideocoalition.com/davinci-resolve-20-released/ |
| Premiere Pro | Remix：把歌縮短到指定長度（例：2:54 → 30 秒得 29:18） | https://larryjordan.com/articles/remix-comes-to-adobe-premiere-pro-v22-2/ |
| Descript Underlord | 「代理式」共同剪輯：文字下指令、去停頓／贅詞、出社群短片、Studio Sound 人聲修復、跨專案記住偏好；有 API／MCP | https://help.descript.com/hc/en-us/articles/36803785502221 、https://www.createwith.com/tool/descript/updates/descripts-underlord-now-remembers-your-editing-preferences-across-projects |
| Remotion＋agent skill | 用 React/CSS 排版的動態文字與圖形（字型、排版、Lottie 等網頁生態）；Whisper 逐字時間＋`createTikTokStyleCaptions` 現成；已有大量 Claude Code／agent skill | https://www.remotion.dev/docs/captions （社群指南：https://didof-dev.pages.dev/en/blog/guide-subtitles-automatic-whisper-remotion 、https://motionbox.io/blog/remotion-for-coding-agents ） |
| FFmpeg 本身 | `xfade` 內建數十種轉場（wipe/slide/circleopen/radial/pixelize/zoomin/hblur…，C 實作、快）、`lut3d` 讀 .cube、`loudnorm`（EBU R128 兩段式）、`subtitles`/`ass`（libass 動態字幕）、`zscale`/`tonemap`（HDR→SDR） | https://ffmpeg.org/ffmpeg-filters.html#xfade 、https://ffmpeg.org/ffmpeg-filters.html#loudnorm 、https://ffmpeg.org/ffmpeg-filters.html#lut3d |

具體地說，我們較差的地方：
- **文字／字幕**：短影音「看起來專業」最大宗是字幕與動態文字。我們只有一個 PIL 畫的 `text`（pop 進場＋隨拍 10% 縮放），
  且 spec 第一輪、第二輪把「字幕」「語音轉字幕」列為**不做**；第四輪分鏡表卻有「字幕」欄位、lint 要「字幕不擋主體」——
  **沒有字幕來源，卻在驗字幕**。CapCut、Resolve、Remotion 全都有逐字時間的動態字幕。
- **素材聲音**：SKILL.md 明說「Source clip audio is not automatically retained」。手機素材的現場聲、口播、笑聲全丟。
  這讓 Vlog、口播、產品介紹——短影音的主流題材——**整類做不了**，只剩「純配樂卡點混剪」這個窄類型。
- **音樂長度適配**：計畫只會在歌上找拍、截 `music.in_ms`，不會把歌剪到 15/30/60 秒（依小節剪接＋交叉淡入、保留結尾）。
  Resolve、Premiere 一鍵就有。
- **響度**：qa_media 只**量** −14 LUFS（`qa_media.py:352`，只是 WARN），但管線沒有任何**正規化**步驟；
  S-28 再疊合成音效，只保證 true peak ≤ −1 dBTP，不保證整體響度。平台多以約 −14 LUFS 作為慣例目標並只會往下調
  （非官方：https://openclip.app/learn/audio-normalization 、https://dj-master-web.vercel.app/en/blog/youtube-loudness-standard-en ）。
- **轉場自己重寫一遍**：crossfade、push/slide、shape_wipe、luma_wipe、zoom_through、spin 大多是 ffmpeg `xfade` 已有的東西，
  我們用 numpy 慢 50–120 ms／格去重做。唯一有獨特價值的是「保留 alpha」與「拍點包絡」。
- **模板／爆款節奏庫**：CapCut 有一整個由真人創作者持續產出、有分潤動機的模板市場。我們的 S-14/S-31「逆向＋模板轉移」
  要從一支片自動拆出事件，正確率未知，產能是 1 支／次。數量級上打不過，也不需要打。

我們**真的比較好**的地方（誠實列出，好決定往哪押）：本機、離線、可重現（seed＋sha256）、alpha 正確（APNG/RGBA/精靈圖）、
pixel-art nearest 取樣、拍點以毫秒精度、可量測 QA、計畫是 agent 好寫的 JSON。這些對「遊戲角色／像素動畫／貼圖 GIF」是護城河，
對「手機素材剪成 Reels」幾乎不是賣點。**第四輪把戰場移到對手最強的地方。**

---

## 2. 過度建造、邊際價值低（建議砍或延後）

依「會不會改變成片好壞」判斷：

1. **fx_reverse＋模板轉移（S-14、S-31）**：已在審查一「拆不了自己的片」；要辨識甩鏡／縮放衝擊類型還要做混淆表。
   成本高、正確率天花板低、法律灰色（下載他人影片多違反平台條款；概念上只轉移結構雖可，但使用流程會鼓勵抓別人的片）。
   一個人工寫的「節奏模板」JSON（10 行）就能取代 90% 用途。**延後；保留「剪點偵測」給 shot_index 用即可。**
2. **長尾風格效果**：kaleidoscope、halftone、posterize、mirror、dust_scratches、invert_flash、spin、glitch、shape_wipe 的 star/heart、
   multi_cutout。這些正是 spec.md 自己寫的「未抵達：看起來廉價或像預設濾鏡」。process.md 的品質閘門大概會刪掉一半——
   **那就先不要建**，把建造與評審時間省下來。
3. **四種補格模式（none/blend/flow/rife）**：使用者只需要「好的慢動作」。留 flow 預設、RIFE 選用；blend 只作內部比較，不需公開。
   更關鍵：補格只在**有真實慢動作素材**時才重要，示範素材多為角色動畫與定格。
4. **程序合成音效（S-28）**：濾波噪聲做的 whoosh/impact 通常一聽就廉價，評審很難用頻譜測試證明「好聽」。
   比較划算：支援使用者／CC0 音效包資料夾＋自動對位＋響度控制；合成只作無素材時的後備。
5. **風格包 5–8 個（S-39）**：在單一風格都還沒被證明好看前就要 8 個，等於 8 倍評審成本。**先 2 個**（定格摳像卡點、Vlog 輕快），驗證後再擴。
6. **2–3 版本＋盲評（S-42）作為預設流程**：把算繪與評審成本乘 3，且（見第 4 節）評審效度存疑。改為「proxy 出 2 版、使用者自己選」，
   LLM 盲評只當參考。
7. **2.5D 視差（S-21）**：可留 experimental；但它依賴 99 MB 模型、只對定格有用，不應排進主線示範的必要條件。
8. **「導演版必須勝過 autoplan」這個標竿**：同一家族模型判同一家族模型產物，勝出不代表人覺得好（見第 4 節）。

---

## 3. 對「AI 導演做出專業、wow 的短影音」最缺的東西（依影響排序）

1. **串流算繪＋正確的交付規格**：逐格送 ffmpeg pipe、不保留整片；輸出固定幀率 30／60 fps（CFR），1080×1920 H.264 yuv420p＋AAC；
   平台預設檔（TikTok/Reels/Shorts：解析度、fps、位元率、檔案上限、安全區）。拍點對齊改在 30/60 fps 格網上做（33.3/16.7 ms），
   而不是 10 ms 網格。**沒有這個，其他一切交付不出去。**
2. **逐字時間字幕＋動態樣式**：faster-whisper（MIT）／WhisperX（BSD-2，wav2vec2 強制對齊取得逐字時間；注意數字與符號可能缺時間戳）
   （https://github.com/m-bain/whisperX ）。用 ASS＋libass 由 ffmpeg 燒入（逐字高亮、彈出、描邊、安全區），不必在 numpy 裡畫字。
   中文需要斷詞與每行字數規則。
3. **保留並處理素材原聲**：口播／現場聲保留、靜音段移除、與配樂 ducking（側鏈）、基本降噪。這打開 Vlog／口播／產品這幾類主流題材。
4. **音樂適配目標長度**：用 downbeat／段落資訊在小節邊界剪接、交叉淡入、保留自然結尾（Premiere Remix／Resolve AI Music Editor 的同等功能）。
5. **響度正規化**：ffmpeg `loudnorm` 兩段式到約 −14 LUFS、true peak ≤ −1 dBTP，混音後再量；這是零依賴、立即見效的「專業感」。
6. **手機素材進料（ingest）**：VFR→CFR、旋轉 metadata、HEVC 解碼、**HDR（iPhone HLG/Dolby Vision 10-bit）→SDR tone map**、
   不同手機的色彩空間標記。真實素材第一步就會在這裡出錯（過曝、灰、歪、音畫不同步），而目前所有測試素材都沒有這些問題。
7. **鏡頭間色彩一致**：先做曝光／白平衡匹配（直方圖或統計色彩轉移）再套風格 LUT；否則 LUT 只會放大鏡頭間差異。
8. **9:16 重構圖**（S-41 已有，應提前）：多數素材是橫的或混的；主體追蹤裁切比任何特效都重要。
9. **快速預覽與決策 UX**：一頁 HTML：每鏡縮圖、入出點、原因、「換掉／保留」按鈕，低解析 proxy 影片在幾十秒內出；
   改一鏡只重算該鏡（S-42 增量）。這才是「say yes or no」。
10. **真實素材的評估集＋人類評分**：至少 10–20 組真實手機素材（不同光線、直橫、口播／無口播），由使用者本人看片給分。
11. **商用安全音樂指引**：使用者多半會用流行歌；本機成片配版權曲上傳會被靜音或認領。文件與導演報告要提示並支援「平台內加音樂」流程（輸出無音樂版＋拍點標記）。

---

## 4. 流程風險

- **CPU／效能**：見第 0 節。Python＋numpy 在 1080p 每格多個 float32 全幅運算，記憶體頻寬是瓶頸；
  許多操作（xfade、lut3d、gblur、zoompan、overlay、subtitles）ffmpeg 濾鏡圖做得更快且串流。
  建議：能用 ffmpeg filtergraph 的用它；numpy 只做 ffmpeg 做不到的（alpha 摳像卡片、拍點包絡驅動參數）。GPU 不是第一步，先砍掉不必要的 float32 全片複製。
- **記憶體**：16 GB 共用、已兩次被 OOM 收掉（progress 19:40、22:00），而且 BiRefNet（973 MB 模型）＋Numba 編譯＋其他工作階段同時跑。
  第四輪會同時需要：shot_index（全素材解碼＋主體遮罩）、3 版本算繪、depth/RIFE 模型。**需要硬性記憶體預算與串流，否則示範本身就跑不完。**
- **範圍蔓延**：18:09 寫第一輪，23:40 已寫到第四輪；第一輪審查二仍判「未達成」就開第二輪；lite 預算「3 小時／subagent ≤ 6」早已超過；
  progress 自己寫「偏離 lite 審查 ≤ 2 輪」。四輪 46 條 S 項疊在一個尚未在真實素材上跑過 1080p 的地基上。
  每次使用者說「還有沒有更好的做法」，回應都是**加功能**，而不是**先把一支真實的片做好**。
- **評估效度**：
  - process.md 說「兩位獨立評審（跨廠商…評審用 Claude）」——兩位評審**都是 Claude**，彼此高度相關，取低分並不能抵消共同偏差。
  - 評審看的是 2 秒小片＋縮圖表；LLM 看縮圖判斷不了閃爍、節奏手感、運動流暢度與聲音，而這些正是剪輯的核心。
  - 盲評 2–3 個版本、每次 n=1 對；沒有一致性統計、沒有人類錨點。研究顯示 LLM 成對評判有系統性的位置偏差，且方向隨任務變動
    （Shi et al., https://arxiv.org/abs/2406.07791 ）；影片編輯評測中，Gemini A/B 評審同樣有一致的位置偏差、跨次一致率僅 83–87%
    （MEDit-Bench, https://arxiv.org/abs/2607.25300 ）。雙順序只能偵測、不能消除偏差；n 太小時「勝出」在統計上沒有意義。
  - 「導演版要勝過 autoplan」是 Goodhart 風險：導演依 lint 與檢查清單優化，評審也依類似清單判，結果是自我一致而非好看。
  - **建議**：人類（使用者）是最終評審；LLM 評審只負責可檢查項（主體出框、字幕擋臉、黑格、落拍）。若要做成對比較，至少 10–20 對、報告一致率與信賴區間。
- **授權**：
  - 字型：系統字型不散布是對的，但把微軟正黑體燒進**商業廣告**成片是否在其 EULA 範圍內需確認；預設應改用 Noto Sans CJK（OFL）並可隨附。
  - 模型權重：BiRefNet、RIFE lite ONNX（第三方轉檔 latentdivergence/fixflix-rife-lite）、Beat This! 權重的訓練資料授權與程式碼授權不同；THIRD_PARTY 已有提醒，建議導演報告也列出本片用到哪些模型。
  - 逆向他人影片：下載 TikTok/IG 影片通常違反平台條款；rea-video 無授權（已只吸收概念，正確）。
  - 音樂：見第 3 節第 11 點，這是使用者最可能踩的坑，比程式碼授權實際得多。
- **與 SKILL.md 既有預設衝突**：SKILL.md 要求「只在使用者要求後期特效時使用、不替角色動作發明特效、特效預設由 Grok 與動作一起生成」。
  第四輪的導演會**自動**選效果與風格包。若不在 SKILL.md 明確劃出「導演模式＝使用者已授權後期特效」的邊界，會讓技能前後矛盾，
  也可能讓原本的角色動畫用途被導演的預設污染。

---

## 5. 建議的重新排序

### 接下來做的 10 件事（依序）

1. **串流算繪＋CFR 30/60 fps 交付**：修掉 100 fps 輸出與整片駐留記憶體；拍點對齊改在輸出格網上。原因：不修就無法上傳、1080p 必 OOM。
2. **平台輸出預設檔＋安全區**（TikTok/Reels/Shorts：1080×1920、30/60 fps、H.264/AAC、位元率、檔案上限、上下 UI 安全區）。原因：專業感的最低門檻，便宜。
3. **響度正規化與混音**：`loudnorm` 兩段式 −14 LUFS／−1 dBTP、配樂 ducking；qa_media 從 WARN 變成閘門。原因：零依賴、立即可聽出差異。
4. **手機素材 ingest**：VFR→CFR、旋轉、HDR→SDR、音訊保留與同步檢查。原因：真實素材第一關；現有測試完全沒覆蓋。
5. **逐字時間字幕（faster-whisper/WhisperX＋ASS/libass 燒入）**，2–3 個動態樣式、中文斷行、安全區。原因：短影音專業感與留存的最大單項。
6. **音樂剪到目標長度**（小節邊界剪接＋淡入淡出＋結尾保留），並輸出「無音樂版＋拍點標記」以便在平台內換授權曲。原因：每支片都需要；對手一鍵就有。
7. **9:16 主體重構圖（S-41 提前）＋鏡頭間曝光／白平衡匹配**。原因：比任何特效都更影響「看起來像專業剪的」。
8. **shot_index（S-36）＋lint（S-38）**，但 lint 只放可量測規則。原因：選鏡與避免堆砌是導演最有價值、也最可驗證的部分。
9. **一頁 HTML 預覽＋逐鏡換掉／保留＋增量重算**（S-33＋S-42 的增量部分），proxy 目標 < 60 秒。原因：「say yes or no」的實際體驗。
10. **真實素材評估集＋使用者本人評分**（10–20 組，含口播與無口播；記錄每支的算繪時間與峰值記憶體）。原因：唯一能證明「wow」的證據，也會揭露上面所有問題。

### 建議砍掉或延後

- 砍：fx_reverse 的轉場類型辨識與混淆表、S-31 模板轉移（改成手寫節奏模板 JSON）。
- 砍：kaleidoscope、halftone、posterize、mirror、dust_scratches、invert_flash、spin、glitch、star/heart 形狀擦除、multi_cutout（或全部留 experimental、不評審、不進文件主表）。
- 砍：公開的 `blend` 補格模式（保留 flow 預設、RIFE 選用）。
- 延後：程序合成音效（改支援音效包資料夾，合成只作後備）。
- 延後：風格包從 5–8 個縮成 2 個。
- 延後：3 版本＋LLM 盲評作為預設流程（改 proxy 出 2 版由使用者選）；「導演版必須勝過 autoplan」的標竿改為人類評分。
- 延後：2.5D 視差維持 experimental，不作示範必要條件。
- 延後：S-29 段落／drop 自動偵測的精緻化（先用 Beat This! 的 downbeat＋簡單能量曲線就夠）。
- 改用 ffmpeg：凡是 ffmpeg `xfade`／`lut3d`／`subtitles` 已有的，不再用 numpy 重寫；numpy 只留 alpha 與拍點包絡的獨特部分。

---

## 來源

- TikTok 規格（第三方整理）：https://ayrshare.com/docs/media-guidelines/tiktok 、https://www.heyorca.com/blog/tiktok-media-specs-best-practices-2026 、https://postfa.st/sizes/tiktok/video
- CapCut：https://www.capcut.com/help/how-to-use-auto-cut 、https://www.capcut.com/help/auto-cut-in-capcut 、https://www.capcut.com/partners/template-creator-us
- DaVinci Resolve 20：https://www.engadget.com/apps/davinci-resolve-20s-latest-ai-feature-can-create-an-entire-timeline-based-on-a-script-120009351.html 、https://www.newsshooter.com/2025/05/27/davinci-resolve-20-final-release/ 、https://www.provideocoalition.com/davinci-resolve-20-released/
- Premiere Remix：https://larryjordan.com/articles/remix-comes-to-adobe-premiere-pro-v22-2/
- Descript Underlord：https://help.descript.com/hc/en-us/articles/36803785502221 、https://www.createwith.com/tool/descript/updates/descripts-underlord-now-remembers-your-editing-preferences-across-projects
- Remotion 字幕與 agent：https://www.remotion.dev/docs/captions 、https://didof-dev.pages.dev/en/blog/guide-subtitles-automatic-whisper-remotion 、https://motionbox.io/blog/remotion-for-coding-agents
- WhisperX：https://github.com/m-bain/whisperX 、https://dev.to/jovan_chan_9500711396d4e6/faster-whisper-vs-whispercpp-vs-whisperx-2026-o29
- 響度（非官方慣例）：https://openclip.app/learn/audio-normalization 、https://dj-master-web.vercel.app/en/blog/youtube-loudness-standard-en
- FFmpeg 濾鏡：https://ffmpeg.org/ffmpeg-filters.html#xfade 、https://ffmpeg.org/ffmpeg-filters.html#loudnorm 、https://ffmpeg.org/ffmpeg-filters.html#lut3d
- LLM 評審偏差：https://arxiv.org/abs/2406.07791 、https://arxiv.org/abs/2607.25300 、https://arxiv.org/abs/2604.28078
- Repo 內證據：scripts/video_export.py:27,52（100 fps）、scripts/qa_media.py:352（−14 LUFS 只是 WARN）、references/fx.md（整片駐留記憶體、各效果 ms／格、10.1 fps 條件）、references/timeline.md:31、SKILL.md:18,27（素材原聲不保留、特效預設政策）、wow/fx/progress.md（OOM 兩次、範圍與審查輪次）。
