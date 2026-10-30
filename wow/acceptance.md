# 答案卷 — qa_media 吸收 video-director（獨立評審，建造前寫定；建造者不得修改）

依據：wow/spec.md、video-director `qa_video.py` 門檻（frame0 mean<8 或 contrast<6 → FAIL；flash 用「跳格」判定；
pop = 單步差 >2 且 >3× 兩鄰 → WARN；freeze ≥1.0 s、eps 0.25/255 → WARN；cuts ≤1 格；loop seam ≤2× 中位步長或 <0.5/255，
速度比 0.5–2；−14 LUFS ±1、TP ≤ −1 dBTP）。下列「實測」由評審 2026-10-30 用 Pillow／ffmpeg 7.1（imageio-ffmpeg）量得。

## 共通規則
- 指令：`python scripts/qa_media.py <input> --out <dir> [...]`。容差：格號 ±1；秒數 ±1 格時長（25 fps = ±0.04 s）。
- 秒數必須用真實格時長累加（GIF/APNG 可變延遲），不得用 格號÷固定 fps。
- 每個 WARN/FAIL 必須在 report.md 與 report.json 都帶格號＋秒數（區段則起訖）。只有籠統分數 = 該條不過。
- 結束碼：有任何 FAIL → 1，否則 0。崩潰（traceback）一律不過。
- 環境：此機 PATH 上沒有 ffmpeg。GIF/APNG/PNG 輸入不得因缺 ffmpeg 崩潰；MP4 需要時以 `VIDEO_GIF_FFMPEG/FFPROBE`
  指向 ffmpeg，缺時須給「run scripts/media_runtime.py --install」類訊息並非 0 結束，不得 traceback。

## 合成短片（評審自行產生；建造者的測試也應涵蓋同型）
BASE：160×120，25 fps（GIF 每格 40 ms，loop=0），100 格 = 4.00 s。背景水平灰階漸層 v=60+x；紅圓 (230,60,60) 半徑 20，
圓心 (80+40cosθ, 60+40sinθ)，θ_i = 2π·i/100（每格約 2.5 px，首尾無縫）。
| 代號 | 做法 | 指令旗標 | 預期 |
|---|---|---|---|
| A 正常循環 | BASE 原樣 | `--loop` | 全部 PASS；loop seam PASS；無 flash/pop/freeze；音訊 N/A；結束碼 0 |
| B 單格閃爍 | BASE，第 50 格（2.00 s）整格換成純白 | — | single-frame flash **FAIL** @ 格 50 / 2.00 s；結束碼 1；其他格不得被報 |
| G 小突波 | BASE，第 60 格（2.40 s）左上 16×16 區塊亮度 +60（僅該格） | — | 在格 60 / 2.40 s 報 pop（WARN）或 flash；不得漏報 |
| C 2 秒凍結 | BASE，格 25–74 全部複製格 25（1.00–3.00 s） | — | frozen stretch 1.00–3.00 s（±0.08）至少 WARN，訊息須說明如何標記為設計停格（--holds 或 timeline） |
| C-hold【陷阱】 | 同 C | `--holds 1.0-3.0`（或建造者文件化的等價語法） | 該段標為 designed hold，**不得 WARN/FAIL**；結束碼 0 |
| C-partial【陷阱】 | 同 C | `--holds 1.0-1.8` | 剩餘 1.8–3.0 s（1.2 s）仍須被報；不可整段放過 |
| D 位置接縫跳動 | θ_i = 2π·0.75·i/99（停在 270°，回到 0° 跳 90°≈57 px） | `--loop` | loop seam **FAIL** @ 格 99→0 / 4.00 s，seam/中位 ≫2；結束碼 1 |
| E 速度接縫【陷阱】 | i≤89：θ=3.9°·i；i=90–99：每格 +0.9°（末格 356.1°，回 0° 只差 3.9°） | `--loop` | 位置 PASS（seam≈1× 中位），但速度比≈0.23 → loop seam **FAIL**，訊息須點出「速度」 |
| F 硬切 | 三場景各 2.00 s：紅圓/灰底、藍方塊/黃底、綠三角/黑灰棋盤；切點 2.00、4.00 s；共 6.00 s | `--expect-cuts 2.0,4.0` | cuts PASS（誤差 ≤1 格）；無 unplanned |
| F-miss | 同 F | `--expect-cuts 2.0,4.4` | cuts **FAIL**：4.4 未找到／4.00 s 為非計畫切點（偏 10 格） |
| H0 黑首格 | BASE，第 0 格全 (0,0,0) | — | frame 0 **FAIL**（black）；另 H0b 第 0 格全 (128,128,128) → frame 0 FAIL（flat） |
| T 透明【陷阱】 | RGBA PNG 夾 `0000.png…0049.png`，128×128；alpha=0 區 RGB 偶數格 (0,0,0)、奇數格 (255,255,255)；不透明 32×32 棋盤方塊（4 px 格，(200,120,40)/(90,60,30)），x=10+2i、y=48 | `--fps 25` | frame 0 PASS（覆蓋僅 6.25%，不得判黑）；**不得**因隱藏 RGB 每格黑白翻轉報 flash/pop；無 freeze；結束碼 0 |
| T-freeze【陷阱】 | 同 T，但方塊在格 10–49 停住（0.40–2.00 s，1.6 s），背景隱藏 RGB 照樣翻轉 | `--fps 25` | 必須報 frozen 0.40–2.00 s（隱藏像素的變化不得掩蓋凍結） |
| S 短片 | BASE 前 30 格（1.20 s） | — | hook_sheet 照樣產生（涵蓋 0–1.2 s），不崩潰 |

