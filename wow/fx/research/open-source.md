# video-gif-studio 開源與研究調查（2026-11）

範圍：對照我們已選定的方案（numpy 特效、Beat This!、rembg BiRefNet、DIS 光流 + RIFE v4.25 lite ONNX、Depth Anything V2 Small ONNX、程序化 SFX、.cube LUT、自製 scene/cut 偵測、AI 導演），找出**更好或可互補**的開源專案與論文。
判定分級：**採用（現在）**／**可選引擎**（optional engine，裝了才啟用）／**之後**／**拒絕**。
授權欄位中「商用 OK」是指程式碼與權重都可商用。標示「未證實」的部分是本次查不到一手 LICENSE 的情況，落地前要再看一次 repo 根目錄。

---

## 0. 會改變現行計畫的判定（摘要）

1. **移動主體去背**：rembg BiRefNet 逐幀推論會**閃爍**（沒有時間記憶）。保留 BiRefNet 作為單幀品質來源，但要**加一層我們自己的時間穩定化**（用 DIS 光流把上一幀 alpha warp 過來，再做 EMA 或中值融合）；**SAM 2.1 tiny（Apache-2.0）列為可選引擎**，負責追蹤遮罩與提示。**RobustVideoMatting（GPL-3.0）和 MatAnyone／MatAnyone 2（NTU S-Lab，非商用）一律拒絕**，只能吸收概念。
2. **2.5D 深度**：影片場景改用 **Video Depth Anything Small（Apache-2.0，有串流模式）** 取得時間一致的深度；單張圖可以考慮 **Depth Anything 3 Small／Base（兩者都是 Apache-2.0）**。DA2 Small 保留為最輕量的預設。DA2、DA3、VDA 的 Base／Large／Giant 有不少是 **CC-BY-NC**，必須在程式裡硬性擋掉。
3. **音樂段落（verse／chorus）**：All-In-One 程式碼是 MIT，但依賴 madmom（模型檔為 CC BY-NC-SA）和 NATTEN（Windows 安裝很痛苦）→ 列為「之後／可選」。**現在先用 librosa（ISC）做自相似矩陣加 Foote novelty 的段落切分**。**Essentia 是 AGPL → 拒絕**。Beat This! **不要啟用 madmom DBN 後處理**（安裝相依問題，而且 madmom 套件裡附帶 NC 模型檔），用它內建的 minimal postprocessing 就好。
4. **轉場**：把 **gl-transitions（MIT，100 多種，每個檔頭都標了授權，其中 2 個是 BSD）的數學移植成 numpy**。這是 CP 值最高的吸收對象。最終輸出另外提供 **ffmpeg xfade 快速路徑**（可選）。
5. **字幕／文字動畫**：預設用 **faster-whisper（MIT）`word_timestamps=True`**；**WhisperX（BSD-2）為可選**，對齊更準，但 pyannote 分離說話者要額外看授權。文字渲染考慮加 **skia-python（BSD-3）作可選字體引擎**，處理描邊、漸層、文字路徑、複雜字型 shaping；Pillow+raqm 留作預設。
6. **品質／美學評分**：**pyiqa（IQA-PyTorch）是 NTU S-Lab + CC BY-NC-SA → 拒絕**，連帶 MUSIQ、Q-Align 透過 pyiqa 的權重都不能用。DOVER 的 repo 裡有 `S-Lab-LICENSE` → 視為非商用，拒絕。Q-Align 是 7B，CPU 跑不動，拒絕。**LAION aesthetic predictor（mirror 標 Apache-2.0，未證實）列為可選**。主力維持「實測指標 + agent 看 contact sheet」。
7. **Remotion 拒絕**：公司超過 3 人就要付費，授權也禁止拷貝它的程式碼去做衍生產品。spring／interpolate 的數學**要自己從阻尼諧振子公式實作**，不能從 Remotion 原始碼移植。
8. **吸收 auto-editor（Unlicense，公有領域）**：音量／動態閾值剪輯的邏輯可以直接移植，用在「去除靜止段」和「去除靜音段」。
9. **鏡頭偵測**：維持自製方案，但**吸收 PySceneDetect（BSD-3）AdaptiveDetector 的演算法**（滾動平均比值，對快速運鏡比較穩）；**TransNetV2（MIT）列為可選引擎**，用來抓漸變、溶接這類軟轉場。
10. **本地 VLM**：**Qwen3-VL 2B／4B（Apache-2.0，llama.cpp GGUF 已支援）列為可選的離線描述器**。預設仍由驅動我們的 agent 自己看 contact sheet，因為它本身就是更強的 VLM，不必再多跑一個模型。

