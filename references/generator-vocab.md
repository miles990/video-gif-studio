# Generator-facing vocabulary (register phrases, terms, push+restraint pairs)

Read when writing a prompt for a video or image generator, after the motion or image plan is set. This file is the generator layer: what a model is reported to respond to, with evidence levels. It is not a style guide.

**How to use (rules first; catalogue below)**

1. **Structure beats vocabulary.** The best-evidenced patterns are second-stamped timelines ("0–2s real-time → 2–6s slow motion → 6–8s real-time"), "X, not Y" disambiguators ("true dolly, not a zoom"; "head-only nod, not a bow") and body-part isolation ("only the head dips ~10°, shoulders stay still").
2. **Pair every push with a restraint.** Escalation terms (ornament, detail, blur, chase cam, speed ramp) need a named partner that keeps the result legible (negative space, hierarchy, controlled complexity, crisp held key pose, locked horizon). See the pairing table. Own A/B, 2026-11-07, GPT image, n=2 per arm, blind cross-family judge: push-only cards ranked last, with legibility 2 and 1 out of 5 and clutter 5 and 5. The same push terms paired with restraint terms produced the top-ranked card and beat push-only on legibility in 4 of 4 cross pairs. Restraint terms alone scored about the same as the plain prompt. Pushes also cost identity: 4 out of 5, against 5 out of 5 for the plain prompt. Add an identity anchor, and ask for no rendered text unless text is required, because 2 of 8 cards had glyph defects.
3. **Do not stack softeners.** "gently, subtle, slowly, soft" together make motion slow and limp. State the amplitude instead ("~10°", "two quick nods").
4. **Style boosters cost fidelity.** Add an identity anchor whenever you add a register or booster: "same facial features, proportions, costume; do not redesign".
5. **A register sentence is optional and unverified.** One genre sentence (e.g. anime chat-sticker loop, Live2D-style locked-off framing, pose-to-pose key acting, overlapping action on hair) improved acting (3/3 pairs), loop seam (3/3) and readability (2/3) on Grok, but did not fix wrong action semantics (n=3 pairs, 2026-11-07, Grok Imagine, blind cross-family judge). Never let a register contradict a hard constraint: a chase cam or strong blur conflicts with a locked loop sticker.
6. **Evidence levels:** A = controlled comparison or paper; B = listed in an official model guide; C = community before/after; D = anecdote; U = no source (candidate only). Promote a term only after an A/B on this skill's own outputs; record the model and date, because phrases drift across model updates.
7. **Re-test after model updates.** A restraint phrase that worked before an update can change meaning after it.

---


Scope extended 2026-11-07 to image generators: GPT image, Midjourney, Nano Banana / Gemini image, FLUX, Seedream and NovelAI / PixAI. See the **Image** section near the end.

Harvested 2026-11-07 for the register-anchor A/B (pre-registered A/B, 2026-11-07). The audience is the **generator**: Grok Imagine, Kling, Veo, Hailuo/MiniMax, Seedance, Wan and Runway. Builder and judge vocabulary is in `wow/references/vocab/` and `video-gif-studio/references/blank-page-vocabulary.md`, and this file does not repeat it.

## Evidence key

- **A**: a paper or a controlled comparison.
- **B**: an official model guide or official docs list the term. B means the vendor says the model reads the term, not that the term works.
- **C**: a community post with visible output, plus a stated before/after or a stated success rate.
- **D**: anecdote, vendor SEO, or a template with no shown result.
- **U**: no source found. The term is a craft-vocabulary candidate only, listed so it can be A/B tested. Do not cite it as known to work.
- **(snip)**: seen only in a search-result snippet. The page itself was not opened.

## Honest bottom line

- **No study tests register phrases.** No paper, and no community post with a real A/B, tests whether a register phrase such as "3A action-game chase cam" changes motion. The source tweet is **D**: 187 likes, no media, and one reply saying "the weight of the turn is clearly heavier".
- **The papers cover basic camera moves only.** That is pan, tilt, zoom, orbit and static. They show that models follow text camera prompts only partially.
  - VBench-2.0 Camera Motion scores (**A**, [VB2]): Kling 1.6 61.7%, HunyuanVideo 34.0%, CogVideoX-1.5 33.3%, Sora 27.2%.
  - DynamicEval (**A**, [DYN]) reports that some models output **static** video despite explicit camera prompts.
  - AnimationBench (**A**, [ANB]) tests Seedance 2.0, Kling 2.6, Veo 3.1, Sora2-Pro and Wan 2.2. It finds that exaggerated facial expression is error-prone and that expressiveness is weak. Anticipation and follow-through are scored, but no per-model numbers are quoted.
  - Directly relevant to our pout and tilt failures: generators are measurably weak at expression and acting, not just at camera.
- **Official guides (B) are camera-and-lens heavy.** Veo's guide is the richest: whip pan, dolly zoom, rack focus, slow-motion, time-lapse, claymation, stop-motion, Pixar-like, "a subtle nod". MiniMax has 15 bracket commands, including `[Shake]` and `[Static shot]`.
- **No official guide found mentions any animation-timing term.** That covers on twos, smear, hit-stop, anticipation and 作画. Every anime and timing term below is **D** or **U**.
- **The strongest community evidence (C) is about structure, not vocabulary.** Two patterns recur:
  - second-stamped timelines, as in the speed ramp in [KC35];
  - "X, not Y" disambiguators, such as "true dolly, not a zoom" in [PIC].

---

## Top 10 to A/B first: Video

The image top 10 is in the **Image** section below.

Rows #11–15 in this table are runners-up kept for reference. The video top 10 is #1–10.

Ranking = evidence × likely impact on our five failures:

- **F1**: slow and floaty motion.
- **F2**: wrong action semantics.
- **F3**: camera drift in locked shots.
- **F4**: mushy impacts.
- **F5**: broken loops.

Weighting is for **anime chat-sticker loops on Grok**.

