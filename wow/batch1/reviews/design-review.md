# W4 獨立設計審查（Batch 1）

審查者：Claude（與建造者 Codex 不同廠商）。未修改任何產品檔，只寫本檔。

## 審查範圍與方法

- 讀 `README.md`、`README.zh-TW.md` 前 80 行。
- 用 Read 看四張審查圖：`after-preview-checkerboard.png`、`after-frame0-transparent.png`、`after-c1-island-kept.png`、`after-contact.png`（都在 `money-radar-team/2026-11-22/vgs-review/`）。
- 另外量了 README 首屏實際引用的 `examples/chibi-running-dash/hero.png`（見「最重要發現」）。
- **沒有做的事**：沒有在 390／1440 寬度的真實 GitHub 渲染下看過，也沒有開 GitHub 深色主題。下面關於版面的判斷來自 Markdown 結構與圖片尺寸，是推論，不是截圖證據。`spec.md` 沒有逐條列出 W4 的 7–12 項，我依任務說明的六個面向審：視覺層級、字體／尺寸對比、狀態誠實、空／錯誤／成功狀態、淺深色可讀、專業感。

## 最重要發現（會直接毀掉第一印象）

**README 首屏的 hero 圖是洋紅底的原始畫面，不是透明成果。**

- `README.md:21`、`README.zh-TW.md:21` 引用 `examples/chibi-running-dash/hero.png`。
- 我讀了該檔：320×320 RGB（沒有 alpha），整張是 (252,0,251) 洋紅底，左上還有一塊略深的矩形邊（約從 40,40 起），角色在底下。
- 審查用的 `after-frame0-transparent.png` 是**另一張**：中灰底、乾淨角色、沒有洋紅。兩者不是同一個檔案。所以「審查圖看起來沒問題」不能代表 README 看到的圖沒問題。
- 圖說是「Chibi dash preview」，沒有說明這是輸入來源。整份 README 第一句話承諾「透明 GIF」，第一張圖卻是整片洋紅底。讀者會合理判斷成「去背失敗」，與 S-2 要求的「不得讓洋紅底通過」直接衝突。
- 這個檔案目前是 untracked（`git status` 顯示 `?? hero.png`），所以尚未發佈，還來得及處理。

## 逐項評分

評分：好／可接受／不及格。

### 1. 視覺層級：可接受（有一個斷點）

- 好的地方：標題 → 一行定位 → Quick start → 圖 → How it works → 價格表，順序合理。「獨立 CLI，也是 skill」放在第一句，S-5 要求的定位有到位。
- 斷點：首屏圖（`README.md:21`）只有 320 px、靜態、靠左，旁邊沒有文字承接；真正會動、能展示價值的 `hero.gif` 被擺到第 63 行之後的 Examples。第一屏賣的是最弱的素材。
- Quick start 底下的「Human entry」那一條（`README.md:17`）塞了四件事：指令、輸出目錄規則、自動色鍵、`--no-key` 失敗語意，一個 bullet 約 60 字，沒有視覺重點。真正的主指令已在上面的 code block 出現過一次，這裡重複。

### 2. 字體／尺寸對比：可接受

- README 靠 GitHub 預設排版，沒有自訂字級，所以談不上設計失誤，但也沒有任何放大的主指令或標語。唯一的強調是粗體「Recheck before listing.」，結果把價格免責聲明做得比主指令還醒目。
- 價格表第三列「Headline 1.5 $0.080/sec」讀起來像打錯字（「1.5」是模型版本，不是價格），字體上沒有任何區隔。建議用 code 樣式或改寫成「Grok 1.5：$0.080/秒」。
- 圖片內文字：`after-preview-checkerboard.png` 與 `after-contact.png` 的標籤（「light checkerboard」、「output frame 41」）只有約 10 px，且「lightcheckerboard」「darkcheckerboard」的字距把空格吃掉了。contact sheet 的標籤是灰字壓在 #ddd 條上，對比偏低。這些是工程用圖，可以接受，但若要拿去當展示圖就不夠。