---

## 1. 渲染／合成框架：什麼時候會比 numpy 好？

| 專案 | 授權 | 維護 | CPU 成本 | 整合成本 | 判定 | 理由 |
|---|---|---|---|---|---|---|
| ffmpeg xfade／filtergraph | LGPL/GPL（看 build，以外部執行檔呼叫） | 活躍 | 極低（C、SIMD） | 低 | **可選引擎（快速路徑）** | 長片、高解析的純轉場或縮放，比 numpy 逐幀快一個數量級。效果種類有限，也不能逐像素自訂。最終編碼本來就在用 ffmpeg。 |
| gl-transitions（GLSL） | MIT（2 個 BSD） | 穩定（以集合為主） | 移植 numpy 後中等 | 中（逐一移植） | **吸收公式到 numpy** | 見第 11 節。不必引入 OpenGL 執行環境。 |
| moderngl（+ gl-transitions 原生跑） | MIT | 活躍 | GPU 快，headless 環境需要 EGL／OSMesa | 高（Windows／CI 無 GPU 的情況） | **之後** | 只有在 4K、長片需要即時轉場時才划算，跟 offline-first、CPU 友善的方向衝突。 |
| skia-python | BSD-3 | 活躍 | 低到中（CPU raster 很快） | 中 | **可選引擎（文字、向量）** | 文字 shaping、描邊、漸層填色、路徑動畫、抗鋸齒品質都明顯勝過 Pillow，適合 kinetic typography。輸出 numpy array 就能接進現有管線。 |
| MoviePy 2.x | MIT | 活躍（2.0 在 2025 年初大改 API） | 慢（Python 逐幀） | 低 | **拒絕（作為引擎）** | 本質上也是 numpy 加 ffmpeg，對我們沒有新增能力，2.0 的 API 破壞性變更也是風險。 |
| editly（Node） | MIT | 單人維護 | 中 | 高（要 Node、headless-gl） | **拒絕引擎，吸收概念** | 宣告式 JSON 剪輯規格、自動 crossfade、ducking 可以借鏡到 storyboard JSON。 |
| FFCreator（Node） | MIT | 維護狀態不明 | 中 | 高（node-canvas、headless-gl，Linux 要 xvfb） | **拒絕** | 安裝在 Windows 上很脆弱，轉場其實也來自 gl-transitions。 |
| Remotion | Remotion License（超過 3 人的公司要付費；禁止拷貝程式碼做衍生產品） | 很活躍 | 高（Chromium 渲染） | 高 | **拒絕** | 授權跟開源 skill 的散布方式衝突，而且依賴瀏覽器。 |
| Motion Canvas | MIT | 社群維護，活躍度普通 | 高（瀏覽器） | 高 | **拒絕引擎，可吸收 easing 程式碼（MIT）** | 適合手寫 TS 動畫，不適合 Python 管線。 |
| VapourSynth | LGPL-2.1 | 活躍 | 低（C 外掛） | 高（要另外安裝，外掛生態以 Windows 為主） | **之後** | 去交錯、降噪、QTGMC 這類修復用途才會用到，不是 GIF 工作室的核心。 |
| GStreamer | LGPL | 活躍 | 低 | 很高 | **拒絕** | 為串流設計，對離線剪輯來說太重。 |
| Blender VSE（bpy） | GPL（當外部程式呼叫就沒問題） | 活躍 | 高 | 高 | **之後（3D 標題、粒子才用）** | 安裝要好幾 GB，不適合作為預設。 |