音訊合成（需 ffmpeg；可在測試中 skipUnless）：320×240、25 fps、6.00 s 的 MP4，AAC 48 kHz。
| 代號 | 音軌 | 預期（標準答案 = 同檔 ffmpeg `ebur128=peak=true` 實測） |
|---|---|---|
| M1 | 440 Hz 正弦經 `loudnorm=I=-14:TP=-1.5`；2.00–3.00 s 以 `volume=0:enable='between(t,2,3)'` 靜音；4.50–4.60 s 加 +12 dB 爆量 | 響度數字與 ebur128 差 ≤0.5 LU、TP 差 ≤0.5 dB；靜音段 2.0–3.0 s（±0.1）被列出；最響 100 ms 落在 4.50–4.60 s（±0.1） |
| M2 | 全幅方波 0 dBFS（未限幅） | true peak **FAIL**（> −1 dBTP）；結束碼 1 |
| M3【陷阱】 | 無音軌 MP4，及任何 GIF/APNG/PNG | 響度/峰值/靜音 = N/A 或 skipped，**不得 FAIL**，不得把「沒有音軌」算成靜音 |

## 範例作品（examples/，實測值）
| 輸入 | 實測事實 | 預期 |
|---|---|---|
| chibi-running-dash/final.gif | 768²，112 格，3.23 s，延遲 20/30/40 ms 混用；首格 alpha 覆蓋 6.3%；若透明處當黑合成，首格均值≈6.4（<8）；loop 以相同首尾圖釘住，seam≈0.47× 中位 | frame 0 **PASS**【陷阱：不得判黑】；無 flash FAIL；格 73（≈2.21 s，依真實延遲）可報 pop WARN；無 freeze；loop seam PASS；音訊 N/A；結束碼 0 |
| chibi-running-dash/final.apng | 同上，APNG | 結果與 GIF 一致（frame 0 PASS、seam PASS）；不得對 APNG 報錯 |
| robot-wave-no-reference/final.gif | 512²，145 格，6.04 s；README 自承「not certified as a seamless loop」；seam≈5.4× 中位 | loop seam **FAIL** @ 格 144→0 / 6.04 s；frame 0 PASS；結束碼 1 |
| seated-leg-switch/final.gif | 640²，289 格，9.93 s；README：「loop endpoints are not completely seamless」；seam≈4.9× | loop seam **FAIL** @ 9.93 s |
| neon-zen-pv/final.mp4 | 960×540，100 fps 編碼、3000 格但只有 727 張不重複（每張重複約 4 格）；首格 Y 均值≈52–61、std≈45；整合 −14.1 LUFS、TP −2.3 dBTP；−40 dB/0.4 s 內無靜音；9.17–9.47 s 與 26.0–26.3 s 為持續快動作（非單格突波） | frame 0 PASS；**不得**因重複格（差 0 → 差 X → 差 0）把每張新圖報成 flash/pop【陷阱】；flash 0 個；freeze 0 段；快動作段最多 WARN，不得 FAIL；響度 PASS（−14.1 ±0.3）、TP PASS（−2.3 ±0.3）；未加 --loop 時不做 loop 檢查（首尾差≈57/255，不是循環作品）；結束碼 0 |
| neon-zen-pv/final.mp4 `--timeline examples/neon-zen-pv/timeline.json`（或建造者的等價旗標） | 不同 manifest 的接點在 5.55、11.73、17.60、24.20 s，chain-qc.json 顯示是接續鏡（前段尾格＝下段首格，MAE≈3–3.8）；3.50 與 21.27 s 是同一來源內的變速點 | 【陷阱】這些點**不得**判「缺少計畫中的硬切」FAIL；可 PASS（接點平順）或 WARN 並說明是接續，不是硬切；結束碼仍 0 |

