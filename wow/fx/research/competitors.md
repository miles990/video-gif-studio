# 商業競品研究：短影音 AI 剪輯（截至 2026-11）

> 目的：替 video-gif-studio（本機、離線優先、給 Claude Code/Codex 代理用的 Python skill）的特效/轉場框架、音樂節拍分析、主體去背、卡點、參考影片逆向、模板轉移、程序化音效、LUT、變速＋光流補幀、2.5D 視差、9:16 自動重構圖、AI 導演＋盲測選優等規劃，找出競品做法與可借鏡處。
>
> **可信度標記**：〔官〕＝官方頁面／官方新聞稿；〔媒〕＝主流媒體或專業媒體；〔三〕＝第三方評測／聯盟行銷／SEO 站（數字常互相矛盾，僅作方向參考）；〔知〕＝長期存在、廣為人知的功能，本次未逐一重新查證（來自既有知識，2026 年前即存在）。
> 價格多數來源互相矛盾，一律以「約略」看待，請以官網為準。

---

## 0. 一頁結論

- **市場分成三種 UX**：(1) **模板**（剪映/CapCut「剪同款」、快影、Canva）——最多人用、最「穩」、成片最像專業；(2) **風格預設＋一鍵**（Captions AI Edit、Submagic、Opus Clip）——以口播為主，靠「字幕動畫＋自動 zoom＋B-roll＋音效」四件套撐起「專業感」；(3) **對話式 Agent**（Descript Underlord、剪映助手/小映、Captions chat editor、Kapwing Kai、Resolve 21.1 接 Claude/Codex）——2026 年全面普及，但產出仍需人工收尾。
- **2026 的趨勢**：模板從「固定成片」變成「可用自然語言改的模板」（剪映 2026-09 剪同款升級）；Agent 能「看畫面」而不只讀逐字稿（Descript 2026）；專業 NLE 把 AI 放在**遮罩／搜尋／音樂長度適配**等「省工」位置，而不是自動成片。
- **我們的差異化空間**：沒有任何主流產品同時做到「本機/離線＋可程式化特效（effect=f(frame,t)）＋從參考影片逆向成可編輯計畫＋多版本盲測自選」。商業產品的「逆向參考影片」只有剪映 Hub 剛開始做（「從一個參考影片出發」），而且是雲端、黑盒。
- **最該學的不是特效數量**，而是：字幕即設計（逐字動畫）、節拍對齊的「打點層級」、音樂自動改長度、說話者/主體追蹤重構圖、轉場一定配音效（whoosh/hit）、模板＝「槽位＋時間軸骨架」的資料結構、風格預設要少而精。

---

## 1. 各競品逐一分析

### 1.1 剪映 / CapCut（字節跳動）

| 項目 | 內容 |
|---|---|
| 與我們重疊 | 節拍卡點（自動踩點/Beat Sync）、模板（剪同款）、一鍵成片/AI 粗剪、智能摳像（主體去背）、定格＋摳像卡點、曲線變速＋智能補幀（光流）、LUT/濾鏡、特效庫、轉場庫、自動字幕＋動畫字、9:16 智能裁切、AI 配音、Agent（剪映助手/小映）、從參考影片出發（剪映 Hub） |
| 做法/UX | **模板為王**：剪同款＝作者做好的時間軸，使用者只換素材槽。Auto Cut 有三種切法：Beat Sync、Speech Pause Detection、Script-Based，並可調「切點密度」〔官〕。2026-09 發佈會：**剪映 Hub**（無限畫布＋多軌，從「一句話、一個參考影片或一份文件」出發→腳本→調用即夢/小雲雀生圖生影片→進多軌精修）、**剪映助手**（桌面 Agent，可做素材整理、口播刪減、字幕糾錯、包裝，**支援自訂 Skills**）、**小映**（手機 Agent，一句話→自動調用圖/影/文/音樂/AI 生成→可繼續調整的初版，會依情緒推薦流行音樂、轉場、表達方式，並學習使用者節奏偏好）、**剪同款升級為可用自然語言改內容和情節**、專業創作者可把工作流沉澱為 Skill 給他人複用〔媒〕 |
| 口碑 | 讚：模板多、潮流快、卡點準、手機上就能做出「像專業」的成片；智能摳像/補幀對素人夠用〔知〕。抱怨：2025–2026 大量功能鎖進 Pro（1080p/60fps、大部分特效、動態字幕），漲價近一倍、停機一週無說明，Reddit r/CapCut、Trustpilot、Change.org 請願〔媒〕；模板同質化（大家都用同一個） |
| 定價 | 免費＋Standard 約 $9.99/月、Pro 約 $19.99/月、2026 新增 Ultra/AI Ultra（AI 積分＋SVIP 合一）〔三〕〔媒〕 |
| 我們沒規劃但重要 | **模板市集＋作者分潤**（每年約 1.5 億人民幣激勵、按模板被使用/匯出次數計酬）〔媒〕〔官〕；趨勢音樂庫與熱門模板即時連動；動態字幕樣式庫；AI 配音（269 種 TTS 聲音〔三〕） |