結論：**numpy 繼續當主路徑**（可控、可測、跨平台）。只加兩個可選引擎：ffmpeg xfade（速度）和 skia-python（文字品質）。

來源：
- https://github.com/gl-transitions/gl-transitions
- https://github.com/mifi/editly
- https://www.npmjs.com/package/ffcreator
- https://www.remotion.dev/docs/license 、 https://github.com/remotion-dev/remotion/blob/main/LICENSE.md 、 https://www.remotion.dev/docs/license/faq
- https://github.com/motion-canvas/motion-canvas
- https://ffmpeg.org/ffmpeg-filters.html#xfade

## 2. 鏡頭／場景偵測

| 專案 | 授權 | CPU | 判定 | 理由 |
|---|---|---|---|---|
| PySceneDetect v0.7.x（2026-10 有新版） | BSD-3 | 很快 | **吸收演算法（AdaptiveDetector、ThresholdDetector）** | 我們已有自製方案。它的 AdaptiveDetector（以前後滾動平均做比值）對快速運鏡誤報少，ThresholdDetector 專抓淡入淡出，邏輯簡單可以直接移植，需保留 BSD 版權聲明。 |
| TransNetV2 | MIT（程式碼與權重） | 中（小型 3D CNN，CPU 上大約幾倍即時） | **可選引擎** | 對溶接、漸變這類軟轉場比 HSV 差分準很多，有 PyTorch port（`transnetv2-pytorch`，MIT）。 |
| AutoShot（CVPR 2023） | MIT（repo 標示） | 中 | **之後** | F1 比 TransNetV2 高，但權重放在百度網盤，取得和重現都困難，不適合自動下載。 |

來源：
- https://github.com/Breakthrough/PySceneDetect
- https://pypi.org/project/transnetv2-pytorch/
- https://github.com/wentaozhu/AutoShot 、 https://arxiv.org/abs/2304.06116

## 3. 移動主體的去背／分割（時間一致性）

| 專案 | 授權 | CPU 可行性 | 判定 | 理由 |
|---|---|---|---|---|
| BiRefNet／BiRefNet_lite（rembg） | MIT | lite 版 1024px 約每幀數秒；512 ONNX 會快很多 | **保留（單幀品質）** | 逐幀推論沒有時間記憶，頭髮邊緣和背景交界會閃。 |
| **自製時間穩定化**（DIS 光流 warp 上一幀 alpha，加信心加權 EMA，再加 guided filter） | 我們自己的 | 低 | **採用（現在）** | 用最低成本解決閃爍，可以拿 qa_media 量 alpha 的 temporal flicker（相鄰幀 alpha 差的中位數）。 |
| SAM 2／2.1（tiny 38.9M） | Apache-2.0（程式碼與權重） | 在 CPU 上偏慢：PyTorch 單張約 7 到 12 秒（Colab CPU，非 ONNX）；有社群做的 ONNX 影片版 | **可選引擎** | 遮罩追蹤的時間一致性最好，可以當「主體是誰」的追蹤器，再交給 BiRefNet 精修邊緣。建議 512 輸入、每 N 幀跑一次。 |
| SAM 3（2025-11） | Meta 自訂的 SAM License（可商用但有 AUP、轉散布條款） | 更重 | **之後** | 可以用文字提示概念（「紅衣服的人」），但授權不是 OSI 認可的開源授權，要另外評估。 |
| RobustVideoMatting | **GPL-3.0** | 快（MobileNetV3，CPU 可以接近即時） | **拒絕（只吸收概念）** | GPL 會把整個 skill 傳染成 GPL。它的 recurrent state（ConvGRU）概念可以用前面的光流穩定化取代。 |
| MatAnyone／MatAnyone 2 | **NTU S-Lab License 1.0（非商用）** | 重 | **拒絕** | 品質目前是 SOTA，但不能商用（Beeble 是另外簽約授權）。 |
| BRIA VRMBG-3.0 | 商用需另簽 BRIA 協議 | — | **拒絕** | gated 模型，不是開放授權。 |