### 3. 狀態誠實：不及格（因為上面的 hero），其餘尚可

- 好的地方：「Full-speed loop review remains pending」（`README.md:75`）誠實標出未完成；價格寫了核對日期；「PASS／WARN／FAIL」與「Reports cannot certify natural motion」把量測的邊界講清楚。這些是同類 README 少見的做法，要保留。
- 不及格處：
  1. 洋紅底 hero 沒有標示是來源（見上）。
  2. `after-frame0-transparent.png` 是把透明物件壓在不透明中灰底上，檔名叫 transparent、圖上沒有任何字說明，單看這張圖無法分辨「透明」與「被填成灰色」。若要當證據，必須放在棋盤格上，或加註「flattened on #xxxxxx」。
  3. `hero.gif` 的 frame 0 實測有約 94% 像素是透明，這是好的；但 README 沒告訴讀者「這張 GIF 是透明的，你在 GitHub 看到的底色是頁面底色」。
- `after-c1-island-kept.png`（白色方塊＋洋紅矩形＋底下一條白線）是合成測試件。不能出現在任何對外頁面，否則會被讀成「洋紅底留下來了」。內部證據用途沒問題。

### 4. 空／錯誤／成功狀態：不及格（缺席）

- 兩份 README 前 80 行完全沒有展示 CLI 的成功摘要、錯誤訊息或 QA 的 PASS／WARN／FAIL 實際長相。S-1 要求的「人話摘要」（尺寸、幀數、時長、MB、是否去背、QA 等級）與 S-4 的人話錯誤是這個版本的賣點，卻沒有一處讓讀者看到。
- 影響：讀者不知道執行後會看到什麼、成功長什麼樣。這對 CLI 工具等於沒有截圖。
- 這是「新手第一次執行後，怎麼知道自己成功了」的缺口，建議放一段 5–8 行的真實輸出（不要手寫，從實際執行複製）。
- 圖片層面：contact sheet 與 checkerboard 圖都是成功狀態，沒有任何失敗案例圖（例如 S-2 的「背景未去除」FAIL 圖）。可以後補。

### 5. 淺色／深色可讀：可接受（圖本身好，呈現方式有限制）

- `after-preview-checkerboard.png`：淺棋盤與深棋盤都能看到角色，沒有洋紅底板。淺棋盤是白／淺灰、深棋盤是 #333／#444 左右，對比溫和，不搶主體，這個選擇是對的。
- 殘留問題（量得到、看得到）：
  - 第二格（衝刺幀）的洋紅色速度線、左下的洋紅虛線圓、劍周圍的洋紅描邊，在兩種底色上都很明顯。我無法只靠圖判斷這是刻意的特效色，還是色鍵殘留的邊緣溢色。如果是特效，建議在說明裡講；如果是溢色，這就是 W6 的缺陷，不只是設計問題。
  - 深色棋盤上，角色的黑色絲襪與深色外輪廓與背景接近，腳部辨識度下降（frame 0 與 frame 3 最明顯）。
- `after-contact.png`：每個 cell 只在**一種**底色上出現（第 1、3 欄淺色，第 2、4 欄深色）。這樣讀者無法在同一幀上比較淺深，且淺深交替會干擾逐格讀動作。建議改成每幀同時顯示兩種底，或至少改成列交替。
- `after-contact.png` 用的是純色底（#eee／#181818），不是棋盤格。純色底可以證明「不是洋紅」，但無法證明「是透明」。已有 checkerboard 圖補這點，所以可接受。
- 角色只佔每個 240 px cell 約 40% 高度，像素風細節在縮圖下糊掉；frame 16、25、33、41 的粉紅塵土在淺底上最明顯，同樣分不出是特效還是殘留。
- README 本身：沒有 `<picture>` 或深色主題圖，GitHub 深色模式下首屏圖（若換成透明版）才能真正驗證透明；目前洋紅版在深淺兩個主題都一樣突兀。