來源：
- CapCut Auto Cut 說明 https://www.capcut.com/help/how-to-use-auto-cut ・ https://www.capcut.com/help/auto-cut-in-capcut
- CapCut 2026 趨勢 https://www.capcut.com/help/latest-capcut-editing-trends
- 新華網 剪映 AI 新創作發佈會（2026-09-21）https://www.news.cn/tech/20260921/6742f6c1f32f41d4918105bc686fe907/c.html
- 第三方 2026 AI 套件整理 https://bibigpt.co/en/features/capcut-2026-ai-suite-explained
- 漲價/鎖 Pro：https://piunikaweb.com/2026/01/27/capcut-pro-price-increase-100-dollars-outage/ ・ https://newsweek.com/app-used-millions-nearly-doubles-subscription-price-overnight-11535999 ・ https://eesel.ai/blog/capcut-pricing ・ https://www.change.org/p/capcut-disappointed-us-stop-the-abuse-of-the-pro-model
- 模板作者計畫 https://www.capcut.com/partners/template-creator-us

### 1.2 Descript（Underlord）

| 項目 | 內容 |
|---|---|
| 重疊 | AI 導演/Agent（多步驟指令）、看畫面理解媒體、自動剪口播、Studio Sound、自動字幕、重構圖 |
| 做法/UX | **以逐字稿編輯為核心**＋對話式 Agent Underlord，單一 prompt 執行多步驟剪輯。2026 新增「媒體理解」，Agent 能看畫面而非只讀逐字稿（有評測稱放置準確度 60%→92%〔三〕）；推出 MCP connector 與 API open beta〔三〕。底層用 Claude（自助用戶預設 Sonnet，企業 Opus）〔官〕；官方稱 30%+ 專案用到 Agent，用 Agent 者匯出率較高〔官〕 |
| 口碑 | 讚：口播/Podcast 最強之一、文字剪片直覺。抱怨：Studio Sound 高強度有機器人感、**影格級精度不足**、不適合電影感作品〔三〕；AI 積分與媒體分鐘兩套計量，重度 AI 使用先撞積分上限〔三〕 |
| 定價 | Free（60 媒體分鐘、100 AI 積分一次性）、Hobbyist ~$16–24、Creator ~$24–35、Business ~$50–65/月〔三〕 |
| 值得注意 | Agent 的「可見計畫→執行→可撤銷」與逐字稿作為中介表示（intermediate representation）——與我們「可編輯 plan」理念相近 |

來源：https://www.descript.com/blog/article/underlord-ai-can-watch-videos ・ https://claude.com/es/customers/descript ・ https://kompozy.io/reviews/descript ・ https://www.tella.com/blog/best-agentic-video-editors ・ https://sonix.ai/resources/descript-pricing/

### 1.3 Opus Clip

| 項目 | 內容 |
|---|---|
| 重疊 | 自動重構圖 9:16（ReframeAnything，物件追蹤）、AI B-roll、選段＝選最佳（Virality Score）、品牌模板 |
| 做法/UX | 長片→一鍵產 N 個短片，每個附 0–99 的 Virality Score；ClipAnything 多模態選段；動畫字幕模板（宣稱 97%+ 準確、20+ 語言）；**Brand template**（品牌色、字型、Logo 一次設定、全片套用）；B-roll 可選圖庫或 AI 生成〔官〕 |
| 口碑 | 讚：快、選段不錯。抱怨：**處理不穩、靜默失敗**是最常見抱怨；Virality Score 不準（低分片常贏過高分片）；選段起訖點常太早/太晚、不懂上下文；免費版限制多、訂閱結束專案消失〔三〕 |
| 定價 | 免費（浮水印、3 天過期）、Pro 約 $29/月〔三〕 |
| 教訓 | 「分數」若不可解釋就會失信——我們的盲測 pairwise 應輸出**理由**而非單一分數 |