來源：
- https://github.com/ZhengPeng7/BiRefNet 、 https://huggingface.co/shozebDev/birefnet-lite-512-onnx
- https://github.com/facebookresearch/sam2 、 https://huggingface.co/vietanhdev/segment-anything-2.1-onnx-models 、 https://zenn.dev/piment/articles/ee78e816e1d05b
- https://roboflow.com/model-licenses/segment-anything-3
- https://github.com/PeterL1n/RobustVideoMatting （GPL-3.0）
- https://github.com/pq-yang/MatAnyone 、 https://pq-yang.github.io/projects/MatAnyone2 、 https://beeble.ai/models/matanyone

## 4. 節拍／段落分析

| 專案 | 授權 | 判定 | 理由 |
|---|---|---|---|
| Beat This!（CPJKU） | MIT（程式碼與權重；small 模型約 8.1MB） | **保留** | 拍點與重拍（downbeat）都是 SOTA。注意：**DBN 後處理要靠 madmom，不要啟用**。 |
| librosa | ISC | **採用（現在）：段落切分** | 用 recurrence matrix 加 Foote novelty，或用 `librosa.segment.agglomerative` 做段落邊界與能量曲線（找 drop、build-up）。純 CPU、輕量。 |
| All-In-One（mir-aidj/allin1） | 程式碼 MIT；依賴 madmom（模型檔 CC BY-NC-SA）、NATTEN、demucs | **之後／可選引擎** | 一次輸出 bpm、beats、downbeats，以及 intro／verse／chorus／bridge 標籤，是最貼近需求的工具。但 NATTEN 在 Windows 要自己編譯，madmom 也有 Python 3.12 相容性問題。權重授權沒有另外說明，視同 MIT 但未證實。 |
| madmom | 程式碼 BSD；**模型和資料檔 CC BY-NC-SA 4.0** | **拒絕（直接依賴）** | 用了它的預訓練模型就不能商用。 |
| Essentia | **AGPL-3.0**（商用要另外付費授權） | **拒絕** | 授權不相容。 |

來源：
- https://github.com/CPJKU/beat_this
- https://github.com/mir-aidj/all-in-one 、 https://pypi.org/project/all-in-one-mps/
- https://github.com/craffel/madmom/blob/develop/LICENSE （與上游 CPJKU/madmom 相同的雙授權）
- https://essentia.upf.edu/licensing_information.html
- https://dfsg-new-queue.debian.org/reviews/python-librosa

## 5. 補幀（慢動作）

| 專案 | 授權 | CPU | 判定 | 理由 |
|---|---|---|---|---|
| RIFE v4.25 lite（Practical-RIFE） | MIT | 快（CPU 上 720p 大約每幀 0.1 到 0.5 秒） | **保留** | 速度和品質的平衡最好。 |
| FILM（Google） | Apache-2.0 | 慢（GPU 導向，CPU 慢好幾倍） | **之後（大位移的高品質模式）** | 大動作比 RIFE 好，但在 CPU 上不實際。 |
| GMFSS（Fortuna 等） | **未證實**（只在 SVFI、ComfyUI 等包裝裡看到） | 很重 | **拒絕** | 授權不明，偏向動畫，需要 GPU。 |
| DIS（OpenCV） | Apache-2.0 | 很快 | **保留** | 作為 fallback，也給第 3 節的 alpha 穩定化用。 |

來源：
- https://github.com/hzwer/Practical-RIFE
- https://github.com/google-research/frame-interpolation 、 https://arxiv.org/pdf/2202.04901
- https://www.runcomfy.com/comfyui-nodes/ComfyUI-Frame-Interpolation/GMFSS-Fortuna-VFI

## 6. 深度（2.5D）

