# Batch 1 規格 — video-gif-studio 輕量交付（上架前入口）

- 模式：wow 交付：輕量
- 日期：2026-11-22（Asia/Taipei）
- 核准：Alex 核准執行；成本上限 $0（不呼叫付費生成）；不改 `.github/workflows`；不提交 Agensi、不對外聯絡
- 核心情境（唯一）：本機既有影片 → 人用一條指令得到可檢查的透明 GIF；同一套工具可作為 Claude Code 與 Codex skill

## 痛點與來源

獨立創作者／遊戲開發者要把 AI 或綠幕／洋紅底影片做成透明 GIF 或 sprite。現行做法是在 ezgif、去背、匯出工具之間手動切換，代價是時間與第一眼品質不穩。來源：擁有者指定需求（2026-11-22 審查與核准）；市場規模標**未知**。對外不得宣稱已驗證的市場節省。

審查證據（本機，免費路徑）：預設 `gif_pipeline.py source.mp4 --out DIR` 產出 12.19 MB 洋紅背景 GIF 且 `technical_pass: true`；正確色鍵後 5.726 秒得到 1.12 MB 透明 GIF，但 QA loop FAIL、尾端定格 WARN。README 不提 `gif_pipeline.py`。安裝器預設只裝到 `~/.codex/skills`。

## 領域要點（建造前列出，答案卷可補反例）

- GIF 為二值透明；洋紅／綠幕殘留不得被當成通過。
- 色鍵須對純色背景有把握才自動套用；前景也可能含洋紅，不確定時應警告而非默默破壞前景。
- 不得把技術通過說成視覺／循環通過。
- 自動處理尾端定格時，須記錄做了什麼；不能假裝來源本來就無縫。
- 本機路徑不得呼叫 Grok／fal。
- 價格表只能引用已核對來源與日期；上架前須再查。
- 不改 CI workflow（另案）。
- Sprite 預設 metadata 仍是 repo 自訂 schema，不得宣稱原生 Unity／Godot／TexturePacker。

## 驚豔時刻與未抵達的樣子

- 驚豔：人（或不看長文的 agent）對一支洋紅底示範影片下達一條指令，得到透明 GIF、人話摘要與 QA；不再出現「12 MB 洋紅還顯示通過」。
- 未抵達：預設仍留下洋紅且 QA 通過；或必須讀長文、記四個旗標才做對；或 Claude Code 仍無法按官方文件安裝／呼叫。

## 主流程與首次使用時間（事前登記）

- 主流程：安裝或使用已有 venv → `python scripts/vgs.py make <video> --out <new-dir>`（或同等 `vgs make`）→ 輸出透明 GIF + 摘要 + QA。
- 時間目標：從看到 README 入口到發出正確指令 ≤ 30 秒（待真人確認）；本機編碼牆鐘另列，目標 ≤ 15 秒（chibi 來源、≤ 320px 寬）。代理估計須標待真人確認。
- 安裝（照 README）與「不看文件完成主任務」分開驗。

## 贏面表（開工）

| 關 | 適用 | 狀態 | 判準與證據路徑 | 未抵達／未知 | 下一步 |
|---|---|---|---|---|---|
| W1 痛點 | 是 | 指定需求可通過；市場未知 | 本檔痛點段 | 市場 | 保持宣稱不超過證據 |
| W2 美觀 | 是 | 待建造 | README 首屏、壓縮 hero、CLI 摘要 | 390／1440 審查 | 設計審查 |
| W3 好用 | 是 | 待建造 | 一條指令、人話錯誤、0 次因介面不清而猜錯 | 真人 30 秒 | L10 |
| W4 介面 | 是（無資料圖：7–12） | 待建造 | 入口層級、狀態誠實、預覽若有則可讀 | 獨立設計審查 | L8 |
| W5 驚豔 | 是 | 待建造 | 真實主流程可重現透明成果 | 盲測分享句 | 示範 |
| W6 領域與實作 | 是 | 待建造 | 非門面：洋紅片→透明；QA 對未去背失敗 | 保留樣本種類 | 測試 |
| W7 工作流 | 是 | 見 progress 宣告 | 成本 0、不改 workflow、小步提交 | CI 另案 | 對照消耗 |

## S 條目

**S-1 一條指令、透明預設。** `python scripts/vgs.py make examples/chibi-running-dash/source.mp4 --out <新目錄>`（不手動傳 `--key`）產出透明 GIF：棋盤底可見主體、無整片洋紅背景、gif_pipeline alpha 不符為 0。人話摘要含尺寸、幀數、時長、MB、是否去背、QA 等級。編碼牆鐘 ≤ 15 s。

**S-2 未去背不得通過 QA。** 對同一支影片若強制保留背景（明確旗標或關閉自動色鍵），QA／交付檢查必須 FAIL 或同等非零結束碼，並指出背景未去除。不得 `technical_pass` 掩蓋洋紅底。

**S-3 尾端定格與循環。** 對 chibi `source.mp4` 的快速起步，不得再出現約 3.54–6.04 s 的長定格 WARN 而不處理。須自動裁切或壓縮尾端定格，並在摘要中說明。若 loop 仍 FAIL，摘要須誠實寫出，不得標視覺通過。目標：處理後定格不再覆蓋收招後的長靜止；loop 能過則過，不能過則清楚標示。

**S-4 人話錯誤。** 來源不存在、PNG 目錄缺 fps、輸出目錄非空、誤標影片 FPS：不得只丟未捕捉的 traceback；須說明發生什麼、影響、下一步。結束碼非 0。

**S-5 雙軌 README + How it works + 圖生影表。** 中英 README 開頭說明這是獨立工具也是 skill；有 How it works 圖（本機 vs 生成 API）；有圖生影選項表，價格僅用 2026-11-22 已核對來源（本機 $0；Grok／X 方案網站額度；Grok API 標題價 1.5 $0.080／秒、lite $0.020／秒，並註明分級表可能不同、上架前再查；fal H3 Max 自 2026-11-16 起 $0.05／$0.08／$0.16 每秒於 480p／768p／1080p）。QA 說明下移。首屏 hero 各 ≤ 3 MB（目標 ≤ 2 MB）。

**S-6 Claude Code 支援。** 安裝器可裝到 `~/.claude/skills`（偵測或 `--target claude`／`--skills-dir`）。文件同時寫 `/video-gif-studio` 與 `$video-gif-studio`。無內建生圖時說明需提供起始圖或既有影片。須在本機 Claude Code 實跑：載入 skill、doctor、以及本機 `vgs make`（或 skill 指引的同等命令）。相容 agent 只宣稱已驗證的 Codex 與 Claude Code。

**S-7 壓縮 hero／示範圖庫與 Agensi 包。** README 示範圖可快速載入。產出 `/workspace/money-radar-team/2026-11-22/agensi-listing-pack.md` 與 `video-gif-studio-agensi.zip`（及封面若需要）。包內不含必須排除的巨型建造產物；不提交上架。

**非目標：** 改 `.github/workflows`；付費生成；原生引擎 importer；自動宣稱所有循環無縫；對外寄信或提交 listing。

## 呈現形式（L2）

- CLI：成功時一段人話摘要（必要數字＋路徑）；失敗時「什麼／影響／下一步」。
- README：首屏英雄圖與兩條入口（人／agent）；How it works 層級清楚。
- 若輸出目錄含簡易 preview／contact，須可在淺／深底辨識透明。