來源：https://opus.pro/home-site ・ https://www.eesel.ai/blog/opusclip-reviews ・ https://realoficial.com.br/en/blog/opus-clip-honest-review-2026-what-it-does-well-and-where-it-falls-short ・ https://www.g2.com/products/opus-clip/reviews

### 1.4 Captions（公司已更名 Mirage）

| 項目 | 內容 |
|---|---|
| 重疊 | AI 導演（AI Edit 一鍵套風格）、自動 zoom、音效、B-roll、轉場、音樂、對話式編輯 |
| 做法/UX | **選一個「風格」→ AI 自動剪輯**（切場、B-roll、轉場、音樂、zoom、字幕），風格庫 20+ 個具名風格（Prism Pro、Paper II、Vinyl、Neon、Cinematic II…）；2026-02 支援 16:9 與 10 分鐘；2026-05 新增商務向 Evo/Focus/Core 風格〔三〕；chat editor 用自然語言要求 B-roll、zoom、音效〔官〕；AI 唇形同步翻譯、Avatar |
| 口碑 | 讚：口播短片最「爆款感」、手機端體驗佳。抱怨：價格與 iOS 綁定、進階功能在 Max 以上、風格容易看起來一樣 |
| 定價 | Pro ~$9.99、Max ~$24.99（含 AI Edit 風格、chat editor）、Scale ~$69.99/月〔三〕；2026-03 募資 $75M〔三〕 |
| 值得學 | **「風格」是一包參數（字幕樣式＋zoom 節奏＋轉場＋音效＋配樂＋調色）**，使用者只選一個名字 |

來源：https://captions.ai/features/edit-with-ai ・ https://mirage.app/captions/edit-with-ai ・ https://yespress.io/products/captions.md ・ https://www.eesel.ai/blog/captions-ai ・ https://www.preqin.com/data/profile/asset/mirage/551879

### 1.5 Submagic

| 項目 | 內容 |
|---|---|
| 重疊 | 自動 zoom、B-roll、轉場、音效、hook 標題 |
| 做法/UX | 以**動畫字幕**為核心；Auto Zoom 一鍵全片，zoom 樣式有 fast zoom、crash out zoom、crash、smooth zoom in、expo zoom、linear zoom 等；6 種 Magic Zoom 轉場＋6 種 Magic B-Roll 樣式；**B-roll 與 emoji 動畫都自動配音效**；Magic Clips 產 hook 標題、描述、封面〔官〕 |
| 口碑 | 讚：字幕業界最佳之一。抱怨：字幕以外功能淺；Magic Cut 太激進造成跳接；匯出偶失敗〔三〕 |
| 定價 | Starter ~$19、Pro ~$39、Business+API ~$69/人/月，配額嚴格〔三〕 |
| 值得學 | **zoom 的命名詞彙表（crash/expo/linear/smooth）**＝把 easing 曲線產品化；「每個視覺事件配一個音效」 |

來源：https://submagic.co/features/auto-zooms ・ https://submagic.co/features/b-rolls ・ https://www.submagic.co/pl/features/transition-editor ・ https://www.submagic.co/integrations ・ https://costbench.com/software/ai-video-editing-saas/submagic/ ・ https://fluxnote.io/guides/submagic-review-honest-2026

### 1.6 Runway（Aleph 2.0 / Edit Studio）

| 項目 | 內容 |
|---|---|
| 重疊 | 主體/物件編輯、重新打光、風格化（類 LUT 但生成式）、多鏡頭一致套用 |
| 做法/UX | 2026-05-21 推出 Aleph 2.0＋Edit Studio：**先用一張靜態影格預覽/指定要的效果，確定後才生成影片**；一次編輯可套到多個鏡頭；只改指定部分、其餘保持原樣；上限 30 秒、1080p；付費方案限定、API 可用〔官〕 |
| 口碑 | 讚：物件替換/去除在清楚、光線好的素材上很強。抱怨：快速運動、精確整合仍弱；無批次；無免費試用；credit 消耗〔三〕 |
| 定價 | Credit 制、僅付費方案 |
| 值得學 | **「先預覽一格，再算整段」**——對我們昂貴步驟（BiRefNet 全片去背、光流補幀、多版本渲染）極有價值 |

來源：https://runway.com/news/introducing-aleph-2-and-edit-studio ・ https://www.atlabs.ai/blog/runway-aleph-review ・ https://filmora.wondershare.com/video-editor-review/aleph-2-0-review.html

### 1.7 VEED