| 模型 | 授權 | 判定 | 理由 |
|---|---|---|---|
| Depth Anything V2 Small | Apache-2.0（Base／Large／Giant 是 **CC-BY-NC-4.0**） | **保留（最輕量的預設）** | — |
| **Video Depth Anything Small**（28.4M，含 metric 版） | Apache-2.0（Base、Large 是 CC-BY-NC） | **採用：影片視差** | 有時間一致性，逐幀跑 DA2 的深度抖動問題會消失。有實驗性的串流模式（一次處理一幀，品質略降）。A100 上 9ms，CPU 估計每幀數百毫秒。需要自己匯出 ONNX，或用 PyTorch CPU 跑。 |
| Depth Anything 3 Small（0.08B）／Base（0.12B） | **Apache-2.0**（Large、Giant 是 CC BY-NC） | **可選引擎（單張圖品質升級）** | 2025-11 發布。Base 也是 Apache，等於拿到比 DA2 Small 更好的可商用模型。社群有 ONNX（SpatialHub）。 |

**硬規則**：模型下載器要做 allowlist，只允許 `*-Small` 與 `da3-base`，在程式層面擋掉 NC 權重。

來源：
- https://github.com/DepthAnything/Depth-Anything-V2
- https://github.com/DepthAnything/Video-Depth-Anything 、 https://huggingface.co/depth-anything/Metric-Video-Depth-Anything-Small
- https://huggingface.co/depth-anything/da3-small 、 https://pypi.org/project/depth-anything-3/ 、 https://huggingface.co/SpatialHub/depth-anything-3-onnx

## 7. 自動重新構圖（Auto-reframe）

| 專案 | 授權 | 判定 | 理由 |
|---|---|---|---|
| Google AutoFlip（MediaPipe） | Apache-2.0 | **拒絕（直接用），吸收概念** | 已經沒有在維護，C++／Bazel 建置太重。它的「每個 scene 選靜止、平移或追蹤策略」概念值得照抄。 |
| pyautoflip | PyPI 上的 Python 重寫版（授權未證實） | **之後** | 依賴 UNISAL 顯著性模型加人臉偵測，維護狀況不明。 |
| **自製方案**：主體框（BiRefNet、SAM 遮罩質心，或 OpenCV YuNet 人臉偵測）→ 每個 shot 選策略 → 用 One-Euro／臨界阻尼平滑 crop 路徑 | 我們自己的 | **採用（現在）** | 輸出直式 9:16 與 1:1 GIF 時剛好用得到。 |

來源：https://research.google/blog/autoflip-an-open-source-framework-for-intelligent-video-reframing/ 、 https://pypi.org/project/pyautoflip/

## 8. 鏡頭美學／品質評分（CPU、寬鬆授權）

| 專案 | 授權 | CPU | 判定 | 理由 |
|---|---|---|---|---|
| pyiqa（IQA-PyTorch，內含 MUSIQ、NIMA、CLIP-IQA 等） | **NTU S-Lab + CC BY-NC-SA 4.0** | — | **拒絕** | 非商用。 |
| DOVER／DOVER-Mobile | repo 裡同時有 `LICENSE` 和 `S-Lab-LICENSE`（**未證實，視為非商用**） | Mobile 每支影片 1.4 秒 | **拒絕（除非確認是 MIT）** | 美學與技術分數拆開這個概念值得吸收：我們的 shot card 應該分兩欄。 |
| Q-Align／OneAlign | 7B LMM | 不可行 | **拒絕** | CPU 跑不動。 |
| MUSIQ（Google 原版） | Apache-2.0（TF 版） | 中 | **之後** | 要自己轉成 ONNX，而且要避免使用 pyiqa 的權重。 |
| LAION improved aesthetic predictor（CLIP ViT-L/14 + MLP） | mirror 標 Apache-2.0（**未證實**）；CLIP 權重是 MIT | 每幀約 0.5 到 1 秒 | **可選引擎** | 只對每個 shot 的 1 到 3 張代表幀打分，成本可以接受。 |
| **實測指標**（清晰度 Laplacian、曝光直方圖、雜訊、運動量、構圖三分法、人臉大小） | 我們自己的 | 極低 | **保留為主力** | 可解釋，也可以寫成 lint 規則。 |

