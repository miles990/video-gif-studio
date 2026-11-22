# Batch 1 self-check（建造後修正，2026-11-22 20:15 台北時間）

全部本機、未呼叫 Grok／fal。Python：`/home/box/.codex/skills/video-gif-studio/.venv/bin/python`。輸出：`/tmp/vgs-acc2`。

## S-1 chibi（一條指令，不傳 --key）

- 牆鐘 5062 ms（≤15 s）
- 已去背，鍵色 #FC01F9，信心 1.000，border_opaque_max 0，alpha_mismatch_pixels 0
- 93 幀，3.87 s，0.72 MB，320×320
- 尾端 trim：6.04s → 3.88s；來源 3.88–6.04s 裁切，guard 0.42s；最後移動幀 3.42s（基線 freeze 起點約 3.54s 附近）
- QA：freeze PASS；pops WARN；loop FAIL（speed mismatch）——摘要已寫明，沒有寫無縫或視覺通過
- 劍光等洋紅特效被保留（連通色鍵不挖主體）；這會讓「不透明像素中的洋紅佔比」在攻擊幀升高，但邊框仍全透明，不是整片背景殘留
- preview.png 有淺底與深底棋盤

## 對照組

- C1 洋紅平底：外部去背、白塊保留、內框洋紅島保留並說明連通色鍵；exit 0
- C2 花背景：未去背（信心 0.021），標示非透明交付；exit 0
- C3 綠幕：自動偵測 #00FE00 並去背；exit 0

## S-2

- `--no-key`：同樣裁切尾端（93 幀、3.87s），loop 量測通過，但交付因「背景未去除」FAIL，exit 1
- 舊 `gif_pipeline.py` 未去背產物：`vgs.py qa` exit 1，邊框不透明比例 1.000
- 對 S-1 透明 GIF：`vgs.py qa` exit 0

## S-4

四個案例皆 exit 1、無人話之外的 Traceback、keep.txt 雜湊不變、缺失來源未建立輸出目錄。

## S-5 / S-7

README 開頭為雙軌入口 + How it works + 2026-11-22 價格表；示範內嵌 hero 皆 ≤ 0.89 MB；原 final.gif 未覆寫。Agensi ZIP 約 3.9 MB、271 檔，未送出。

## S-6

`--target claude` 與 `--skills-dir` 在暫時 HOME 成功；重跑既有不同來源 exit 1 且不覆寫。doctor exit 0，`local_gif_runtime_ready: true`。未改使用者真實 `~/.claude/skills` 或 `~/.codex/skills`。Claude Code 實跑見同目錄後續紀錄。