| 項目 | 內容 |
|---|---|
| 重疊 | 自動字幕、AI 配音/配音翻譯、Avatar、歌詞影片 |
| 做法/UX | 瀏覽器編輯器＋AI 功能堆疊；AI 眼神校正、歌詞影片產生器、一鍵配音〔三〕 |
| 口碑 | 讚：基礎穩、上手快。抱怨：無進階剪輯、網頁慢、多席位貴、好用 AI 功能在付費牆後〔三〕 |
| 定價 | Free（720p、浮水印）、Lite ~$12、Pro ~$24、Business ~$59/月〔三〕 |
| 值得學 | **歌詞影片（lyrics video）**——音樂＋逐字時間軸＝我們已有的節拍/段落分析可直接延伸 |

來源：https://magichour.ai/blog/veed-pricing ・ https://fluxnote.io/guides/veed-io-review-2026 ・ https://aiindigo.com/blog/veed-io-review-2026-the-practical-standard-for-ai-video-editing

### 1.8 invideo AI

| 項目 | 內容 |
|---|---|
| 重疊 | AI 導演（prompt→整支片：腳本、配音、素材、音樂、音效） |
| 做法/UX | Prompt 驅動；1,600 萬支圖庫影片＋生成模型（Sora 2、Veo 3.1、Kling 3.0）混用〔三〕 |
| 口碑 | 讚：真的能一句話產整支。抱怨：**圖庫配對太泛、看起來跟其他 AI 片一樣**；曾出現帶圖庫浮水印的素材；credit 與重生成成本；客服差；Trustpilot 偏負面〔三〕 |
| 教訓 | **「一句話全自動」的失敗模式＝泛用、無個性**。我們的 AI 導演必須以使用者素材為主、有明確 treatment |

來源：https://www.fast.io/resources/invideo-ai-review-2026.md ・ https://www.rfp.wiki/design-multimedia/ai-video-generators/invideo ・ https://uk.trustpilot.com/review/ai.invideo.io?page=4

### 1.9 Adobe Premiere（2026 起改名 Adobe Premiere，去掉 Pro）

| 項目 | 內容 |
|---|---|
| 重疊 | Auto Reframe〔知〕、主體遮罩（Object Mask）、Generative Extend（延長鏡頭）、Media Intelligence（自然語言搜素材）、Remix（音樂自動改長度）〔知/媒〕、Morph Cut〔知〕 |
| 做法/UX | **AI 放在「省工具」而非自動成片**。26.0（2026-01）Object Mask：一鍵選取人/物並追蹤，**本機運算、不上雲**；26.3（2026-06）加 Sharp/Smooth 邊緣模式、更快追蹤、3D 透視追蹤；Firefly Boards 依板上順序自動建序列；26.5（2026-09）Generative Media Tool〔官/媒〕。Generative Extend 用 Firefly 把片段延長最多約 2 秒（含音訊），附 Content Credentials〔媒〕。**Remix**：把音樂標為 Music→輸入目標長度→自動在節拍/樂句處重組，時間軸上標出接點；只能在目標長度 ±5 秒內達成，且不理解歌詞〔三〕 |
| 口碑 | 讚：Object Mask 清楚主體表現好、Generative Extend 實用救急。抱怨：雜訊/低對比素材遮罩失準、26.3 偶選錯物件〔媒/官社群〕；訂閱制、效能 |
| 定價 | Creative Cloud 訂閱、生成式功能耗 Firefly credits |
| 值得學 | **Remix＝音樂自動改長度**——我們有 beat/downbeat/section 分析，可做到「段落感知」的 remix，甚至比 Adobe 更好（處理歌詞、指定保留副歌） |

來源：https://www.provideocoalition.com/new-ai-and-masking-tools-in-premiere-plus-major-upgrade-to-after-e%EF%AC%80ects/ ・ https://digitalproduction.com/2026/01/22/premiere-drops-the-pro-and-picks-up-some-serious-ai/ ・ https://community.adobe.com/announcements-727/what-s-new-in-adobe-premiere-26-3-june-2026-1628369/index1.html ・ https://helpx.adobe.com/premiere-pro/kb/fixed-issues.html ・ https://www.businesswire.com/news/home/20250402472642/en ・ https://www.engadget.com/adobe-premiere-pro-remix-music-re-time-sync-213055147.html ・ https://larryjordan.com/articles/remix-comes-to-adobe-premiere-pro-v22-2/

### 1.10 DaVinci Resolve（20 → 21 → 21.1）

