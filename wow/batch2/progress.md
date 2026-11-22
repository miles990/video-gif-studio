# Batch 2 progress — video-gif-studio 輕量（W5 + Pixel）

## 資源宣告（G1）

- 成本上限：$0；不呼叫 Grok／fal
- Fable 評審呼叫上限：≤ 2 次（`claude -p --model claude-fable-5-1`，禁用工具）
- 路由：規格＝協調者；獨立答案卷＝Claude Opus；建造＝Codex；W4 設計審查＝Claude（非建造者）；交付前評審＝Fable 5-1
- 不改 `.github/workflows`；每次 push 前檢查 `origin/main`

## 關卡

- [x] G1 資源宣告（本檔）
- [x] L1–L2 spec.md（Batch 2）
- [x] L4 獨立答案卷（Opus，建造前；wow/batch2/acceptance.md）
- [x] L7 建造（Codex + coord fix `3b83806` / `873003d`）
- [x] L8–L9 驗證、實跑 held-out 與 recovery hints、X 像素素材、GitHub 390/1440 淺深雙色截圖、獨立 Sonnet W4 設計審查
- [ ] L11–L13 Fable 評審（Call 1 已存 `wow/batch2/reviews/fable.md`；Call 2 觸發 `claude-fable-5-1` CLI 用量上限：`You're out of usage credits.`，待帳號額度恢復後可補跑或由 Alex 直接複核）