來源：
- https://github.com/chaofengc/IQA-PyTorch 、 https://pypi.org/project/pyiqa/0.1.13
- https://github.com/VQAssessment/DOVER
- https://github.com/christophschuhmann/improved-aesthetic-predictor 、 https://gitee.com/young_chiang/improved-aesthetic-predictor

## 9. 用 VLM 寫鏡頭描述 vs. 讓 agent 看 contact sheet

| 選項 | 授權 | 判定 | 理由 |
|---|---|---|---|
| Agent（Claude、Codex）看 contact sheet 加實測數據 | — | **保留為預設** | 驅動端本身就是頂級 VLM，不必另外安裝。contact sheet 上每格疊時間碼和 shot id，就能直接寫進 shot card。 |
| Qwen3-VL 2B／4B Instruct（GGUF，llama.cpp 從 2025-10 開始支援） | Apache-2.0（第三方來源確認，以官方卡為準） | **可選引擎（離線、批次、無 agent 的 CLI 模式）** | 4B Q4 在 CPU 上每張圖約數秒到十幾秒，適合大量素材的預先標註。 |
| InternVL 系列 | 程式碼 MIT，但部分權重受 LLM 底座授權限制 | **之後** | 授權要逐個模型確認。 |

來源：
- https://unsloth.ai/docs/models/qwen3-vl-how-to-run-and-fine-tune
- https://huggingface.co/bartowski/Qwen_Qwen3-VL-4B-Instruct-GGUF
- https://docs.voxel51.com/model_zoo/models/Qwen_Qwen3_VL_2B_Instruct.html

## 10. 字幕與文字動畫

| 專案 | 授權 | 判定 | 理由 |
|---|---|---|---|
| faster-whisper（`word_timestamps=True`）+ Whisper 權重（MIT） | MIT | **採用（現在）** | CPU int8 實用，逐字時間精度大約 ±50 到 150ms，做 karaoke 式逐字高亮足夠。 |
| WhisperX（wav2vec2 強制對齊） | BSD-2（diarization 用的 pyannote community-1 是 CC-BY-4.0；alignment 模型授權各語言不同） | **可選引擎** | 逐字邊界更準，支援 CPU int8。缺點是相依很重（torch、torchaudio），而且中文對齊模型要另外找。 |
| 動態文字（kinetic typography）函式庫 | Python 生態沒有成熟又寬鬆授權的函式庫 | **自製** | 用 skia-python 或 Pillow 逐字排版，配上 easing 與 spring 預設組：pop、typewriter、slide-up、wave、highlight-sweep。 |

來源：https://github.com/m-bain/whisperX 、 https://github.com/SYSTRAN/faster-whisper

## 11. 代理式剪輯論文（2024 到 2026）與評估方法

| 論文 | 程式碼 | 評估方法（可借鏡的部分） |
|---|---|---|
| **LAVE**（IUI 2024，arXiv 2402.10294） | 沒有公開 | 8 人使用者研究（新手加熟手），看感知、創造力、共創感。屬於定性評估。 |
| **VideoAgent**（ECCV 2024，2403.11481） | github.com/YueFan1014/VideoAgent（授權未標示 → 只吸收概念） | 長影片 QA 準確率。概念上可以學：結構化記憶（時間事件描述 + 物件追蹤狀態），對應我們的 shot card 索引。 |
| **EditDuet**（SIGGRAPH 2025，Adobe，2509.10761） | 未確認有公開程式碼 | Editor 和 Critic 兩個 agent。**用 VLM 當評審做自動評估，並跟人類偏好做比較**，驗證 LLM-as-judge 和人類的一致性。 |
| **Prompt-Driven Agentic Video Editing**（2509.16811） | 沒有公開 | 超過 400 支影片：**專家評分、QA 測驗（看摘要影片能不能答對劇情問題）、偏好研究**。重點是先建立帶時間戳的語意索引，再做規劃。 |
| **CutClaw**（2603.29664，GVCLab） | github.com/GVCLab/CutClaw（論文是 CC BY-NC-SA，程式碼授權未確認 → 只吸收概念） | Playwriter、Editor、Reviewer 三個 agent，把場景跟音樂結構對齊。指標分三軸：**視覺品質、指令遵循、節奏對齊**（剪點和拍點的距離）。 |