| 項目 | 內容 |
|---|---|
| 重疊 | AI Detect Music Beats（在節拍處放 marker、可吸附）、AI Music Editor（音樂改到指定長度，給最多 4 個選項）、Magic Mask v2（主體遮罩）、IntelliScript（依腳本自動選最佳 take 建時間軸、替代 take 放額外軌）、Speed Warp（AI 光流變速）〔知〕、Smart Reframe〔知〕、AI 調色、21.1 接 Claude/Codex AI 助手＋20 個新 scripting API |
| 做法/UX | 專業 NLE 內建工具；**IntelliScript 把「替代方案」放在其他軌**讓人選〔媒〕；21（2026-06）加 AI CineFocus（後製改焦/散景）、Face Reshaper、IntelliSearch、UltraSharpen、Photo 頁〔媒〕；21.1（2026-09）**整合 AI 助手（Claude、ChatGPT Codex）＋20 個 scripting API**〔媒〕 |
| 口碑 | 讚：免費版強、Studio 一次買斷 $295、升級免費；Speed Warp/Magic Mask 品質業界頂尖〔知/媒〕。抱怨：學習曲線陡、AI 工具多僅限 Studio |
| 值得學 | (1) **音樂改長度給多個候選**；(2) **替代方案並排放在軌道上**＝我們的 variants；(3) Resolve 21.1 開放 scripting API 給 Claude/Codex——**它也在搶「代理驅動剪輯」位置**，我們可考慮輸出 Resolve/FCPXML 時間軸以互通 |

來源：https://www.provideocoalition.com/davinci-resolve-20-released/ ・ https://cined.com/davinci-resolve-20-released-with-handful-of-ai-assisted-features ・ https://petapixel.com/2026/06/03/davinci-resolve-21-officially-released-with-new-photo-editing-ai-tools/ ・ https://www.newsshooter.com/2026/06/02/davinci-resolve-21-final-release/ ・ https://gigazine.net/gsc_news/en/20260909-davinci-resolve-21-1-update ・ https://www.redsharknews.com/davinci-resolve-21.1-new-features-release?hs_amp=true ・ https://www.kunalganglani.com/blog/resolve-studio-21-ai-features

### 1.11 Kapwing

| 項目 | 內容 |
|---|---|
| 重疊 | Smart B-roll（讀逐字稿找關鍵字→建議 B-roll/圖片疊加）、Smart Cut/Auto Cut（去靜音、粗剪）、AI 編輯助手 Kai |
| 口碑 | 讚：瀏覽器協作方便。抱怨：B-roll 需要語音才有用、功能多但淺〔三〕 |
| 值得學 | 「**建議**」而非「強塞」B-roll——給候選讓人/Agent 接受 |

來源：https://kapwing.com/resources/kapwing-direct ・ https://www.kapwing.com/ai/b-roll-generator ・ https://www.kapwing.com/help/kapwing-release-notes-may-2026/

### 1.12 Canva Video

| 項目 | 內容 |
|---|---|
| 重疊 | Beat Sync（分析音樂、自動把剪點對齊節拍，仍可手調）、Magic Video（自動風格化、剪、排序）、去背、AI 配音〔官〕 |
| 口碑 | 讚：設計模板強、品牌一致。抱怨：3 分鐘以下、少圖層才順，10+ 元素介面卡〔三〕 |
| 定價 | 免費～Pro 約 $12.99–15/月〔三〕 |
| 值得學 | **「自動但可微調」**：Beat Sync 算完剪點後仍讓人拖；設計系統（品牌色/字型）貫穿影片 |

來源：https://www.canva.com/video-editor/ai/ ・ https://www.canva.com/pt_pt/ferramentas/beat-sync/ ・ https://bityclips.com/blog/canva-video-review-2026 ・ https://www.creatorstackclub.com/software/canva-video-editor

### 1.13 Pika / Kling / Hailuo（生成式特效）

| 項目 | 內容 |
|---|---|
| 重疊 | 「特效」概念，但為生成式（非 f(frame,t)） |
| 做法 | Pikaffects：一鍵把物體 Squish/Crush/Inflate/Melt/Cake-ify/Tear，2025 底在 TikTok/IG 爆紅〔三〕；Kling Effects（MochiMochi、BoomBoom 等，API 可用）、Kling 3.0 Omni（2026-06）可編輯影片 3–15 秒、4K〔三〕；Hailuo 一鍵模板（Morph、StyleSwitch、PetPal…）〔三〕 |
| 口碑 | 讚：爆款、好玩。抱怨：**爆款特效是「格式」不是工具，壽命很短**〔三〕；商用需付費、時間短 |
| 對我們 | 不必追；但可把這些當「可選的外部運動來源」（skill 已以 Grok 為預設運動來源），重點是**讓我們的節拍/卡點框架能把生成片段當素材嵌入** |

