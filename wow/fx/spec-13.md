# spec-13 — 接上 GPT-Image-2.6（2026-11-06）

來源：使用者 2026-11-06 `/wow gpt images 2.6, 有發布了 可以用` ＋「搜尋研究有哪些新功能 可以用上的」。
OpenAI 2026-11-04 發布 ChatGPT Images 2.6／GPT-Image-2.6（API：Flare 快、Sunburst 細節與跨編輯一致；比 2.5 快 50%）；
ChatGPT 與 **Codex 全方案可用**（本機 Codex CLI 0.166 的 `image_generation` 功能為 stable、已啟用 → 可走使用者既有訂閱，不必另付 API）。
trunk-based：每個 S 一個小切片，測試全綠當天以 experimental 合回 main。

## 新功能 → 我們怎麼用（調查來源見文末）
| 2.6 新功能 | 用在 video-gif-studio |
|---|---|
| **原生 GIF 輸出**（2–64 格、每格 20–2000 ms、尺寸 16 的倍數、可循環；可由靜態圖起始；單一簡單動作＋固定鏡頭） | 新的「短循環動作」來源：角色待機、吉祥物、貼圖、產品轉動、反應圖。進我們既有管線（摳像、alpha QA、循環接縫檢查、sprite 匯出）。與 Grok 影片做技術軸比較，選適合的路線 |
| **參考圖最多 16 張＋跨編輯一致（Sunburst）** | 角色／產品身分鎖定：建立參考庫 → 產生分鏡關鍵格、影片生成的首末格、coverage（全景／中景／特寫）時身分一致 |
| **透明背景** | 直接產 RGBA 貼紙、疊層、卡片素材，省掉摳像，品質更乾淨 |
| **Markup 局部修改**（原圖＋同尺寸透明註記層） | 接 spec-11 修改語法／看圖回饋：「這裡換掉」「第二鏡的杯子改成拿鐵」→ 自動畫註記層精準改局部，其他不動 |
| **SVG 輸出**（可編輯向量、透明） | 片名卡、logo、字幕裝飾、圖示：向量進我們的 fx（描邊生長、遮罩揭露、縮放不糊），任何解析度都清晰 |
| **一次最多 8 張** | brief 的分岔與導演多版本：同一鏡一次出 2–8 個方向給使用者挑（動態預覽） |
| **11 種長寬比、到 4K、`complexity`／品質檔位** | 9:16 直式關鍵格、21:9 電影感；草稿用 Flare＋low，成品用 Sunburst＋high |
| **C2PA＋SynthID** | 交付 manifest 記錄 AI 來源；spec-12 S-144 的「AI／實拍判定」可讀 C2PA |

## 規格
- S-150 **影像路由**：`image_route`：`codex`（預設，走使用者 Codex 訂閱的 image_generation）／`api`（gpt-image-2.6-flare／sunburst，需 API key，**每次花費前先問使用者**）／既有路線（Grok 等）。記錄實際模型、參數、張數、耗時；同一請求有快取不重付。
- S-151 **分鏡關鍵格與動態分鏡**：spec-7 的分鏡／動態分鏡用 2.6 產每鏡關鍵格（取代剪影卡），依景別、構圖、色彩段、美學；草稿 Flare-low，可升 Sunburst。
- S-152 **身分參考庫**：角色／產品／場景各 ≤16 張參考，所有關鍵格、首末格、coverage 都帶參考；身分一致度以量測（人臉／物件特徵相似度）＋看片驗證。
- S-153 **原生 GIF 動作來源**：GIF → 影格 → 既有清理／摳像／循環接縫／sprite 匯出；與 Grok 在相同題目上做技術軸比較並記錄（速度、接縫、身分、動作合理性）。
- S-154 **透明資產**：透明背景直接產貼紙／疊層／卡片，alpha 品質用既有 QA 驗。
- S-155 **Markup 局部修改**：修改語法與看圖回饋自動生成註記層，呼叫 edits；未註記區域像素差 ≈ 0 才算成功。
- S-156 **SVG 向量素材**：片名卡、logo、字幕裝飾 → 光柵化或動畫化（描邊生長、遮罩揭露）進 fx；靜態 SVG 安全（無腳本、無外部資源）檢查。
- S-157 **多版本挑選**：brief 分岔／導演版本一次產 2–8 個候選關鍵格，動態預覽頁讓使用者挑（兩軸：好看由使用者）。
- S-158 **用量與來源紀錄**：每次生成寫入 manifest（路線、模型、品質、張數、C2PA 是否存在）；API 路線預估費用並先問；訂閱路線記錄張數。

## 驚豔時刻
打一句話，導演就用 2.6 畫出每一鏡的關鍵格（角色一致、9:16、有你的品味），你挑一個方向後，它把關鍵格變成會動的片；說「第二鏡杯子換成拿鐵」，只有那個杯子被改掉。

## 來源（2026-11-06 調查）
- OpenAI Developers 發布：https://x.com/OpenAIDevs/status/2118124753340756055
- OpenAI 發布：https://x.com/OpenAI/status/2118124944928432327
- eesel 規格整理（GIF 參數、markup、SVG、Flare／Sunburst、價格）：https://www.eesel.ai/blog/chatgpt-images-2-6
- TestingCatalog：https://www.testingcatalog.com/openai-launches-images-2-6-with-gifs-and-image-reference/
- OpenArt 規格（長寬比、4K、16 張參考、透明背景、C2PA）：https://openart.ai/blog/gpt-image-2-6-overview/
- 注意：部分細節來自第三方整理，實作前以 OpenAI 官方文件與實測為準。

## 能力實測（2026-11-06，Codex 訂閱路線，codex-cli 0.166，image_generation 工具）
| 功能 | 訂閱路線 | 證據／做法 |
|---|---|---|
| 一般出圖（含 9:16、清楚的文字） | ✅ | cafe-keyframe 941×1672，生成 19.6 s；「MENU」正確 |
| 透明背景 | ✅ 原生（`transparent_background`） | probe-alpha：RGBA、48.6% 全透明；外框周圍有零星半透明白點 → 仍需我們的 alpha 清理／QA |
| 參考圖（身分／場景保留） | ✅（`referenced_image_paths`） | probe-edit：只換杯子、構圖光線保留；但整張重生，杯子以外平均差 8.5/255（非像素一致） |
| 局部修改（markup／mask） | ❌ 無參數 | 做法：參考圖重生＋我們用遮罩把改動區合成回原圖（區外像素一致）；精準 markup 需 API |
| 原生 GIF | ❌ 只回 PNG | 做法：關鍵格＋我們的補格／Grok 做動作；原生 GIF 需 API（付費，需先問） |
| SVG | ❌ 無格式選項 | 需 API（付費，需先問）；或關鍵格向量化（potrace 類）作替代 |
| 回報模型名稱 | ❌ 不回報 | manifest 記「codex-image_generation（模型未回報）」 |
| 模型選擇 Flare／Sunburst、品質、complexity | ❌ | 需 API |
→ 預設全走訂閱；API 只在使用者同意後用於：原生 GIF、SVG、精準 markup、指定 Flare／Sunburst。