### 6. 專業感而非範本感：可接受，偏工程文件

- 加分：badge 只有兩個（CI、Release）且用 `·` 乾淨連接；Mermaid 圖簡單、標籤是人話；中英版結構逐行對齊；價格表有日期與免責。整體沒有 emoji 堆疊與「Features ✨」式範本語氣。
- 減分：
  - 一個主指令在「Quick start」、「Human entry」、安裝說明裡出現三次。
  - Quick start 的 code block 裡有一行註解「From the installed skill directory, with its venv Python:」，沒有說 venv Python 的實際路徑，是複製不能直接貼的指令，而它是首屏唯一的指令。
  - 首屏沒有一個「看了就想試」的畫面（見最重要發現）。
  - 價格表與安裝器細節（`--skills-dir`、`CODEX_HOME` 的判斷順序）擠在 How it works 之後、QA 之前，對第一次來的人是雜訊；這段更適合放進獨立的 install 文件。

## 繁中版（README.zh-TW.md）

- 結構與英文逐行對齊，沒有漏段。用詞自然（「平坦棚景」「色鍵」「交付」）。
- `README.zh-TW.md:43`「標題價 1.5 為 $0.080／秒」與英文一樣有歧義，且中文裡「標題價」更像「標題價格」的直譯，不好懂。
- hero 圖片 alt 文字已翻成「Q 版前衝預覽」，但與英文版一樣指向洋紅底圖，同一個問題。

## 前 5 項設計修正

| # | 等級 | 項目 | 理由與證據 |
|---|---|---|---|
| 1 | **must-fix** | 首屏 hero 不得是洋紅底。換成透明版放在棋盤格或淺深兩底上；若要保留來源圖，改圖說為「Source frame (magenta studio background)」並放在透明結果旁邊做前後對照。 | `examples/chibi-running-dash/hero.png` 實測是 RGB 洋紅底，整份文件第一張圖與「transparent GIF」承諾矛盾。 |
| 2 | **must-fix** | 把會動的透明 `hero.gif` 提到首屏，並加一句說明：GitHub 上看到的底色是頁面底色，這張是透明的。 | `hero.gif` frame 0 約 94% 像素透明，726 KB，符合 ≤ 3 MB；目前放在 Examples 之後。 |
| 3 | **must-fix**（對外前） | 補一段真實的 `vgs make` 成功輸出（與一個失敗例，如輸出目錄非空），不要手寫。 | 前 80 行沒有任何成功／錯誤狀態可見；S-1、S-4 的賣點讀者看不到。 |
| 4 | later | 釐清速度線／塵土的洋紅色是特效還是溢色；若是特效，在證據圖加註；若是溢色，轉給 W6 處理。另外 contact sheet 改成每幀淺深兩底並排，標籤放大到至少 12 px 並修正字距。 | 衝刺幀的洋紅描邊在淺深兩底都明顯；contact 每幀只在一種底色上出現。 |
| 5 | later | 瘦身 Quick start：刪掉重複的 Human entry bullet，把 venv Python 的實際路徑寫在 code block 內；安裝器判斷順序與價格表移到獨立文件；「Headline 1.5」改寫避免歧義（中英同步）。 | 主指令重複三次；code block 含不能直接貼的註解；價格表第三列易誤讀。 |

## 結論

- 文字結構與誠實度整體優於同類專案：定位清楚、價格有日期、未完成處有標示。
- 但第一印象會被首屏 hero 毀掉：洋紅底圖放在「透明 GIF」承諾旁邊。這是 must-fix 第 1 項，修完前不建議對外發佈。
- 第 2、3 項同樣建議在對外前處理；第 4、5 項可排到後續。
- 以上以我實際讀到的檔案與像素量測為準；390／1440 真實渲染與深色主題我沒有看過，需要之後補截圖才能下最終判斷。