來源：https://dev.to/raxxostudios/viral-ai-video-effects-in-2026-how-they-are-made-3lc2 ・ https://piapi.ai/fr/blogs/kling-api-vs-pika-api ・ https://www.atlascloud.ai/blog/guides/kling-3-0-omni-upgrade ・ https://aitoolsatlas.ai/tools/hailuo-ai ・ https://www.tomsguide.com/ai/ai-image-video/pika-labs-drops-new-ai-video-effects-for-halloween-including-popping-eyes-and-levitation

### 1.14 其他中國 App（快影、必剪、醒圖）

| App | 內容 |
|---|---|
| 快影（快手） | AI 一鍵成片、模板庫（聲稱 10 萬+）、自動配樂與轉場〔三〕；與剪映同屬「模板＋卡點」路線 |
| 必剪（B 站） | 一鍵加字幕、大量模板、AI 摳圖/擦除/寫真、文字生成影片（配音＋畫面）、與 B 站生態整合〔三〕 |
| 醒圖 | 字節旗下修圖 App，模板與剪映互通〔知〕；重點在「圖片模板→動態化」 |

來源：https://sj.qq.com/topic/200082788 ・ https://www.tixiaolu.com/v2/posts/v2-a0e4aaf3.html （皆為低可信度，僅作方向）

---

## 2. 能力對照表（我們規劃 vs 競品）

| 我們的能力 | 剪映/CapCut | Captions | Submagic | Opus | Descript | Premiere | Resolve | Canva | Runway |
|---|---|---|---|---|---|---|---|---|---|
| 程式化特效/轉場 f(frame,t) | 庫（黑盒） | 風格內建 | zoom/轉場樣式 | – | 少 | 外掛/AE | Fusion（可程式） | 庫 | 生成式 |
| 節拍/重拍/段落分析 | 自動踩點 | 有（隱含） | – | – | – | Remix 內部 | Detect Beats | Beat Sync | – |
| 主體去背 | 智能摳像 | – | – | 追蹤 | – | Object Mask | Magic Mask | 去背 | Aleph |
| 定格摳像卡點 | 模板常見 | – | – | – | – | 手動 | 手動 | – | – |
| 參考影片逆向成計畫 | 剪映 Hub（新） | – | – | – | – | – | – | – | 參考影格 |
| 模板轉移 | 剪同款 | 風格 | 樣式 | 品牌模板 | 模板 | MOGRT | – | 模板 | – |
| 程序化音效 | 音效庫 | 有 | 自動配 | – | – | – | – | – | – |
| LUT | 濾鏡 | 風格內 | – | – | – | Lumetri | 頂級 | 濾鏡 | 生成式 |
| 變速＋光流補幀 | 曲線變速＋智能補幀 | – | – | – | – | Optical Flow | Speed Warp | – | – |
| 2.5D 視差 | 3D 照片特效〔知〕 | – | – | – | – | 手動/AE | Fusion | – | – |
| 自動 9:16 重構圖 | 有 | 有 | 有 | ReframeAnything | 有 | Auto Reframe | Smart Reframe | Magic Resize | – |
| AI 導演＋多版本盲測選優 | 小映（單版） | AI Edit（單版） | – | Virality 分數 | Underlord | – | IntelliScript 替代 take | Magic Video | 先預覽 |

**觀察**：沒有任何競品做「多版本渲染＋盲測挑最好」；最接近的是 Opus 的分數（被批評不準）與 Resolve 把替代 take 放在別軌。這是我們的明確差異點。

---

## 3. 影響最大的 10 個教訓（依「讓短影音看起來專業」的影響排序）

