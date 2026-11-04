# spec-6 — 讓 AI 導演「用得好」的效果層（2026-11-05）

來源：使用者 2026-11-05 `/wow 可以讓AI導演影片用的效果, 看還有沒有更好的做法?找到合適最好的做法做`。
路線位置：P2（效果庫擴充）之後、P3（導演）之前；trunk-based，每個 S 一個切片，完成即 commit＋push。

## 第一性原則
導演不是用「濾鏡」思考，而是用**意圖**：「這裡要一記重擊」「揭露主角」「呼吸一下」「蓄力」「爆點」「收尾」。
現在的效果對 agent 只是函數名＋參數；agent 不知道它傳達什麼、多強算剛好、跟什麼內容配、會不會看不見或太刺眼、算繪要多久。
審查三抓到的問題（light_leak 看不見、radial_blur 毀畫面、每拍都閃）正是「效果沒有讓導演能判斷的資訊」造成的。
所以更好的做法不是再加效果，而是讓每個效果**可被理解、可被校準、可被組合、可被驗證**。

## 調查依據（research/ 三份報告）
- 競品：Submagic 把運鏡命名（crash／expo／smooth），agent 才能穩定叫用；Captions／Opus Clip 以「風格」打包整組效果；
  CapCut 分層卡點（剪點在重拍、強調在拍點、段落換風格）；Submagic 音效跟著每個視覺事件。
- 懷疑論：每拍都閃是業餘感；效果要有密度上限；WCAG 閃爍規則（每秒 ≤ 3 次大面積閃）。
- 開源：鏡頭卡分「技術／美感」兩欄；可量測的規則才進 lint。

## 規格
- S-70 **效果卡（registry 擴充）**：每個效果／轉場除參數外，宣告機器可讀的導演資訊：
  `intent`（hit／reveal／breathe／build／drop／transition-match／transition-energy／texture／title…）、
  `energy`（0–1，觀感強度等級）、`needs`（subject、motion、alpha、text）、`good_for`／`avoid_for`（內容與段落）、
  `duration_ms` 建議範圍、`pairs_with_sfx`、`conflicts`、`cost_ms_per_frame@720p`（實測）、`gate`（品質閘門分數與日期）、
  `preview`（預設參數的 2 秒小片＋縮圖路徑）。`--list --json` 輸出完整卡；`--cards` 產一頁 HTML 目錄（每張卡一個會動的預覽）。
- S-71 **觀感強度校準**：同一個 `amount`，不同效果的「看起來多強」要可比。對標準素材量測每個效果的觀感變化
  （逐格亮度變化、結構差異 SSIM、位移量、閃爍面積），把 `amount` 映射成 `perceived`（0–1）；導演用 `perceived` 下指令。
  校準表入庫，可重跑；新效果加入時自動校準。
- S-72 **意圖配方（recipe）**：具名的多效果組合＋時間形狀＋音效，例：`impact`（zoom_punch＋shake＋flash＋hit）、
  `reveal_subject`（vignette 收→cutout_card＋halation）、`breathe`（slow zoom＋grade 微暖）、`build`（逐拍增強的 shake＋riser）、
  `drop`（flash_cut＋radial_blur＋重 hit）、`title_pop`（text＋pop）、`freeze_card`（定格摳像卡點整套）。
  配方是 JSON（可讀、可改、可放使用者庫），只能引用 stable 效果；配方本身也過品質閘門。首批 12–16 個。
- S-73 **可見度與刺眼度自動檢查**：算繪後量每個事件在畫面上的實際變化：低於可感門檻→「看不見」警告；
  超過上限（大面積亮度劇變 > WCAG 每秒 3 次、整格破壞性模糊等）→「刺眼／毀畫面」錯誤；寫進 manifest 與 qa 報告。
- S-74 **效果預算**：依段落能量曲線（S-29）給每段 `perceived` 總量上限與事件密度上限；fx_lint 檢查超預算與「每拍都閃」。
- S-75 **關鍵時刻候選**：對指定的關鍵事件（例 drop、開場鉤子）用 proxy 產 2–3 個配方候選小片並排（含縮圖與量測），
  導演或使用者選一個；選擇與理由寫進分鏡表。
- S-76 **導演查詢介面**：`fx_query --intent hit --needs subject --max-cost 30 --section drop` 回傳排序後的候選效果／配方
  （依意圖符合度、閘門分數、成本、與前後事件的多樣性），附理由；agent 用它選，而不是背清單。
- S-77 測試：卡片欄位完整性（每個 stable 項都有卡）、校準可重現（±5%）、配方只引用 stable、可見度檢查對正反例
  （light_leak 舊預設判「看不見」、radial_blur 舊預設判「毀畫面」）、預算 lint、查詢排序穩定。

## 驚豔時刻與未抵達的樣子
- 驚豔：導演只說「drop 要重、開場要勾人、中段呼吸」，系統就選出合適配方、強度剛好、音效對上、沒有一個看不見或刺眼的事件，
  並附一頁會動的效果目錄讓人一眼看懂有什麼可用。
- 未抵達：卡片欄位是空話（intent 全寫 hit）；perceived 校準與肉眼不符；配方只是效果清單沒有時間形狀；
  檢查放過看不見的效果；查詢永遠回同幾個效果（沒有多樣性）。

## 不做
學習式（ML）效果推薦；雲端素材庫；付費效果包。

## 限制來源
- 首批配方 12–16 個、±5%：agent 自訂儀器。WCAG 3 次／秒：外部標準（WCAG 2.3.1）。