## S 條目判定
- **S-1** 對 A、T（PNG 夾）、chibi GIF、chibi APNG、neon MP4 各跑一次：`<out>/` 下必須有 report.md、report.json、
  contact_sheet.*、phone_sheet.*（寬度剛好 360 px，用 Pillow 量）、hook_sheet.*（僅含 0–3 s 的格，或短片的全長）。
  report.json 可被 `json.load` 讀取，每項檢查有 level ∈ {PASS, WARN, FAIL}。結束碼：A=0、B=1、D=1、chibi GIF=0、robot GIF=1。
- **S-2** 上方合成表與範例表的每一列都對（含全部【陷阱】列）。任何一個陷阱列錯 = S-2 不過。
- **S-3** SKILL.md 的「Final quality gate」與「Export and verify」兩節都提到 `scripts/qa_media.py`：何時跑、怎麼讀 PASS/WARN/FAIL、
  數字證明不了什麼（例如動作自然、語意正確）。新增 `references/quality-review.md` 且 SKILL.md 有連結；內含：
  獨立評審不帶建造歷史、預設拒絕、引用格號、只看畫面重述主旨、完成定義清單；明寫 GIF/sprite 不檢查響度、
  透明素材只看 alpha 覆蓋區、設計停格如何標記。不得照搬 video-director 的文字排版／旁白／FACTS.md 條目而不適配。
- **S-4** README.md（及 README.zh-TW.md）註明來源 https://github.com/win4r/video-director、MIT、© 2026 win4r；
  `scripts/qa_media.py` 與 `references/quality-review.md` 檔頭有出處；THIRD_PARTY（或 LICENSE 附註）含 MIT 全文與版權行。
- **S-5** `python -m unittest discover -s tests` 新增 qa_media 測試，至少涵蓋 B（閃爍）、C（2 秒凍結）、D（接縫跳動）、A（正常循環），
  並斷言格號/秒數與 level，不只斷言「不崩潰」。這四個必須用 Pillow 產生 GIF/PNG，在**無 ffmpeg 的此機實際執行（不得 skipped）**。
  基準線（建造前，2026-10-30，以 pillow+numpy+opencv 執行）：125 tests，5 errors（3 個缺 ffmpeg、1 個 Windows symlink 權限、
  1 個 Windows 檔案鎖），8 skipped。建造後：除這 5 個既有環境錯誤外不得新增 error/failure；若設定 VIDEO_GIF_FFMPEG 讓缺 ffmpeg 的
  3 個通過更好。
- **S-6** `python scripts/doctor.py` 輸出包含 qa_media 的相依狀態（numpy、PIL、ffmpeg、ffprobe）；
  `git diff main -- requirements.txt` 不新增必要套件；`scripts/qa_media.py` 的 import 僅限標準庫＋numpy＋Pillow
  （ffmpeg 經 media_runtime 取得，不硬寫 PATH 上的 ffmpeg）。
- **S-展示** `wow/demo/chibi-running-dash/` 與 `wow/demo/neon-zen-pv/` 各有 report.md、report.json 與三張圖，內容符合範例表預期；
  每次執行牆鐘時間 ≤ 30 s（驚豔時刻；超過記為未達）。交付對照表列出這些路徑。

## 不算通過的樣子
- 報告沒有格號／秒數；或透明 GIF/APNG 報錯或首格判黑；或 GIF 因無音軌 FAIL；或 C-hold 仍 WARN 而訊息沒說怎麼標記。
- 測試只在有 ffmpeg 時才跑；或改動 examples/ 內任何檔案；或修改本答案卷。