1. **字幕就是設計主角（逐字動畫字幕）**——Captions、Submagic、Opus、CapCut 全部把「逐字高亮/彈跳/關鍵字變色＋emoji」當核心賣點；口播類短片的「專業感」八成來自字幕。我們目前規劃沒有明列，**應補上 word-level 字幕動畫系統**（逐字時間碼＋樣式預設＋關鍵字強調＋安全區）。
2. **剪點與動作的「打點階層」**——CapCut Auto Cut 可調卡點密度、Canva Beat Sync 算完仍可微調、Resolve 放 beat marker 可吸附。專業感來自「重拍切鏡、次拍做 zoom/閃、段落換場換風格」的層級，而不是每拍都切。我們的 beat/downbeat/section 應輸出**分層事件軌**（section > downbeat > beat > onset）並讓效果綁定層級。
3. **音樂自動改長度（段落感知 remix）**——Premiere Remix（±5 秒、不懂歌詞）、Resolve AI Music Editor（給 4 個候選）。短影音常需 15/30/60 秒精準長度；我們已有段落分析，可做「保留副歌、在小節邊界接、淡入淡出」的 remix，並**給多個候選**。
4. **每個視覺事件配音效（whoosh/hit/riser/pop）**——Submagic B-roll、emoji、轉場都自動配音效；Captions chat 可要求音效。我們的程序化 SFX 要**與轉場/zoom/定格自動綁定**，這是業餘與專業差距最大的地方之一。
5. **「風格」＝一包少而精的參數預設**——Captions 20+ 具名風格、Submagic 6+6 樣式、Opus 品牌模板。使用者/Agent 選一個名字就套整組（字幕樣式＋zoom 曲線＋轉場族＋SFX 族＋LUT＋配速）。我們應定義 **style pack schema**，而不是讓 Agent 每次從 100 個效果自由組合（容易雜亂）。
6. **自動 zoom/punch-in 的命名 easing 詞彙**——Submagic 的 crash / crash out / expo / linear / smooth zoom。把 easing 產品化成名詞，Agent 才能可靠調用；也是口播片「動感」主要來源（尤其搭配說話重音或節拍）。
7. **主體追蹤重構圖 9:16（含說話者切換）**——Opus ReframeAnything、Premiere Auto Reframe、Resolve Smart Reframe。重構圖錯一次（切到頭）就毀掉專業感；需要平滑的追蹤路徑（死區＋加速度限制）與多人時的說話者優先。
8. **先預覽一格/一段，再算全片**——Runway Aleph 2.0 先用靜態影格預覽；對我們昂貴的 BiRefNet、光流補幀、多版本渲染應有 **proxy/keyframe preview 模式**，讓 AI 導演在低成本預覽上做盲測，再對勝出者全解析度渲染。
9. **模板＝「槽位＋時間軸骨架」且可用自然語言改**——剪映剪同款 2026 升級成可用自然語言改內容和情節、可替換素材；剪映 Hub 可從「一個參考影片」出發。這正對應我們的「參考影片逆向→可編輯 plan→模板轉移」，建議 plan 的 schema 明確區分 **slot（素材槽，含時長/構圖/主體需求）、timing（綁定 beat 層級）、look（style pack）**，讓轉移時只換 slot。
10. **Agent 要「看得見畫面」並輸出可解釋選擇**——Descript 2026 讓 Underlord 看畫面後放置準確度大幅提升；Opus 的不可解釋 Virality Score 遭批評。我們的 AI 導演選鏡/選版本時，應基於視覺分析（我們已有 qa_media 量測），pairwise 評審輸出**理由**與量測證據，而非單一分數。

---

## 4. 可吸收的做法（概念/UX/結構層面；不抄程式碼或專有素材）— 依影響排序 Top 10

> 均為「做法」的借鏡，以我們自己的實作與自製/開源素材完成。

1. **逐字動畫字幕樣式系統（借鏡 Submagic/Captions/CapCut 動態字幕）**
   具體結構：`caption_style = {font, weight, stroke, shadow, case, max_words_per_line, position(safe-area), active_word: {color, scale, bg_pill}, entry_anim: pop|slide|typewriter, keyword_emphasis: {color, emoji?}}`；資料來源＝ASR 逐字時間碼（離線 whisper 類）。預設 4–6 種即可（粗白黑描、黃色高亮、膠囊底、打字機、極簡小字、卡拉 OK）。
2. **Style Pack（借鏡 Captions AI Edit 風格、Opus Brand Template）**
   一個 YAML/JSON 包含：字幕樣式、zoom 曲線族、轉場族、SFX 族、LUT、配速（平均鏡頭長度、每段 cut 密度）、字型/品牌色。AI 導演只挑 pack＋微調少數參數；變體＝同素材 × 不同 pack。
3. **分層卡點 + 可調密度（借鏡 CapCut Auto Cut 密度、Resolve beat marker 吸附、Canva 可微調）**
   `cut_density: every_beat | every_downbeat | every_2_bars | section_only`，效果綁定 `on: downbeat|beat|onset|section_start`。輸出 marker 檔讓人/Agent 微調後重渲。