**我們評估方式的修正建議**：
(1) 盲測兩兩比較之外，再加**自動節奏對齊分數**：剪點到最近 beat 或 downbeat 的誤差中位數，`qa_media` 可以直接量。
(2) 加 **指令遵循檢查表**：把 brief 拆成可驗證的條目，由 agent 逐條勾選。
(3) 比照 EditDuet，定期抽樣人類判斷，**校準 agent 評審跟人的一致率**。
(4) 分數拆成「美學」和「技術」兩欄（DOVER 的概念）。

來源：
- https://arxiv.org/abs/2402.10294 、 https://www.dgp.toronto.edu/~bryanw/lave/
- https://arxiv.org/abs/2403.11481
- https://arxiv.org/abs/2509.10761 、 https://research.adobe.com/publication/editduet-a-multi-agent-system-for-video-non-linear-editing
- https://arxiv.org/abs/2509.16811
- https://arxiv.org/abs/2603.29664 、 https://github.com/GVCLab/CutClaw

---

## 12. 可吸收清單（程式碼／素材可合法移植進 video-gif-studio）

原則：**MIT、BSD、Apache-2.0、ISC、Unlicense、CC0 可以吸收程式碼或素材**，但要保留版權聲明，統一放在 `THIRD_PARTY_NOTICES.md`。Apache-2.0 還要保留 NOTICE 檔，並註明有修改。**GPL、AGPL、NC、ShareAlike，以及沒有授權的專案，只能吸收概念**，不得貼上程式碼。

### 前 10 名（依價值 ÷ 成本排序）

| # | 來源 | 吸收什麼 | 授權與義務 | 價值 | 成本 |
|---|---|---|---|---|---|
| 1 | **gl-transitions** | 100 多個轉場的 GLSL `transition(uv)` 數學，改寫成 numpy 向量化函式（先做大約 20 個常用的：crosswarp、directionalwarp、cube、doorway、wind、ripple、swirl、pixelize、dreamy、glitch、burn、circleopen、zoomblur 等） | 每個檔頭有 License 行，MIT（2 個是 BSD）。要逐一列出原作者 | 很高（轉場庫一次補齊） | 中（每個 0.5 到 2 小時，GLSL 函式要逐一對應） |
| 2 | **Robert Penner easing**（或 easings.net 的公式） | 30 個 easing 函式（quad 到 expo、back、elastic、bounce 的 in／out／inOut） | BSD-3（也有 MIT 版）。保留 2001 年的版權聲明 | 高 | 很低（約半天） |
| 3 | **auto-editor** | 依音量（dB）和動態閾值找出靜音段與靜止段的邏輯，包括 margin 和最小片段長度 | **Unlicense（公有領域）**，沒有義務（建議致謝） | 高（素材預剪、去掉沒內容的片段） | 低 |
| 4 | **PySceneDetect** | AdaptiveDetector（滾動比值）與 ThresholdDetector（淡入淡出）的演算法 | BSD-3，保留版權聲明 | 中高（降低快速運鏡誤報） | 低 |
| 5 | **Kenney 音效包**（Interface Sounds 100 個、UI Audio 50 個、Impact Sounds） | 點擊、彈出、撞擊等 SFX 當成程序化 SFX 的「真實樣本層」，或作為合成時的參考 | **CC0**，沒有義務 | 中高 | 很低（注意 repo 體積，可以按需下載） |
| 6 | **Motion Canvas** | easing 與 tween 工具函式（TS 改寫成 Python），以及 spring、`linear` 插值的參數化方式 | MIT，保留版權聲明 | 中 | 低 |
| 7 | **ffmpeg xfade** 的轉場公式 | xfade 的 50 多種轉場（wipe、slide、circlecrop、radial、smooth*、hl／vu-wind 等）邏輯，用來對齊命名，並作為 numpy 版的對照組 | ffmpeg 是 LGPL-2.1+（部分是 GPL）。**不要拷貝 C 程式碼**，只依公式描述自行實作，或在執行時呼叫外部 ffmpeg | 中 | 低到中 |
| 8 | **Spectral Film LUT（JanLohse/spectral_film_lut）** | 程式碼是 MIT，可以吸收它生成底片模擬 LUT 的程式，自己產生 .cube | 軟體 MIT。它附的 LUT 本身要再確認。**spektrafilm 與 RawTherapee 的 LUT 是 CC BY-SA → 不要內建** | 中高（風格包的核心） | 中 |
| 9 | **editly** | JSON 剪輯規格的欄位設計（clips、layers、transition、audio ducking、Ken Burns 參數）。程式碼是 MIT，可參考 ducking 與 crossfade 的實作 | MIT | 中（storyboard JSON schema 可以借鏡） | 低 |
| 10 | **win4r/video-director** | 已經吸收（qa_media） | MIT，已列出 | — | 完成 |

