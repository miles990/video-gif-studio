# spec-15 — 接上 Suno MCP（音樂、遊戲配樂、音效）（2026-11-06）

來源：使用者 2026-11-06 `/wow 剛剛看到這個 可以用`（Suno MCP 存取權截圖）。專案重心：影像、影片、遊戲資源。
已連線：Codex `codex mcp add suno --url https://api.suno.com/mcp`（OAuth 已登入）；Claude Code 已註冊、待使用者 `/mcp` 登入一次。
實測（只讀、未花點數）：35 個工具；帳號 Premier 年費、**歌曲點數 8,510**、**下載點數 67**（下載才扣，稀缺）；library 有使用者自己的作品（盤／神の盤／ゲーム開始…）。
依使用者授權（2026-11-06：只有 AI 生成**影片**要先問）：音樂生成可直接做，但**下載點數只有 67**，要節省並記帳。
trunk-based，每個 S 一個切片，當天以 experimental 合回 main。

## Suno 工具 → 我們怎麼用（依實際 schema）
| 工具 | 用途 |
|---|---|
| `sounds_create`（`tempo` BPM、24 種 `key`、`loop` 無縫循環） | **遊戲 BGM 循環**（關卡、選單、戰鬥）、**音效／短樂句**（升級、勝利、失敗 jingle、UI 音），可指定 BPM 與調性 → 跟動畫節拍直接對齊 |
| `audio_create`（`instrumental`、`duration`／`duration_strict`、`style`／`negative_style`、`lyrics`、controls：audio/style influence、weirdness、variety） | 影片配樂（指定長度、純音樂）、角色主題曲、預告片配樂 |
| `audio_extensions_create`＋`audio_full_song` | 把配樂延長到片長或段落（從某秒接續） |
| `audio_covers_create`／`audio_mashups_create` | 同一主題的不同風格版本（戰鬥版、和平版、8-bit 版）→ 遊戲的「同主題變奏」 |
| `audio_analysis`／`audio_listen` | 量測 BPM、調性、段落 → 接 music_sync／Beat This!／spec-7 品味報告 |
| `audio_lyrics_alignment` | 歌詞逐字時間 → 直接接 P1 逐字字幕（卡拉 OK 式） |
| `audio_upload_create/complete` | 上傳使用者自己的音訊做翻唱／延長／分析 |
| `audio_download`（mp3／wav；**扣下載點數**、需 `confirm`） | 只下載最終選定版本；預覽用 `audio_listen`／串流，不下載 |
| `library_*`、`playlists_*` | 管理產出、把專案配樂收成 playlist；重用使用者既有作品 |

## 規格
- S-170 **音樂路由**：`music_route=suno`（MCP，經 Codex 或 Claude Code）；記錄工具、參數、clip id、扣點（歌曲／下載）；快取（同請求不重生）；
  下載點數防呆：預設只下載使用者選定的 1 版、wav 優先；每輪下載上限（預設 5），低於 10 點時停止並回報。
- S-171 **遊戲 BGM 循環**：依關卡情緒／BPM／調性生成 `loop=true` 循環；本機驗證無縫循環（尾首交叉相關、無爆音、響度一致），並輸出引擎可用格式（OGG／WAV＋loop 點 metadata：Godot、Unity、FMOD 風格）。
- S-172 **遊戲音效與 jingle**：UI、拾取、升級、勝利、失敗、受擊等短音效（`sounds_create`），調性與主題曲一致；響度正規化、裁切靜音、短淡出；與 spec-14 VFX sprite 對齊時間。
- S-173 **影片配樂**：依分鏡／brief 的段落與 drop 位置與長度生成（`duration_strict`），必要時延長；分析後與既有 music_fit／節拍分層對齊。
- S-174 **同主題變奏**：一個主旋律產出多個情境版本（探索／戰鬥／Boss／勝利／8-bit），共用調性與動機；變奏間可無縫切換（相同 BPM／小節對齊）。
- S-175 **歌詞逐字對齊 → 字幕**：用 `audio_lyrics_alignment` 取逐字時間接 P1 字幕樣式（不必再跑 whisper）。
- S-176 **節拍驅動動畫**：用 Suno 給的 BPM／分析結果驅動 sprite 動畫與 VFX 的節拍（例：角色 idle 隨 BGM 拍子擺動、攻擊命中落在重拍）。
- S-177 **用量與來源紀錄**：manifest 記錄 Suno clip id、模型／參數、授權（使用者帳號產出）、扣點；不把使用者私人作品公開。
- S-178 **示範**：一個原創小遊戲情境：主題曲＋探索／戰鬥兩個無縫循環＋5 個 jingle／UI 音效，配上 spec-14 的角色 sprite 隨拍子動，輸出 Godot 可用的音訊與動畫；
  看片聽音由獨立評審（技術軸：循環接縫、響度、對拍）＋使用者抽查（好聽）。

## 驚豔時刻
一句「冰劍狐狸劍士的雪山關卡」→ 拿到同主題的探索／戰鬥兩段無縫循環 BGM、升級與勝利 jingle，角色 sprite 跟著 BGM 的拍子呼吸、攻擊落在重拍，整包直接丟進 Godot 就能跑。