| # | Phrase to test | Fixes | Ev | Why it ranks here | Sticker conflict |
|---|---|---|---|---|---|
| 1 | **"locked-off camera, the camera remains perfectly still; no pan, no tilt, no zoom, no drift"** (EN). 锁定机位/固定机位，镜头完全静止 / 鎖定機位 / カメラ固定、カメラ移動なし | F3 | B + C | Runway Academy gives "The locked-off camera remains perfectly still" verbatim [RWA]. Veo lists "Static shot (or fixed)" [VEO], MiniMax has `[Static shot]` [MMX], and Kling has "Static camera" [KLC]. Adobe users report that drift persists even with negatives [ADB]: treat it as a mitigation, not a fix. | none: this is the sticker's base layer |
| 2 | **Return-to-key-pose loop clause:** "end in exactly the same pose, expression, gaze and head angle as the first frame so the loop is seamless". JA: 最後は…@image1と完全に同じ開始状態へ戻し、ループが継ぎ目なく繋がること | F5 | B + C | Runway: "start and end on the exact same frame to create a perfect loop" [RWA]. Grok loop-mode idle prompts with output video [ERIS]. Caveat: identical start and end frames can make the model render "a statue" (D) [REDL]. | none |
| 3 | **"a subtle nod" / exact micro-action verb plus amplitude** (Veo's own example list) | F2 | B | Veo lists "a subtle nod", "eyes blinking slowly" and "fingers tapping" as subtle actions [VEO]. Our nod turned into a whole-torso bow, so test the verbatim official phrasing plus body-part isolation: "only the head dips ~10°, shoulders stay still". | none |
| 4 | **Second-stamped speed timeline:** "0–2s real-time → 2–6s EXTREME SLOW MOTION (syrupy) → 6–8s back to real-time". Writing only "slow motion" makes the whole clip slow. | F1 | C + B | Seedance 2.5 with output, and the author says that without the stamps it "freezes / stays slow the whole way" [KC35]. Veo lists slow-motion and time-lapse as pacing terms [VEO]. | medium: a ramp inside a 3 s loop must ramp back |
| 5 | **"animated on twos at 12 fps, each drawing held two frames, visible pose-to-pose timing, distinct key drawings, no smooth in-between interpolation, no CGI smoothness"** | F1, anime look | D (output shown, no A/B) | Higgsfield Originals open-sourced the Seedance 2.0 prompt, and the posted output is stepped [HGO]. This attacks the "smooth AI float" directly. | low. Stepped motion can also hide loop seams. Watch for the generator doubling frames and judder. |
| 6 | **Hit-stop: "freeze frame on impact for 2 frames, bright flash, subtle screen shake, then snap back to normal speed"** | F4 | D | Vendor fight guides only [S2P][BPX]. MiniMax's official `[Shake]` (B) [MMX] is the nearest official primitive. | medium: use only on a "punch" or "surprise" sticker beat |
| 7 | **Named principles: "crisp anticipation, then the action, then follow-through and overlapping action on hair and ribbons; slow in / slow out"** | F1, F2 | D (generation); A (measurement) | AnimationBench scores anticipation and follow-through, and models are weak at them [ANB]. HGO lists the 12 principles in its style line [HGO]. This is the register sentence tested on 2026-11-07 (acting and loop improved, semantics not). | none |
| 8 | **The tweet sentence: "3A动作游戏惯性追尾机位，强动态模糊+TimeRamp"** | F1, F4 | D | The claim [GNL] and one reply anecdote [GNL-thread]. A reply notes that "machine position and blur raise the sense of speed, but impact force still relies on timing and hit pauses". | **high**: chase cam plus strong blur contradicts a locked sticker. Test on action clips, not stickers. |
| 9 | **"Single continuous shot, no cuts"** plus a per-second beat list (Grok) | F2, F5 | B + D | Runway lists "continuous, seamless shot" [RWA]. A Grok 1.5 example with output pairs it with a locked-off camera [AIW]. | none |
| 10 | **"limited animation frame rate (12fps feel)"**, 90s-OVA register | F1 | D | Seedance 2.5 anime guide, no shown A/B [ATA] | low |
| 11 | **"impact frames flashing, intense speed lines"** (shōnen register). 冲击帧 / 衝擊幀 / インパクトフレーム、集中線 | F4 | D | [ATA][ATF](snip). Kling's official anime blog does **not** list these [KLA]. | medium: the flash frame breaks a loop if it lands at the seam |
| 12 | **"crash zoom"** (snap zoom into the face, then whip back out) | F4, F1 | B + C | Runway Academy has "aggressive crash zoom" [RWA]. Kling 4 posts with output [BAS][ICL]. | high in a loop unless the clip zooms back out |
| 13 | **"whip pan"** | F1 | B | Veo: "whip pan from one arguing character to another" [VEO]. Runway: "Whip pan to … Whip pan back" [RWA]. | high |
| 14 | **"handheld, natural camera shake"** versus its negation **"never handheld, never gimbal drift"** | F3 (negated), F1 | B | Veo has "Handheld or shaky cam" [VEO], Runway has "Natural camera shake" [RWA], and MiniMax has `[Shake]` [MMX]. Most useful negated in locked shots. | high when positive |
| 15 | **"cinematic motion blur" / "strong motion blur"**. 强动态模糊 / 強動態模糊 / 強いモーションブラー | F1 | D | Grok orbit recipe [GRL], vendor blog [HGM], the tweet [GNL]. No guide or paper. | medium: blur smears line art, which hurts the 128 px legibility of anime stickers |

**Suggested test order for the sticker A/B:**

1. Arm B = #1 + #2 + #3 + #7. That is locked-off camera, return-to-key loop clause, official micro-action phrasing, and the named principles.
2. Add #5 (on twos) as a third arm.
3. Test the tweet sentence (#8) only on a separate action clip, because it conflicts by design with a locked loop.

---

## Domain 1: Camera rigs and moves

| Term (EN / 简 / 繁 / 日) | Visible effect in output | Suits / conflicts | Ev | Source | Models reported |
|---|---|---|---|---|---|
| Static shot, locked-off, tripod / 固定镜头、锁定机位、三脚架 / 固定鏡頭、鎖定機位 / 固定カメラ、据え置き | Frame does not translate, rotate or zoom | Stickers, idles, product, ASMR. Conflicts with any action register. | B, C | [VEO][RWA][MMX][KLC]; drift persists [ADB]; negatives list [VID][PIP] | Veo, Runway, MiniMax, Kling, Vidu, Firefly (drift) |
| Pan L/R / 摇镜（左/右摇）/ 搖鏡 / パン | Rotation in place, horizontal | Reveals, landscapes. Conflicts with loops. | A, B | [VEO][MMX][KLC]; VBench-2.0 measures pan [VB2] | All; VB2 scores Kling 1.6 best |
| Tilt U/D / 俯仰摇（上摇/下摇）/ 上下搖 / ティルト | Vertical rotation in place | Reveals height | A, B | [VEO][MMX][VB2] | All |
| Dolly / push in / pull out / 推镜、拉镜 / 推軌、推拉 / ドリーイン・アウト、トラックアップ | Physical move with **parallax**. Models often substitute a zoom. | Emphasis, isolation | B, C | [VEO][MMX "Push in/Pull out"][KLC]; ~80% true dolly, ~95% with "camera physically moves forward, not zoom, parallax visible" [PIC] | Veo 3.1 (PIC), Kling, MiniMax, Seedance 1.0 Pro [BPS](snip) |
| Truck L/R / 横移 / 橫移 / トラック（横移動） | Lateral move, subject passes | Walking, follow | B | [VEO][MMX] | Veo, MiniMax |
| Pedestal U/D / 升降 / 升降 / ペデスタル | Vertical translation | Reveal height | B | [VEO][MMX] | Veo, MiniMax |
| Zoom in/out / 变焦推拉 / 變焦 / ズーム | Field of view changes, no parallax | Kling's guide lists "zoom" among words to **avoid** [KLC] | A, B | [VEO][MMX][VB2] | All |
| Crash zoom / snap zoom / 急推变焦、闪推 / 急推 / クラッシュズーム | Violent fast zoom into a face or object; comic and action punctuation | Action, comedy, reaction stickers if it returns | B, C | [RWA]; Kling 4 crash zoom + time-freeze + whip in one shot, with output [BAS][ICL] | Runway Gen-4.5, Kling 4 |
| Whip pan / 甩镜、急摇 / 甩鏡 / ホイップパン（素早いパン） | Motion-blurred snap between subjects | Comedy, action, transitions. Conflicts with loops. | B | [VEO][RWA][HGF] preset | Veo, Runway, Higgsfield |
| Dolly zoom, Vertigo effect / 希区柯克变焦、滑动变焦 / 滑動變焦 / ドリーズーム（めまいショット） | Subject holds size while the background stretches | Shock or dread beat | B, D | [VEO]; reported success varies from ~22% to ~80% (D, untraceable blogs, see search notes) | Veo |
| Arc / orbit / 环绕运镜 / 環繞 / 回り込み、オービット | Camera circles the subject | Hero reveal. Conflicts with locked. | A, B, C | [VEO "Arc shot"][KLC "Orbit slowly"]; VB2 adds orbit; "360 orbit" often degrades into a pan [PIC] | Veo 3.1 (partial), Kling, Grok [GRL] |
| Crane shot / 摇臂镜头 / 搖臂 / クレーンショット | Rising and sweeping reveal | Epic establishing | B | [VEO][HGF]. Bare "Crane", "Dolly" or "Aerial" words may trip Seedance moderation; use full phrases (D) [SKD](snip) | Veo, Higgsfield, Seedance |
| Aerial / drone shot / 航拍 / 空拍 / ドローン空撮 | Sweeping flyover | Landscape | B, C | [VEO]; "Aerial" beats "drone shot" in Veo 3.1 tests [PIC] | Veo |
| FPV drone, close-range orbit / 穿越机镜头、贴身环绕 / 穿越機 / FPVドローン | High-speed weaving between and around fighters | Fight PV. Conflicts with stickers. | D | Seedance fight prompts with output [LAN2]; MiniMax H3 "Close-Range Orbital Shot" plus foreground-occlusion transition [LOV](snip) | Seedance 2.x, MiniMax H3 |
| Tracking / follow / 跟拍 / 跟拍 / 追従ショット、フォロー | Camera follows a moving subject | Walks, chases. Note: "camera follows/watches" wording *causes* drift in locked shots [PIP]. | B | [MMX "Tracking shot"][KLC][VEO] | MiniMax, Kling, Veo |
| Chase cam / inertial follow / 惯性追尾机位 / 慣性追尾機位 / 慣性追従カメラ（三人称追従） | Camera lags and overshoots behind the character; turns feel weighty | 3A action, fights. Conflicts with locked stickers. | D | [GNL] + reply "转身那一下的重量感很明显" (the weight of the turn is clearly heavier) | Unnamed ("AI 打斗视频", AI fight video) |
| Snorricam / body-mount / 身体绑定摄影 / 身體綁定攝影 / ボディマウント | Subject fixed in frame while the world swings | Panic, drunk. Conflicts with locked. | B* | Higgsfield UI preset, not a prompt word [HGF] | Higgsfield (preset) |
| Handheld / shaky cam / 手持 / 手持 / 手持ち、手ブレ | Organic jitter and reframing | Documentary, chaos. Conflicts with locked. Negate it for stickers. | B | [VEO][RWA "Natural camera shake"][MMX `[Shake]`] | Veo, Runway, MiniMax |
| Gimbal / Steadicam / 稳定器 / 穩定器 / ジンバル、ステディカム | Floating smooth move | Fashion, glide. Can *add* float, which is the opposite of punch. | D | Named as natural-language only, not an official MiniMax command (snip) | — |
| POV / 主观镜头 / 主觀鏡頭 / 主観ショット | First-person | Rides, horror | B | [VEO] | Veo |
| Dutch angle / 斜角镜头 / 斜角 / ダッチアングル | Canted horizon | Unease | B, C | [VEO]; intent read in ~65% of tests, degree unpredictable [PIC] | Veo 3.1 |

## Domain 2: Shutter and time

| Term | Visible effect | Suits / conflicts | Ev | Source | Models |
|---|---|---|---|---|---|
| Slow-motion / 慢动作 / 慢動作 / スローモーション | Whole clip slows unless time-boxed | Impact detail. Floaty risk. | B, C | [VEO pacing]; must be second-stamped or it stays slow for the whole clip [KC35] | Veo, Seedance 2.5 |
| Speed ramp / TimeRamp / 变速、升格降格切换 / 變速 / スピードランプ | Real-time → slow → real-time inside one shot | Action, fashion. A loop must ramp back. | C, D | [KC35] stamped recipe with output; "正常速度与高帧率慢动作（Speed Ramp）自然混合" (normal speed and high-frame-rate slow motion blended naturally) [CIA](snip); [GNL] | Seedance 2.5 |
| Time-lapse / 延时摄影 / 縮時攝影 / タイムラプス | Compressed long duration | Process, sky. Conflicts with acting. | B | [VEO] | Veo |
| Freeze frame / time-freeze / 定格、时间冻结 / 定格 / ストップモーション的静止（時間停止） | Drops and particles hang mid-air while the camera moves | Bullet-time beat | C | Kling 4 "time-freeze" with output [BAS][ICL] | Kling 4 |
| Bullet time / time-slice / 子弹时间 / 子彈時間 / バレットタイム | Frozen moment with an orbiting camera | Hero beat | B* | Higgsfield preset [HGF] | Higgsfield |
| Hit-stop / hitstop / 顿帧 / 頓幀、打擊停頓 / ヒットストップ | 2–4 frame hold at contact, then snap | Fights, punchy reactions | D | [BPX][S2P]; reply in [GNL-thread] | Seedance 2.0 (claimed) |
| Motion blur / 动态模糊 / 動態模糊 / モーションブラー | Streaked fast limbs | Speed. Hurts line-art legibility. | D | [GRL][HGM][GNL] | Grok (claimed) |
| Shutter angle 180° / 45° (staccato) / 快门角度 / 快門角度 / シャッター開角度 | 45° should give crisp, strobing, blur-free motion | Gritty combat | **U** | No source found on whether any generator reads numeric shutter angles | — |
| Undercranking / step printing / 降格、抽帧 / 抽格 / コマ落とし | Sped-up or stuttered motion | Retro action, HK action | **U** | No source | — |
| 24fps vs high frame rate / 24帧电影感 / 24格 / 24fps | Filmic cadence versus video smoothness | — | D | "24fps电影感" (24 fps film look) in Seedance fight prompts [LAN2]; "120fps … no slow motion" [YOU](snip) | Seedance |

## Domain 3: Animation acting and timing

| Term | Visible effect (intended) | Suits / conflicts | Ev | Source | Models |
|---|---|---|---|---|---|
| Animated on twos / 12fps / 一拍二 / 一拍二 / 2コマ打ち | Stepped cadence, each drawing held two frames | Hand-drawn anime, stickers | D | [HGO] with output | Seedance 2.0 |
| Pose-to-pose, distinct key drawings, no smooth in-betweens / 关键帧到关键帧 / 關鍵格 / ポーズトゥポーズ | Readable keys, no float | Stickers, gags | D | [HGO]. AnimationBench excludes pose-to-pose as unmeasurable [ANB] | Seedance 2.0 |
| Anticipation / 预备动作 / 預備動作 / 予備動作（ため） | Small counter-move before the action | Nods, jumps, hits | D (gen), A (measured) | [HGO]; scored as a dimension in [ANB] | Seven models in ANB, no per-model numbers quoted |
| Follow-through and overlapping action / 跟随与重叠动作 / 跟隨與重疊動作 / フォロースルー、オーバーラップ | Hair and ribbons settle after the body stops | Idles, stickers | D, A | [HGO][ANB] | Same |
| Slow in / slow out (ease) / 缓入缓出 / 漸入漸出 / スローイン・スローアウト | Acceleration curves | All | A (measured) | Measured with CoTracker peak/valley in [ANB] | Same |
| Squash and stretch / 挤压与拉伸 / 擠壓伸展 / スクワッシュ＆ストレッチ | Volume-preserving deformation | Cartoon, chibi | A (measured) | "Sora2-Pro and Kling2.6 show some deformation ability … significant gap" [ANB] | Sora2-Pro, Kling 2.6 |
| Exaggerated expression / 夸张表情 / 誇張表情 / 誇張表現 | Big readable face acting | Reaction stickers | A (weakness) | "Exaggerated facial expressions especially error-prone" [ANB]: this predicts our pout failure | Seven models |
| Smear frames / 拖影帧 / 拖影格 / スメア（オバケ） | Stretched in-between on fast moves | Snappy action | D | "dynamic motion smears" gallery prompt, no result [CAR](snip). Reddit: models "smear" by *accident* (snip) | Seedance (claimed) |
| Moving hold / 微动停格 / 微動停格 / ムービングホールド | Held pose with breath and hair life | Sticker end-pose | **U** | — | — |
| Line boil / 线条抖动 / 線條抖動 / 線のゆらぎ | Hand-drawn jitter | Hand-drawn look | D | "line jitter and boil between frames" [HGO] | Seedance 2.0 |
| Idle: breathing + blink + hair sway / 待机呼吸眨眼 / 待機 / 待機モーション（呼吸・瞬き・髪揺れ） | Subtle loopable life | Idle stickers. Too subtle can render a frozen image (Kling note). | D | [ERIS] Grok loop prompt with output; Magic Hour template [MH] | Grok, Kling |

## Domain 4: Anime and 作画 (sakuga) terms

The only anime terms in an official guide are Kling's style words: "clean anime-inspired linework", "cel-shaded color", "comic-style motion", "Japanese Anime style" and "high detail anime battle choreography" [KLA] (B). Veo lists "Japanese anime style" and "cel-shaded animation" [VEO] (B). None of the motion-specific Japanese terms appear in any guide.

| Term (JA / 简 / 繁 / EN) | Intended effect | Ev | Source | Note |
|---|---|---|---|---|
| 作画 / 作画（sakuga）/ 作畫 / sakuga | High-effort fluid action animation | D | "sakuga motion control", "sakuga animation" [ATA]; Seedance 2.5 "sakuga-inspired 2D manga effects" [IMH](snip) | Community note [BIM](snip): writing "anime sakuga" alone does nothing, the choreography text matters |
| インパクトフレーム / 冲击帧 / 衝擊幀 / impact frame | 1–2 inverted or high-contrast flash frames at contact | D | [ATA][ATF](snip); Vidu "single white flash with flat cel shading" (snip) | |
| 集中線・スピード線 / 速度线 / 速度線 / speed lines | Radial or parallel streaks | D | [ATA] | |
| リミテッドアニメ / 有限动画 / 有限動畫 / limited animation (12fps feel) | Stepped, held drawings | D | [ATA] | |
| 止め絵 / 定格画 / 定格畫 / held still (tome-e) | Single held illustration with camera move or effects only | **U** | — | Cheap register worth testing for stickers |
| 中割り / 中间帧 / 中間格 / in-betweens | Smoothness between keys | **U** (negated form D) | "no smooth in-between interpolation" [HGO] | Use negated |
| 金田パース・金田ポーズ / 金田透视 / 金田透視 / Kanada pose / perspective | Extreme foreshortened pose, angular FX | **U** | No result mentions Kanada with any generator | |
| 一枚絵 / 一张画 / 一張畫 / single-illustration shot | Pan over one drawing | **U** | — | |
| 口パク / 口型 / 口型 / mouth flaps | 2–3 mouth shapes, not realistic lip-sync | **U** | — | Could counter over-real lip motion in stickers |
| 揺れもの / 摇摆物 / 搖擺物 / secondary dangles | Hair, ribbon, accessory sway | D (as "hair sways slightly") | [ERIS] "髪は全体を通して微かに揺れる" (the hair sways slightly throughout) | |
| 演出 / 演出 / 演出 / direction (enshutsu) | Whole-shot staging intent | **U** | — | |
| 日本のアニメ作画。手描きの繊細な線、平坦なセル塗り (JA) | Hand-drawn anime look | D | MiniMax H3 prompt with output [SOH] | Style anchor, not motion |
| Live2D-style idle / VTuber idle / Live2D 风待机 / Live2D風待機 | Puppet-warp parallax: head and body tilt on a fixed rig | **U** | A search for a Live2D prompt with any generator returned nothing | High-value candidate for stickers: names a "rig, not camera" motion family |
| 国漫热血 / 熱血國漫 / 「高完成度热血国漫 / 动漫电影感 / 超高能战斗PV感」 | Chinese-anime battle-PV register | D | [LAN1] Seedance 2.0 with output | Fight register |

## Domain 5: Game feel and 3A registers

| Term | Intended effect | Ev | Source | Conflict |
|---|---|---|---|---|
| 3A动作游戏惯性追尾机位 / 3A動作遊戲慣性追尾機位 / AAA action-game inertial chase cam / 3Aアクションゲームの慣性追従カメラ | Weighty third-person follow, overshoot on turns | D | [GNL] | Locked stickers |
| Hitstop + screen shake / 顿帧+震屏 / 頓幀+震屏 / ヒットストップ＋画面揺れ | Contact pause plus jolt | D (B for `[Shake]`) | [BPX][MMX] | Loop seam |
| Souls-like camera / 魂系镜头 / 魂系鏡頭 / ソウルライクのカメラ | Over-shoulder lock-on, heavy commits | **U** | — | — |
| Character-action camera (DMC/Bayonetta) / 角色动作游戏镜头 / キャラクターアクション | Wide, readable, stylish juggle | **U** | — | — |
| Fighting-game frame data look / 格斗游戏帧数据感 / 格鬥遊戲 / 格ゲーのフレーム感（発生・持続・硬直） | Startup, active, recovery readable as poses | **U** | — | Promising for "wrong action semantics": names phases |
| i-frames look / 无敌帧 / 無敵幀 / 無敵時間 | Dodge blur or flash | **U** | — | — |
| UE5 次世代光影, PBR / UE5級 | Game-render look (lighting, not motion) | D | [LAN2] | Fights anime flatness |

## Domain 6: Genre registers (bundles)

| Register | What it bundles (intended) | Ev | Source | Conflict with stickers |
|---|---|---|---|---|
| Hand-drawn anime on twos (see sentences below) | Stepped timing, principles, aggressive handheld | D | [HGO] | Handheld part conflicts; keep the timing part |
| Handheld documentary / raw indie | Shake, natural light, observational | B | [RWA] "Handheld documentary film style", "Raw indie film aesthetic", "Observational feel" | High |
| Claymation / stop-motion / 黏土动画 / 定格动画 / 定格動畫 / クレイアニメ、ストップモーション | Stepped cadence, tactile surfaces | B | [VEO] "claymation style", "stop-motion animation" | Low: stepped cadence suits stickers |
| Pixar-like 3D / 皮克斯风 / ピクサー風 | Appealing, broad 3D acting | B | [VEO] "Pixar-like 3D animation" | Low |
| Classic Disney / 迪士尼 2D | Full animation, squash and stretch | B | [VEO] "classic Disney animation style" | Low |
| Cel-shaded / 赛璐珞 / セル調 | Flat colour; masks AI flicker (D, reddit snip) | B | [VEO][KLA] | None |
| Wuxia wire-fu / 武侠威亚 / 武俠吊鋼絲 / ワイヤーアクション | Floaty hang-time leaps, fabric trails | D | [GOE] "flowing wire-fu choreography … sweeping camera movement … fabric and energy trails" | Wire-fu *adds* float. Do not use against F1. |
| Hong Kong action / 港式动作 / 港產動作 / 香港アクション | Fast cutting, undercranked hits | D (snip) | "Hong Kong wuxia + Hollywood action" [YOU2](snip) | High |
| Film noir, high-key, low-key | Lighting registers | B | [VEO] | Lighting only |
| Music video / MV / 音楽PV | Beat-synced cuts, performance | D | MiniMax H3 "high-energy 2D anime pop-punk music video" [JSH](snip) | Cuts conflict |
| Product commercial / TVC / 产品广告 | Slow push-ins, macro, glossy | D | Kling official example "slow push-in" [KLP] | Low |
| Sports broadcast, nature documentary (long lens), K-drama, ASMR macro, LINE/WeChat sticker animation | — | **U** | No generator-facing source found | Candidates; see the drafted sentences at the end |
| Sticker loop (official MiniMax skill) | Centered, static white background, loopable, ≤6 s | B (vendor-authored skill) | [MXS] | Base layer |

## Domain 7: Lens and look terms that affect motion feel

| Term | Effect on motion feel | Ev | Source | Models |
|---|---|---|---|---|
| Wide-angle lens / 广角 / 廣角 / 広角 | Exaggerated near-far speed, distortion | B | [VEO] | Veo |
| Telephoto / long-lens compression / 长焦压缩 / 長焦壓縮 / 望遠圧縮 | Flattened depth, slower apparent motion | B | [VEO] | Veo |
| Fisheye / 鱼眼 / 魚眼 / 魚眼 | Bulging, skate-video energy | B | [VEO] | Veo |
| Rack focus / 焦点转移 / 移焦 / ピント送り | Focus pull between planes | B, D | [VEO]; Grok 1.5 example "focus pulls off the pair" [AIW] | Veo, Grok |
| Shallow / deep depth of field | Subject isolation | B | [VEO][KLC] | Veo, Kling |
| Anamorphic / 变形宽银幕 / 變形寬銀幕 / アナモルフィック | Oval bokeh, flares, widescreen | B, D | [VEO "anamorphic widescreen"]; "Wide anamorphic ~24mm" [HGO] | Veo, Seedance |
| Split diopter | Two focal planes | B | [VEO] | Veo |
| Lens flare | — | B | [VEO] | Veo |

---

## Ready-made register sentences (verbatim, with source)

1. **3A fight** (ZH), D. "3A动作游戏惯性追尾机位，强动态模糊+TimeRamp" (AAA action-game inertial chase cam, strong motion blur + TimeRamp). [GNL]
2. **Hand-drawn anime on twos** (EN, Seedance 2.0), D with output: "traditional hand-drawn 2D animation, animated on twos at 12 frames per second — each drawing held for two frames then replaced, choppy stepped motion cadence, visible pose-to-pose timing, distinct keyframe drawings with no smooth in-between interpolation … line jitter and boil between frames. No 3D render, no game engine, no CGI smoothness. The 12 principles of animation throughout: anticipation, squash and stretch, follow-through and overlapping action, slow in/slow out, arcs, secondary action, exaggeration, solid drawing." [HGO]
3. **Anti-gimbal handheld** (EN, same source), D: "Aggressively handheld inside the scene — constant restless shake and jitter every frame … Horizon never perfectly level. Never gimbal-smooth, never tripod, never dolly, never crane, never aerial." [HGO]
4. **Grok idle loop** (JA, Grok loop mode), D with output: "@image1を15秒のシームレスなループ動画にする。…カメラ固定、バストアップ、白い無地背景。…動き：穏やかに呼吸し、自然に瞬きする。…最後は手を下ろし、表情・視線・首の角度・姿勢を@image1と完全に同じ開始状態へ戻し、ループが継ぎ目なく繋がること。髪は全体を通して微かに揺れる。…カメラ移動なし" [ERIS]
   - Gloss: make @image1 into a 15 s seamless loop; locked camera, bust-up framing, plain white background. Motion: breathe calmly and blink naturally. At the end, lower the hand and return expression, gaze, head angle and posture to exactly the starting state of @image1 so the loop joins seamlessly. Hair sways slightly throughout. No camera movement.
5. **Sticker** (EN, official MiniMax skill), B: "Smooth loopable motion, keep action within 6 seconds. Character stays centered, white background remains static." Action refs: "wave hand cheerfully, slight head tilt" / "shake with laughter, eyes squint shut". [MXS]
6. **Locked-off continuous shot** (EN, Grok 1.5), D with output: "One continuous shot, no cuts, locked-off camera. 0-2s: hold the wide frame as … 2-4s: … focus pulls off the pair onto …" [AIW]
7. **Locked-off** (EN, Runway official), B: "The locked-off camera remains perfectly still." Loop: "The camera must start and end on the exact same frame to create a perfect loop." [RWA]
8. **Speed ramp** (EN, Seedance 2.5), C: "SPEED TIMELINE (mandatory): 0.00–2.00s = REAL-TIME … 2.00–6.00s = EXTREME SLOW MOTION (syrupy) … 6.00–8.00s = back to REAL-TIME settle + brief lock. CAMERA: continuous low-angle ORBIT … Orbit speed matches tempo." [KC35]
9. **Grok orbit** (EN), D: "CAMERA: 360° clockwise orbit around subject, center-locked parallax, subtle push-in (3%), stabilized, cinematic motion blur" [GRL]
10. **Chinese-anime fight PV** (ZH, Seedance 2.0), D with output: "整体风格为 高完成度热血国漫 / 动漫电影感 / 超高能战斗PV感 … 动作极快 - 镜头高速跟随 - 特效夸张 - 速度感极强 … 动作必须清楚可读 - 特效不能把动作完全遮住" [LAN1]
    - Gloss: overall style is polished hot-blooded Chinese anime / anime-film feel / super-high-energy battle PV. Action extremely fast, camera follows at high speed, exaggerated effects, very strong sense of speed. The action must read clearly, and the effects must not fully hide it.
11. **FPV fight** (ZH, Seedance), D with output: "穿越机环绕式镜头：高速贴身绕拍、低空环绕、侧后绕切、贴地掠过、人物之间穿梭…但不能乱飞，必须始终看清双方站位与攻防逻辑" [LAN2]
    - Gloss: FPV-drone orbiting camera: high-speed close orbits, low-altitude circling, side-rear cut-arounds, ground-skimming passes, weaving between the fighters. It must not fly randomly, and the positions and attack/defence logic of both sides must always be clear.
12. **Shōnen anime** (EN, Seedance), D: "fluid high-frame animation, strong speed lines, impact frames, dramatic lens pulls, explosive effect timing" [ATF](snip). 90s OVA variant: "limited animation frame rate (12fps feel)" [ATA]
13. **Hit-stop** (EN, Seedance 2.0 template), D: "Heavy hit: 2-frame freeze frame + bright highlight flash + subtle screen shake → quickly return to normal motion." [BPX]. Also "freeze frame on impact, then release" [S2P]
14. **Wuxia** (EN, Seedance 2.0), D: "flowing wire-fu choreography … sweeping camera movement … fabric and energy trails" [GOE]
15. **Handheld documentary** (EN, Runway official example), B: "Handheld documentary film style. Raw indie film aesthetic. Natural lighting. Unpolished, authentic look. Low budget realism. Observational feel." [RWA]
16. **Kling stable move** (EN, official pattern), B: "Slow, stable pan left across [scene], no sudden motion." [KLC]
17. **Anti-drift** (EN, Vidu), D: "no panning, no drift, no handheld motion" [VID]
18. **True dolly disambiguator** (EN, Veo 3.1), C: "camera physically moves forward, not zoom, true dolly motion" / "parallax visible on background elements" [PIC]
19. **Japanese anime look** (JA, MiniMax H3), D with output: "日本のアニメ作画。手描きの繊細な線、平坦なセル塗り、フルカラー。浅い被写界深度、フルサイズ換算24〜85mmのズーム感。" [SOH]
    - Gloss: Japanese anime drawing; delicate hand-drawn lines, flat cel colouring, full colour; shallow depth of field, a 24–85 mm full-frame-equivalent zoom feel.

### Drafted candidates (ours, U: no source; only for A/B arms, not to be cited)

- **Sticker:** "LINE-sticker style anime chat-sticker loop, Live2D-style rigged idle on a locked-off frame, pose-to-pose key acting on twos, crisp anticipation, held key pose, overlapping action on hair and ribbons, returns to the first frame." (= the 2026-11-07 tested register sentence + on-twos)
- **Fighting-game:** "fighting-game frame-data read: clear startup pose, one-frame active hit with hit-stop, readable recovery pose, locked camera."
- **Nature documentary:** "nature-documentary long-lens telephoto, locked tripod, compressed depth, patient observational hold."
- **Sports broadcast:** "sports-broadcast long-lens follow pan, slight operator lag, instant-replay slow motion."
- **ASMR macro:** "ASMR macro, extreme close-up, locked tripod, slow deliberate hand motion, shallow focus."

---

# Image

Covers GPT image (gpt-image-2 / ChatGPT Images), Midjourney, Nano Banana / Gemini image, FLUX, Seedream and NovelAI / PixAI.

Image failures ranked against:

- **I1**: cluttered or illegible results.
- **I2**: flat or generic composition.
- **I3**: identity loss of the subject.
- **I4**: sticker unreadable at 128 px.

## Image bottom line

- **A-level evidence is about generic boosters only.**
  - Mo et al. (CVPR 2024) table A1 (snip; supplemental PDF returned 403): adding "artstation" raised the aesthetic score 5.58 → 5.83 but **lowered** text-image similarity 0.28 → 0.26 [MO].
  - Pavlichenko & Ustalov (SIGIR 2022) ran human-judged keyword search on Stable Diffusion. Popular keywords are not necessarily the most effective [BPT].
  - Lesson: style and "quality" boosters trade against prompt fidelity, which is a plausible mechanism for **I3 identity loss**. Pair every booster with an identity anchor.
- **Official guides are restraint-heavy (B).**
  - OpenAI: "Avoid … extra decoration"; "Favor simplicity over detail so it reads clearly at small and large sizes"; "Do not redesign the character" [OAI].
  - Google (Nano Banana): "Describe the scene, don't just list keywords"; an official sticker template; an official negative-space template [GGL].
  - FLUX: no negative prompts. Write the positive opposite, e.g. "empty" rather than "no people" [BFL].
- **NovelAI / PixAI / Illustrious-family models read Danbooru-style tags.** NovelAI's docs show weighting syntax (`2.1::transparent background::`) and "visual novel chibi" (V5) [NAI].
  - Tag post counts could not be verified: the Danbooru API returned 503 / blocked.
  - Tags marked **T** below are standard Danbooru tag names from memory, unverified this session. Treat them as D until checked.
- **Both @NanameNanameumh suffixes are D.** Each was posted with output images, and several users replied with their own outputs and said the result is rich but not cluttered. Neither shows a with/without comparison.
- **Fragility warning (C).** A GPT-images user showed with/without results for "線はシンプル、細かく書き込まず、面で表現する" (simple lines, no fine detailing, express it with planes). The interpretation of that phrase **changed after the 2026-11-01 model update** [LUL]. Re-validate restraint phrases after each model update.

## Top 10 to A/B first: Image

| # | Phrase | Fixes | Ev | Source | Conflict / note |
|---|---|---|---|---|---|
| 1 | **Official sticker template:** "A [style] sticker of a [subject] … The design features bold, clean outlines, simple cel-shading, and a vibrant color palette. The background must be white." | I4, I1 | B | [GGL] | Base layer for chat stickers |
| 2 | **"Favor simplicity over detail so it reads clearly at small and large sizes"** (OpenAI logo guidance; transplant it to stickers) | I4, I1 | B | [OAI] | Fights any detail booster. Pair them deliberately. |
| 3 | **Identity anchor:** "Same facial features, proportions, and color palette. Do not redesign the character." | I3 | B | [OAI]; community "REFERENCE & IDENTITY LOCK … single source of truth" (D) [MEA] | Add it whenever a style booster is present (see the A-level trade-off) |
| 4 | **Placement + negative space:** "A minimalist composition featuring a single [subject] positioned in the [bottom-right] of the frame. The background is a vast, empty [color] canvas, creating significant negative space." | I2, I1 | B | [GGL]; OpenAI "subject centered with negative space on left" [OAI] | Poster / KV. For stickers, shrink to "generous padding". |
| 5 | **Hierarchy + restraint pair:** "intentional visual hierarchy, controlled visual complexity" | I1, I2 | D | Both Naname suffixes [NN1][NN2] | Cheap 4-word add; test alone |
| 6 | **Naname restraint suffix (画像洗練 隠し味, "image refinement, hidden-seasoning prompt"):** "theme-driven art direction, concept-integrated decorative design, intentional visual hierarchy, controlled visual complexity, restrained ornamentation. sophisticated graphic composition, dynamic framing and spatial layering. smooth continuous contours." | I1, I2 | D | [NN2]. The author says the aim is to select only the ornament the picture needs, and the effect is subtle: 「地味に効果がありますが…わかりにくい」 ("it quietly works, but it's hard to notice") | Safe on stickers. The subtle effect needs a blind judge. |
| 7 | **Naname escalation suffix (豪華装飾, "luxurious ornament"):** the 9 terms (see Domain 11) | I2 | D | [NN1], with user outputs in the replies | **Conflicts with stickers**: the frame steals pixels from the subject at 128 px. Use for KV / card art. |
| 8 | **Danbooru framing tags:** `simple background, white background, upper body / full body, chibi` | I4, I1 | T | [NAI] (chibi V5) | Tag models only. Natural-language models want sentences [GGL]. |
| 9 | **Positive-opposite phrasing:** "empty / deserted / monochrome / smooth gradient background" instead of "no clutter / no background" | I1 | B | [BFL] | FLUX ignores negation. Probably general: OpenAI also states positive constraints. |
| 10 | **Wallpaper register:** "black background, negative space, rim light, looking-back pose" (黒背景、余白、リムライト、振り向き構図) | I2 | D | Posted with output [MAR] | Dark background fails on chat-app dark mode for stickers |

Runner-up: "balanced negative space, avoid unnecessary peripheral expansion" (D) [TOB]. Rule of thirds, "from above / from below" and foreground/midground/background layering (D) [SAK].

## Domain 8: Composition and art direction

| Term (EN / 简 / 繁 / 日) | Visible effect | Suits / conflicts | Ev | Source | Models |
|---|---|---|---|---|---|
| Negative space / 留白 / 留白 / 余白 | Empty area that isolates the subject | Posters, KV, wallpapers. Stickers: as padding only. | B | [GGL][OAI]; [TOB][MAR] D | Gemini, GPT image |
| Visual hierarchy, focal point / 视觉层级、视觉焦点 / 視覺層級 / 視覚的階層、主役と脇役 | One dominant read, subordinate rest | All | D | [NN1][NN2] | GPT image, MJ (user replies, unspecified) |
| Controlled visual complexity, density control / 控制复杂度、疏密 / 疏密 / 密度コントロール | Detail clustered, rest calm | Ornate work | D | [NN1][NN2] | — |
| Rule of thirds, subject on right / 三分法 / 三分法 / 三分割構図 | Off-centre balance | Scenes. Conflicts with centered stickers. | B, D | Kling (video) lists it [KLP]; [SAK] | — |
| Rule of odds / 奇数法则 / 奇數法則 / 奇数の法則 | 3 or 5 grouped items | Props | **U** | — | — |
| Leading lines, eye guidance / 引导线、视线引导 / 引導線 / 視線誘導 | Lines point to the subject | Scenes | D | [SAK] mentions 視線誘導 | — |
| Framing device (arch, window, ornament) / 框中框 / 框中框 / フレーム内フレーム | Subject enclosed | KV, cards | D | "monumental ornamental framing" [NN1] | — |
| Spatial layering FG/MG/BG / 前中后景 / 前中後景 / 前景・中景・背景 | Depth | Scenes. Clutter risk. | D | [NN2] "dynamic framing and spatial layering"; [SAK] | — |
| Camera height: from above / from below / 俯拍 / 仰拍 / 俯瞰・あおり | Cute vs powerful | Characters | B (photo terms) / D | [GGL] "low-angle perspective"; [SAK] | Gemini |
| Explicit placement ("logo top-right, empty space below") | Layout obeyed | Posters, stickers with text | B | [OAI] | GPT image |
| 構図 / 构图 / 構圖 / composition (generic) | — | — | **U** as a term | Generic words such as "cinematic" or "composition" are vague; guides prefer explicit placement [OAI][GGL] | — |

## Domain 9: Ornament, illustration and card registers

| Term | Visible effect | Suits / conflicts | Ev | Source |
|---|---|---|---|---|
| Art Nouveau / Mucha frame / 新艺术运动 / 慕夏 / アール・ヌーヴォー、ミュシャ風 | Halo arch, floral border, flat poster colour | Card, KV. Conflicts with 128 px stickers. | T / U (no generator-specific source found) | `art_nouveau` is a Danbooru tag (T) |
| Tarot card / 塔罗牌 / 塔羅牌 / タロットカード | Vertical framed card, title plate, symbolism | Card art | T / U | `tarot` (T) |
| Gacha SSR card art / 抽卡SSR立绘 / 抽卡SSR / ガチャSSRカードイラスト | Dynamic pose, FX burst, rich BG | Promo art. Clutter risk. | **U** | No source found |
| 立ち絵 / 立绘 / 立繪 / tachi-e standing sprite | Full-body, neutral BG, readable silhouette | Character sheets, VN | D | Nano Banana tachi-e as the single source for every cut [TAP]; character-sheet framing [MEA] |
| Key visual (KV) / 主视觉 / 主視覺 / キービジュアル | Poster-grade hero composition with type space | Promo | **U** | — |
| 一枚絵 / 一张图 / 一張圖 / single illustration | Self-contained finished piece | — | **U** | — |
| TCG full-art / 全画框卡 / 全圖卡 / フルアート | Art bleeds past the frame | Cards | **U** | — |
| LINE sticker / LINEスタンプ / 表情包 / 貼圖 | Character + short text, one emotion, padding | Chat | D | 8-sticker GPT prompt [HAL]; GPT-images chibi GIF [MID] |
| Chibi / SD / Q版 / Q版 / ちびキャラ、SD | 2–3 head proportions, big head, readable at small size | Stickers | B (NovelAI "visual novel chibi"), T | [NAI] |
| Character sheet / reference sheet / 设定图 / 設定畫 / キャラシート、三面図 | Turnaround views | Identity anchor | D | [MEA][HPJ] |

## Domain 10: Rendering and line terms

| Term | Visible effect | Suits / conflicts | Ev | Source | Models |
|---|---|---|---|---|---|
| Cel shading / 赛璐珞上色 / 賽璐珞 / セル塗り、アニメ塗り | 1–2 hard shadow steps, flat fills | Stickers, anime | B | [GGL] "simple cel-shading"; [VEO][KLA] (video) | Gemini, Veo, Kling |
| Bold clean outlines / 粗描边 / 粗描邊 / 太い主線 | Silhouette survives downscale | Stickers (I4) | B | [GGL] | Gemini |
| Thick white sticker border / 白色描边 / 白邊 / 白フチ | Die-cut sticker look | Stickers | D | [CAR2](snip) "thick crisp black outline, flat colors"; frameo "thick white sticker outline" (snip) | — |
| Flat colour / 平涂 / 平塗 / ベタ塗り、フラット | No gradients | Stickers, icons | B, T | [OAI] "Flat design, minimal strokes, no gradients unless essential" | GPT image |
| 厚塗り / 厚涂 / 厚塗 / thick-paint (impasto-style digital) | Painterly volume, few lines | Splash art. **Conflicts with 128 px**. | D (model-version tendency only) | Animagine 3.1 looks 厚塗り/backlit vs 4.0 薄塗り with the same seed [JIK] | Animagine (SDXL) |
| Line weight variation / 线条粗细 / 線條粗細 / 線の強弱 | Thick outer, thin inner lines | Illustration | **U** | — | — |
| "Simple lines, planes not details" (線はシンプル、細かく書き込まず、面で表現する) | Lower detail density | Stickers | C | Before/after posted; **meaning drifted after the 11/1 update** [LUL] | GPT images 2.6 |
| Smooth continuous contours / 流畅轮廓 / 流暢輪廓 / 滑らかな連続した輪郭 | Clean silhouette edges | All | D | [NN2] | — |
| Rim light / 轮廓光 / 輪廓光 / リムライト | Bright edge separates the figure from the BG | Dark BG. Counteracts clutter. | D, T | [MAR]; `rim_lighting` (T) | GPT image (MAR) |
| Bloom / glow / 辉光 / 光暈 / ブルーム | Soft highlight bleed | Fantasy. Reduces 128 px contrast. | **U** for image models | — | — |
| 2.5D / 2.5次元 | Anime face, 3D-ish shading | — | **U** | — | — |
| Photo terms: 85mm portrait lens, bokeh, Dutch angle, macro | Lens look | Realism | B | [GGL] | Gemini |
| Midjourney `--stylize` / `--raw` | Higher stylize gives more MJ house style and less literal prompt following; raw reduces auto-styling | Identity (I3): use low stylize or raw | D (third-party, docs 403) | [MJ3] | Midjourney |

## Domain 11: Push + restraint pairs (the main structure)

The principle comes from [NN1]. For every escalation term, name the restraint term that keeps the richness legible:

> 「装飾を増やして豪華にする」のではなく、「その絵に必要な装飾だけを選び…」

Gloss: not "add ornament to make it luxurious", but "select only the ornament the picture needs".

[NN2] is the same author's restraint-weighted register.

### The two suffixes side by side

| | 豪華装飾 (escalation-weighted) [NN1], 2026-11-03, ~23K views, 747 likes | 画像洗練 隠し味 (restraint-weighted) [NN2], 2026-11-06, ~3.1K views, 169 likes |
|---|---|---|
| Push terms | monumental ornamental framing; seamless ornamental integration; oversized symbolic centerpiece; extreme detail concentration | concept-integrated decorative design; dynamic framing and spatial layering |
| Restraint terms | bold negative space separation; intentional visual hierarchy; controlled visual complexity | intentional visual hierarchy; controlled visual complexity; **restrained ornamentation**; **smooth continuous contours** |
| Governing / neutral terms | theme-driven art direction; sophisticated graphic composition | theme-driven art direction; sophisticated graphic composition |
| Ratio, push : restraint | 4 : 3 | 2 : 4 |
| Author's stated intent | Big frame + fusion with the subject + dense detail, while raising finish, individuality and **legibility (視認性)** | Choose only the needed ornament; the effect is subtle (「地味に効果がありますが…わかりにくい」) |
| Evidence | D: outputs posted, users replied with outputs and called it rich but not cluttered | D: outputs posted |

Observation: the restraint-weighted version drops the centerpiece and frame escalation and adds contour clarity ("smooth continuous contours"). That makes it the safer candidate for stickers. The escalation version suits KV and card art.

### Pairing table

| Push (escalation) | Paired restraint | Why the pair works | Ev of the pair | Source |
|---|---|---|---|---|
| monumental ornamental framing | bold negative space separation | The frame adds richness, and the empty gap keeps the subject from merging into it | D | [NN1] |
| extreme detail concentration | controlled visual complexity / "detail only at the focal point, calm periphery" | "Concentration" localises detail. The restraint term caps the total. | D | [NN1][NN2] |
| oversized symbolic centerpiece | intentional visual hierarchy | One dominant element, the rest subordinate | D | [NN1] |
| seamless ornamental integration | restrained ornamentation / concept-integrated decorative design | Ornament derived from the theme, not added | D | [NN1][NN2] |
| dynamic framing and spatial layering | smooth continuous contours / clear figure-ground separation | Depth layers stay readable if silhouettes stay clean | D | [NN2] |
| theme-driven art direction (escalates meaning) | (self-limiting: the theme filters what gets added) | Selection criterion | D | [NN1][NN2] |
| highly detailed / intricate | "Favor simplicity over detail so it reads clearly at small and large sizes" | Small-size legibility | B | [OAI] |
| decorative elements | "Avoid … extra decoration … anything that feels generic or overdesigned" | Official anti-clutter | B | [OAI] |
| vibrant colour palette | bold clean outlines + simple cel-shading + white background | Saturation is fine when edges are hard and the BG is empty | B | [GGL] sticker template |
| single subject, minimalist | vast empty canvas, significant negative space, explicit position | Restraint used *as* the composition | B | [GGL] |
| rich dark background (wallpaper) | rim light + negative space | Edge light separates the figure from the dark BG | D | [MAR] |
| style booster ("artstation", "masterpiece") | identity anchor ("Same facial features, proportions… Do not redesign") | Boosters cost text-image fidelity (A) | A (cost) + B (anchor) | [MO][OAI] |
| GPT's default high detail | 線はシンプル、細かく書き込まず、面で表現する (simple lines, no fine detailing, express it with planes) | Explicit detail-density cap | C (model-update fragile) | [LUL] |
| 描き込み (rendering density) | 余白 (empty space) | Classic JP illustration pair | U as a prompt pair | — |
| 情報量 (information load) | 密度コントロール (density control) | — | U | — |
| 主役 (lead) | 脇役 (supporting) | Same as hierarchy, in JP | U | — |
| sparkles / particles / glow | "only around the subject; background empty" | Keeps the effect local | U | — |
| dynamic pose / foreshortening | readable silhouette, chibi 2–3 heads | Pose energy without a tangle at 128 px | U | — |
| 厚塗り painterly | bold outline / flat fill at sticker size | Painterly mush disappears when downscaled | U (D for the style tendency [JIK]) | — |

### Video analogue of the same structure

The tweet's sentence [GNL] is all push: chase cam, strong blur, TimeRamp. Its restraint partner is missing. In the thread, @sensen2028 points out that impact force still needs timing and hit pauses. Candidate pairs:

| Push | Restraint |
|---|---|
| strong motion blur | crisp held key pose on contact |
| inertial chase cam | locked horizon / readable staging ("必须始终看清双方站位与攻防逻辑", the positions and attack/defence logic of both sides must always be clear, as in [LAN2]) |
| speed ramp | second-stamped return to real-time [KC35] |
| FX-heavy | "特效不能把动作完全遮住" (the effects must not fully hide the action) [LAN1] |

[LAN1] and [LAN2] already write their restraint clauses in this pattern.

### Image register sentences (verbatim)

1. **豪華装飾 (escalation)** [NN1]: "monumental ornamental framing, seamless ornamental integration, oversized symbolic centerpiece, extreme detail concentration, bold negative space separation, intentional visual hierarchy, controlled visual complexity, theme-driven art direction, sophisticated graphic composition"
2. **画像洗練 隠し味 (restraint)** [NN2]: "theme-driven art direction, concept-integrated decorative design, intentional visual hierarchy, controlled visual complexity, restrained ornamentation. sophisticated graphic composition, dynamic framing and spatial layering. smooth continuous contours."
3. **Sticker** [GGL]: "A [style] sticker of a [subject], featuring [key characteristics] and a [color palette]. The design should have [line style] and [shading style]. The background must be white."
4. **Negative space** [GGL]: "A minimalist composition featuring a single [subject] positioned in the [bottom-right/top-left/etc.] of the frame. The background is a vast, empty [color] canvas, creating significant negative space."
5. **Layout** [OAI]: "Medium close-up at eye level, subject centered with negative space on left." / "Logo top-right, headline centered, empty space below for body copy."
6. **Anti-clutter** [OAI]: "Avoid clip art, stock photography, gradients, shadows, decorative elements, or anything that feels generic or overdesigned."
7. **Square stability** [TOB] (JA/EN, D): "1:1 square composition, centered framing, balanced negative space, avoid unnecessary peripheral expansion"
8. **Wallpaper** [MAR] (JA, D): 黒背景、余白、リムライト、振り向き構図 (black background, negative space, rim light, looking-back pose)

### Drafted candidates (ours, U: for A/B arms only)

- **Sticker (restraint-weighted):** "chibi LINE-sticker character, one emotion, bold clean outlines, simple cel-shading, flat colour, intentional visual hierarchy, controlled visual complexity, smooth continuous contours, generous padding, white background, same facial features, proportions and colour palette as the reference."

---

## Sources (key → URL)

### Official guides and docs
- [VEO] https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide
- [MMX] https://platform.minimax.io/docs/api-reference/video-generation-i2v
- [MXS] https://github.com/MiniMax-AI/skills/blob/main/skills/gif-sticker-maker/assets/video-prompt-template.txt
- [KLC] https://kling.ai/blog/kling-ai-camera-control-video-guide
- [KLP] https://kling.ai/blog/kling-ai-prompt-guide
- [KLA] https://kling.ai/blog/kling-ai-anime-video-prompts
- [RWA] https://academy.runwayml.com/prompt-library
- Runway's camera-terms page (https://help.runwayml.com/hc/en-us/articles/46749315925395) could not be opened (403).
- [BPS] https://docs.byteplus.com/docs/ModelArk/1587797 (snip: Seedance 1.0 Pro responds to tracking, pan, truck and orbit). Seedance 2.0 and 2.5 guide bodies were not retrievable.
- Wan and Grok: no official prompt guide found. Grok advice comes from Scenario and Replicate, both third-party: [SCN] https://help.scenario.com/articles/5410526625-grok-imagine-video-a-guide-to-ai-motion-creation

### Papers
- [VB2] https://arxiv.org/abs/2503.21755
- [DYN] https://arxiv.org/abs/2510.07441
- [ANB] https://arxiv.org/abs/2604.15299
- [CAMB] https://arxiv.org/abs/2504.15376 (camera-motion taxonomy for understanding, not generation)

### Community posts on X
- [GNL] https://x.com/i/status/2118652052272447896 (replies read via agent-reach, = [GNL-thread])
- [KC35] https://x.com/i/status/2114901454159052953
- [HGO] https://x.com/i/status/2077952102169526462
- [ERIS] https://x.com/i/status/2116852652340646373
- [AIW] https://x.com/i/status/2115002899579245038
- [LAN1] https://x.com/i/status/2092807747020689580
- [LAN2] https://x.com/i/status/2101681457345507461
- [BAS] https://x.com/i/status/2115385300440461452
- [ICL] https://x.com/i/status/2115171368446701913
- [LOV] https://x.com/i/status/2089764797361582208
- [SOH] https://x.com/i/status/2094736167681826950
- [CIA] https://x.com/i/status/2105509894690574362
- [IMH] https://x.com/i/status/2112171868543414765
- [BIM] https://x.com/i/status/2081465350747779450
- [JSH] https://x.com/i/status/2094305294117429711

### Vendor and community blogs
- [PIC] https://blog.picassoia.com/veo-3-1-cinematic-camera-control-put-to-the-test
- [ADB] https://community.adobe.com/bug-reports-403/no-matter-what-model-i-use-and-even-if-i-give-explicit-instructions-to-not-push-or-pan-or-move-it-still-does-it-1632612
- [PIP] https://www.pippit.ai/blog/stop-unwanted-camera-movement-ai-video
- [VID] https://www.cutout.pro/learn/?p=2620
- [BPX] https://budgetpixel.com/blog/if-you-want-to-create-cinematic-fighting-videos-in-seedance-20-start-with-a-prompt-template
- [S2P] https://seedance2pro.io/blog/seedance-2-fight-scene-guide
- [ATA] https://www.atlascloud.ai/blog/guides/seedance-2.5-anime-prompts-style-control
- [ATF] https://www.atlascloud.ai/seedance-2-prompt/66
- [GOE] https://www.goenhance.ai/prompts/video-prompts/epic-wuxia-martial-arts-prompt
- [GRL] https://www.latestly.com/socially/technology/elon-musks-xai-grok-imagine-enables-cinematic-360-degree-camera-shots-for-creators-know-how-to-create-videos-using-custom-prompt-7156829.html
- [HGM] https://geo.higgsfield.ai/blog/how-to-add-motion-blur-depth-of-field-ai-video
- [HGF] https://www.miracamp.com/learn/video-editing/new-higgsfield-viral-presets and https://bibigpt.co/en/features/higgsfield-ai-video-generator-explained
- [MH] https://magichour.ai/blog/how-to-make-seamless-ai-video-loops
- [REDL] https://reddit.sentinel-team.org/posts/1skzgzr/snapshots/2026-04-18T02%3A30%3A02.574056Z
- [SKD] https://clawhub.ai/woodfantasy/seedance-shot-design
- [CAR] https://carat.im/en/prompt-gallery/sakuga
- [YOU] https://youmind.com/video-prompts/1399
- [YOU2] https://youmind.com/es-419/video-prompts/seedance-2-0-wuxia-action-short-video-prompt-1644

### Image sources

Official:
- [OAI] https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide.md
- [GGL] https://developers.googleblog.com/en/how-to-prompt-gemini-2-5-flash-image-generation-for-the-best-results/
- [BFL] https://docs.bfl.ai/guides/prompting_guide_t2i_negative
- [NAI] https://docs.novelai.net/en/image/tags/

Papers:
- [MO] https://openaccess.thecvf.com/content/CVPR2024/supplemental/Mo_Dynamic_Prompt_Optimizing_CVPR_2024_supplemental.pdf (snip; 403)
- [BPT] https://arxiv.org/abs/2209.11711
- Taxonomy (qualitative): https://arxiv.org/abs/2204.13988

Third-party:
- [MJ3] https://www.temperstack.com/learn/midjourney/master-stylize-parameters/ (official docs.midjourney.com returned 403)
- Seedream: no official guide retrieved. Third-party advice (concise wording, one style) is at https://www.veed.io/learn/seedream-4-prompting-guide

Community posts on X:
- [NN1] https://x.com/i/status/2117732766771269926 (prompt in the author's reply in the same thread)
- [NN2] https://x.com/NanameNanameumh/status/2118818205313507711; intent note https://x.com/NanameNanameumh/status/2118831728542581017
- [LUL] https://x.com/i/status/2118003597854343231
- [MAR] https://x.com/i/status/2067442490341494903
- [TOB] https://x.com/i/status/2099128837770715644
- [SAK] https://x.com/i/status/2076956972906066244
- [JIK] https://x.com/i/status/1884917396059951548
- [TAP] https://x.com/i/status/1989521234594308457
- [MEA] https://x.com/i/status/2097949170594193427
- [HPJ] https://x.com/i/status/1993611181408563278
- [HAL] https://x.com/i/status/2070847382552768618
- [MID] https://x.com/i/status/2118519274482586001
- [CAR2] https://carat.im/prompt-gallery/p/14425 (snip; it is uncertain which gallery entry the quote came from)
- Danbooru tag counts could not be verified: the counts/tags API returned 503 / blocked. T-rated tags are from memory.

### Search notes
- xiaohongshu search through agent-reach returned unrelated, personalized results without a login, so it yielded nothing usable.
- bilibili was not reached in time.
- Dolly-zoom success figures (22% and ~80%) appeared only in search summaries of blogs that could not be traced. Picassoia's page reports no dolly-zoom figure.
