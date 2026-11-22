# Batch 2 規格 — video-gif-studio 輕量交付（W5 過關 + 像素風 X 展示）

- 模式：wow 交付：輕量（接續 Batch 1）
- 日期：2026-11-22（Asia/Taipei）
- 核准：Alex 核准執行 Batch 2；成本上限 $0（不呼叫 Grok／fal）；push `main`；不改 `.github/workflows`；不提交 Agensi、不發 X 貼文
- 優先目標：讓 W5（驚豔與可檢驗品質）過關，並補齊 Batch 1 Fable 評審指出的必改項，加上像素風預設與 X 首發素材包

## Batch 1 遺留與本批解題

1. **旗艦 loop 必須通過 QA（S-8）**：Batch 1 對 `examples/chibi-running-dash/source.mp4` 只在最後移動幀後固定加 0.4 s guard（93 幀 / 3.88 s），落在極低速壓縮尾幀上導致 `loop FAIL: speed mismatch`。Batch 2 須加入**誠實的自動迴圈點偵測（`--loop auto`，預設）**：在動作結束附近搜尋同時滿足 `qa_media` position 與 speed 門檻的自然回位點並裁切（無淡入淡出／插幀）；對不回位的非循環片，不得默默 crossfade，須誠實報 `loop FAIL`，僅在明確指定 `--loop crossfade` 時才混合接縫並於 manifest 與摘要揭露。
2. **解決連通色鍵 vs `magenta_share_max ≤ 0.02` 衝突與低飽和底保護（S-9）**：
   - Batch 1 發現：純連通色鍵把 chibi 第 54 幀劍弧封閉區內的背景洋紅留在畫面中（`mag_max = 0.2722`），而官方示範與 S-1 驗收要求為 `≤ 0.02`。另一方面，直接全域色鍵若遇低飽和中性背景（如米白、淺灰、米黃 `sat < 0.35`），會因色度距離為零而把主體整片刪掉。
   - Batch 2 規定：
     - 自動色鍵須同時滿足「邊框均勻穩定（confidence > 0.95）」**且**「邊框為高飽和棚景鍵色（HSV/RGB chroma 飽和度 ≥ 0.35）」，否則不自動去背並誠實標示原因與「非透明交付」；若使用者真的想對低飽和純底去背須明確傳 `--key <HEX>`。
     - 預設全域色鍵清除背景與受困封閉棚景（確保 `magenta_share_max ≤ 0.02`），同時偵測是否有與邊框不連通的鍵色區塊（例如 C1 內框或劍弧內袋）；若有，摘要與 manifest **必須明確警告**（列出面積比例與 `--keep-interior-key` 選項），不得默默挖空。提供 `--keep-interior-key` 供需要保留內框的人使用。
     - `vgs qa` 與 `vgs make` 同時回報 `border_opaque_max` 與殘留鍵色比例（magenta/key share），不得只看邊框就放過大塊未去背面積。
3. **像素風預設 `--pixel` + Sprite 與 X MP4 輸出（S-10）**：
   - `vgs make` 支援 `--pixel` 預設（搭配可選 `--pixel-width`、`--pixel-scale`、`--colors`、`--sprite`、`--mp4`、`--loop-count`）。
   - `--pixel` 使用最近鄰（`NEAREST`）降採樣至像素網格（未指定 `--pixel-width` 時預設 96 px 寬）、無抖動限制色盤（預設 32 色，可由 `--colors` 指定 2..255）、整數倍率最近鄰放大（預設放大至 ≥ 288 px 寬，保持硬邊）。
   - `--sprite` 於 `--out/sprites/` 呼叫既有 `sprite_export.export` 產出 `sheet-000.png` + `sprites.json`（專案 schema，不宣稱原生 Unity／Godot／TexturePacker）。
   - `--mp4` 產出 H.264 `yuv420p` 規格（供 X 播放；可使用 `--loop-count` 重複至 8–15 秒，於深色底合成，保留最近鄰硬邊）。
   - 在 `/workspace/money-radar-team/2026-11-22/x-pixel-media/` 實產一套 Alex 首發 X 像素風專欄素材：MP4（8–15 秒）、透明像素風 GIF（< 15 MB）、Sprite Sheet 與說明檔。
4. **保留（held-out）真實影片實測（S-11）**：
   - 使用不帶自訂旗標的 `python scripts/vgs.py make <video> --out <new-dir>` 實跑至少 3 支非 `chibi` 的真實影片（含至少 1 支飽和棚景片、1 支低飽和純底片、1 支複雜背景片），全部免費本機，紀錄關鍵判定與 QA 結果到 `wow/batch2/evidence/`。
5. **線上 GitHub README 首屏截圖（390 & 1440）與同步更新（S-12）**：
   - 更新並 push 後，用無頭瀏覽器截取 `https://github.com/miles990/video-gif-studio` 首屏 `390×844` 與 `1440×900` 畫面，交由獨立 W4 設計審查（Claude）檢視，並同步更新 README（含新 `hero.gif`、`hero-preview.png`、真實 `vgs make` 輸出範例與 `--pixel` 用法）、`SKILL.md` 與 Agensi 精簡包（仍不送出）。

## 非目標

- 不改 `.github/workflows/` 與另案 `scripts/run_ci_smoke.py`
- 不呼叫 Grok／fal 或任何付費 API
- 不提交 Agensi、不發 X 貼文、不對外聯絡
- 不覆寫 `examples/*/final.gif` 與官方紀錄