4. **轉場/zoom/定格自動配 SFX（借鏡 Submagic 自動音效）**
   規則表：whip/slide→whoosh（長度＝轉場時長、聲像跟方向）、crash zoom→impact＋低頻 boom、定格→camera shutter/riser 收尾、文字彈出→pop；SFX 用程序化合成，並做 ducking 與 -X LUFS 控制。
5. **命名 zoom/easing 詞彙表（借鏡 Submagic 的 crash/expo/linear/smooth）**
   `punch_in(crash)`、`punch_out(crash_out)`、`ken_burns(smooth)`、`expo_in`、`linear_drift`、`shake_on_hit`；每個附預設持續時間與與節拍對齊方式，Agent 用名字叫用。
6. **音樂改長度 + 多候選（借鏡 Premiere Remix、Resolve AI Music Editor 給 4 選項）**
   在小節/段落邊界切接、交叉淡化、保留指定段（副歌/drop），輸出 2–4 個候選與接點清單，並把接點標記給剪輯計畫使用。可延伸「歌詞影片」（借鏡 VEED lyrics video）。
7. **預覽優先、再全渲（借鏡 Runway Aleph 2.0 靜態影格預覽）**
   AI 導演流程：低解析/關鍵影格 contact sheet → 盲測 pairwise → 勝者全解析度渲染；BiRefNet/光流只對勝者全片執行。
8. **模板＝槽位骨架、可自然語言改（借鏡剪映剪同款 2026、剪映 Hub 從參考影片出發）**
   逆向參考片時輸出 `slots[]`（時長、鏡位/景別、主體需求、運動方向）＋`timing`（綁 beat 層級）＋`look`（推測 style pack/LUT）。模板轉移＝新素材自動配槽（依景別/主體/運動相似度），並允許「把第 3 段換成產品特寫」這類自然語言修改。
9. **替代方案並排保留（借鏡 Resolve IntelliScript 把替代 take 放額外軌）**
   每個決策點保留 runner-up（次佳鏡頭/效果），寫入 plan 的 `alternates`，使用者一句話就能換，不必整片重算。
10. **Hook 與包裝產出（借鏡 Submagic Magic Clips、Opus）**
    除了影片，同時產 hook 文字（開頭 1–2 秒大字）、封面影格（自動挑最清楚、表情最好、主體居中的一格）、標題/描述草稿。這些是「看起來像專業創作者」的最後一哩，成本極低。

---

## 5. 我們不該抄的（及原因）

- **鎖功能的付費牆/積分雙計量**（CapCut 2026 漲價與鎖 1080p 引發大規模反彈；Descript 積分與分鐘雙計量讓人困惑）——我們是開源本機工具，信任就是護城河。
- **不可解釋的「爆紅分數」**（Opus Virality Score 被證實不可靠）——改用 pairwise＋理由＋量測證據。
- **純 prompt→泛用圖庫成片**（invideo：成片泛、跟別人一樣、還出現圖庫浮水印）——AI 導演以使用者素材為主，生成/圖庫只補洞。
- **追逐生成式爆款特效**（Pikaffects 類格式壽命短、需雲端與付費）——提供外部來源接口即可，不內建。
- **模板市集／作者分潤經濟**——需要平台、審核、版權處理，與 skill 定位不符；但「模板/ style pack 檔案格式可分享」值得做（Git 即市集）。
- **雲端上傳素材**——Premiere 2026 Object Mask 都強調本機運算保護隱私，我們離線優先是賣點，不要為了某模型破壞。
- **過度激進的自動剪（Submagic Magic Cut 造成跳接）、無聲失敗（Opus 最大抱怨）**——每一步要有量測驗證（我們已有 qa_media）與可讀錯誤訊息。
- **風格過多造成選擇困難與雜亂**——Captions/Submagic 都是「少而精」的具名樣式；不要把 100 個特效直接丟給 Agent 自由組合。
- **AI 唇形同步/Avatar/配音翻譯**——與我們的剪輯核心距離遠、倫理風險高（深偽），暫不做；如需配音，可接外部 TTS。

---

## 6. 補充：值得追蹤的動向

- 剪映助手「**支援自訂 Skills**」、Resolve 21.1「**接 Claude/Codex＋scripting API**」、Descript「**MCP connector＋API**」：大廠都在開放給外部 Agent。我們可考慮輸出 **FCPXML / OTIO（OpenTimelineIO）** 讓計畫能匯入 Resolve/Premiere 精修，形成「我們做第一版、專業 NLE 收尾」的互補，而非正面競爭。
- 所有第三方評測（〔三〕）的數字與價格常互相矛盾，本文件僅用於方向判斷。