### 其他評估過的項目

| 來源 | 結論 | 原因 |
|---|---|---|
| Remotion 的 `spring()`、`interpolate()`、transitions | **不得拷貝程式碼**；改依阻尼諧振子公式（質量、剛性、阻尼）自行實作 | Remotion License 明文禁止拷貝或修改它的程式碼去做衍生產品 |
| FFCreator 轉場 | 不需要另外吸收 | 本身就是 gl-transitions，用第 1 項即可 |
| Q-DDL 800+ LUTs | **可選擇性收錄**，但要附署名 | CC BY 4.0（不是 CC0），必須署名。建議不內建，提供下載腳本加署名檔就好 |
| Sinewavekid Film LUTs | **拒絕** | 禁止轉散布 |
| rea-video | **只吸收概念** | 沒有授權 |
| RobustVideoMatting、MatAnyone、madmom 模型、Essentia、pyiqa、DOVER | **只吸收概念** | GPL、NC、AGPL 或 S-Lab |
| CutClaw、VideoAgent 程式碼 | **只吸收概念** | 授權未確認（CutClaw 論文是 CC BY-NC-SA） |
| 底片顆粒、雜訊素材 | **程序化生成**（numpy 多尺度高斯加 Poisson 顆粒，依亮度調整強度），不另外收素材 | 找不到夠清楚的 CC0 grain plate 來源，自己生成反而更可控 |

來源：
- https://github.com/gl-transitions/gl-transitions
- https://gist.github.com/marioluan/5499930 （Penner BSD）、 https://fujifilm-dsc.com/en/manual/gfx-eterna-55/technical_notes/oss/penner_easing_equations.html
- https://github.com/WyattBlue/auto-editor
- https://github.com/Breakthrough/PySceneDetect
- https://opengameart.org/content/interface-sounds 、 https://github.com/Calinou/kenney-interface-sounds 、 https://kenney.nl/assets
- https://github.com/motion-canvas/motion-canvas
- https://ffmpeg.org/ffmpeg-filters.html#xfade
- https://huggingface.co/Norton0924/OpenSourceLuts 、 https://github.com/JanLohse/spectral_film_lut 、 https://github.com/andreavolpato/spektrafilm
- https://cgpress.org/archives/800-free-luts.html
- https://github.com/mifi/editly
- https://www.remotion.dev/docs/license 、 https://github.com/remotion-dev/remotion/blob/main/LICENSE.md

---

## 附註：本次沒有拿到一手 LICENSE 的項目（落地前必須再查）

- DOVER（`LICENSE` 和 `S-Lab-LICENSE` 兩個檔的內容）
- LAION improved-aesthetic-predictor（上游 repo 的 LICENSE）
- GMFSS
- All-In-One 權重
- pyautoflip
- Qwen3-VL 官方模型卡
- CutClaw、VideoAgent 的 repo 授權
- JanLohse/spectral_film_lut 附帶的 LUT 檔
