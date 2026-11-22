# Batch 1 progress — video-gif-studio 輕量

## 資源宣告（G1）

- 時間盒：1–2 人日；最後 20% 只修錯、複驗、示範
- 成本上限：$0；不呼叫 Grok／fal，只用既有示範素材
- 路由：規格由協調者寫；答案卷＝Claude Opus（`claude -p --model opus`）；建造＝Codex（`codex exec`）；畫面／W4 審查用與建造者不同廠商（Claude）；交付前評審＝Fable（`claude -p --model claude-fable-5-1`，禁用工具、高 effort）；本機驗證用既有 venv＋ffmpeg
- 不改 `.github/workflows`；每次 push 前 `git pull --rebase origin main`
- CI 修復另案；上架前再看徽章

## 關卡

- [x] G1 資源宣告（本檔）
- [x] L1 spec.md
- [x] L2 呈現形式已寫在 spec
- [x] L3 開工實跑（建造後 /tmp/vgs-acc2 與 Claude Code 實跑）
- [x] L4 獨立答案卷（Opus，建造前；wow/batch1/acceptance.md）
- [x] L7 建造（Codex + 協調者修正）
- [x] L8 審查一＋獨立設計審查（wow/batch1/reviews/design-review.md）
- [x] L9 審查二（修正首屏 hero、真實 CLI 輸出後複驗）
- [x] L10 首次使用（CLI 與 Claude Code 實跑已做；真人 30 秒計時仍待）
- [x] L11–L13 示範與交付檔已備（Agensi 包未送出）
- [x] 交付前 Fable 評審（claude-fable-5-1；W5 未通過，整批 未達成）

## 偏離

- 既有 `wow/spec.md` 等保留為 qa_media 輕量紀錄；本批工作檔在 `wow/batch1/`。
- Fable 模型指定為 `claude-fable-5-1`（非 `claude-fable-5`）。

## Fable（claude-fable-5-1）

W1–W4、W6、W7 通過；W5 未通過；整批 **未達成**。詳見 reviews/fable.md。
