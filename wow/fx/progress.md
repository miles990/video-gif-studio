# progress — wow 輕量：fx 程式化特效／轉場框架（2026-11-04）

## 決定
- 交付模式：輕量（使用者只說「使用 wow 技能」；需求已指定、單一核心情境、同 repo 上輪也用輕量）。撤回：改說「做成品」即從步驟 3 接續。
- 開發副本 C:\Users\User\src\video-gif-studio，分支 fx-framework；已安裝 skill 不動。
- 建造者 Codex（wow-agent），出題與評審 Claude 子代理（跨廠商）。一次只跑一個重任務（16 GB 機器，見 agent-conduct 5）。
- 摳像：Windows 無 Mac「拷貝主體」，沿用 repo 既有 alpha／background_remove（spec「不做」）。

- 18:25 使用者：「吸收 改善…用最好的做法做」→ spec 加 S-10～S-13（onset 包絡、Beat This! 重拍、BiRefNet 摳像、使用者層級效果庫）。
- 18:35 使用者貼第二則推文（rea-video，無授權）→ spec 加 S-14 逆向（只吸收概念、自行實作）。範圍擴大，3 小時預算可能不足：超過時先保核心 S-1～S-9＋S-展示，S-10～S-14 依序取捨並如實回報。
- 選用依賴裝在 repo 外 C:\Users\User\src\fx-optdeps\venv（torch CPU、beat_this、rembg），不污染技能 venv。

## 工具就緒
- 開發副本 .venv 存在；已安裝 skill venv：numpy 2.5.4、Pillow 13.0.0、OpenCV 5.0.0。Codex CLI 0.166.0。磁碟 C: 剩 30 GB。

## 步驟
- [x] 1a 規格 spec.md（18:09）
- [x] 1b 驗收條目 acceptance.md（獨立 Claude 出題者，18:50 完成）＋保留樣本 14 條（repo 外 scratchpad/fx-holdout.md）
- [ ] 2 建造（Codex，wow-agent 標籤 fx-build，18:55 開始，上限 150 分）
- [ ] 3 審查一 → 修正 → 審查二
- [ ] 4 首次使用＋示範
