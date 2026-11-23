# wow／INDEX — video-gif-studio

本目錄是過程紀錄與索引。最終示範成品在產品路徑（`examples/`、`README.md` 等），不要在 `wow/` 再複製一份。

## 本輪（2026-11-23 八關稽核）

| 路徑 | 內容 |
|---|---|
| [audit-2026-11-23.md](audit-2026-11-23.md) | W1–W8 判決、E1–E11 表、Fable 摘要、測試與 CI、缺口階段建議 |
| [INDEX.md](INDEX.md) | 本檔 |

中間產物在 `wow/work/`（**不要 commit**）：

| 路徑 | 內容 |
|---|---|
| `work/evidence/eng/` | `wow-eng all --run` 的 `eng.json`、`eng-report.md` |
| `work/evidence/doctor/` | 本輪 `doctor.py` JSON |
| `work/evidence/visual/` | 本輪 `vgs make`／`qa_media` 輸出、GitHub 390／1440 淺深截圖、合成幀 |
| `work/logs/` | 完整單元測試 log |
| `work/reviews-raw/` | Fable 提示詞與原文 |

## 既有過程紀錄（歷史，已在 git）

這些是 batch 1／batch 2 與較早的 demo／fx 工作檔，尚未依 2026-11-23 目錄規則搬到 `work/`。本稽核不搬、不改產品碼。

| 路徑 | 內容 |
|---|---|
| [progress.md](progress.md)、[spec.md](spec.md)、[acceptance.md](acceptance.md)、[DELIVERY.md](DELIVERY.md) | 較早的進度、規格、驗收、交付 |
| [batch1/](batch1/)、[batch2/](batch2/) | 輕量輪的規格、答案卷、評審與部分證據（含 390／1440 README 截圖、held-out、Fable 5-1 紀錄） |
| [demo/](demo/)、[fx/](fx/) | 歷史示範與特效研究產出 |

## 產品路徑上的成品（不在 wow／複製）

| 路徑 | 內容 |
|---|---|
| [`README.md`](../README.md)、[`README.zh-TW.md`](../README.zh-TW.md) | 人類第一入口 |
| [`SKILL.md`](../SKILL.md) | Claude／Codex skill |
| [`examples/`](../examples/) | 可分享示範（含 `examples/chibi-running-dash/hero.gif` 等） |
| [`scripts/vgs.py`](../scripts/vgs.py)、[`scripts/doctor.py`](../scripts/doctor.py)、[`scripts/install.py`](../scripts/install.py) | 人類 CLI／安裝 |
