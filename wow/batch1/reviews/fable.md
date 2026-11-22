**Judgement on the packet only (pre-completion, 2026-11-22).**

| Gate | Label | Basis in packet |
|---|---|---|
| W1 痛點 | 通過 | Owner-stated need plus a measured failure of the old default: unkeyed 4.21–12.19 MB magenta GIFs that still reported technical_pass true. No invented market or savings claim. |
| W2 美觀 | 通過 (with one blemish) | First screen now uses a checkerboard preview and a 726 KB transparent hero; gallery heroes ≤ 0.89 MB; after-screenshots show no magenta floor on light and dark. Blemish: the mid-frame sword trail keeps interior magenta, visible on the flagship. Live GitHub render at 390/1440 px not captured. |
| W3 好用 | 通過 | One command, no flag, 5.06 s, exit 0, correct key auto-detected. Four human errors exit 1 with what / impact / next step. Installer, doctor, and a live Claude Code session all worked. Human 30-second timing still owed. |
| W4 專業介面 | 通過 | State honesty is good: summary reports loop FAIL and pops WARN, no "seamless" claim, `--no-key` delivery fails loudly. Light and dark checkerboards, dated cost table with recheck notice, EN + ZH-TW. Open items: possibly red CI badge on the first screen, live render unverified. |
| W5 驚豔質量 | 未通過 | The default flow on the flagship clip fails loop (speed) and warns on pops. The kept interior magenta can exceed the written acceptance magenta_share_max ≤ 0.02 on attack frames, so the default output can violate the project's own acceptance. Visual motion approval is pending. Only the curated example plus C1–C3 were run; no held-out real videos. Transparency and freeze are strong, but "amazing and checkable" is not yet shown. |
| W6 領域知識與真實實作 | 通過 | Connected-component chroma key with ring_opaque_max and alpha_mismatch metrics, border kept transparent, C1 island preserved, C3 green keyed, C2 honestly labeled non-transparent. Freeze detection trims the tail from last motion. `vgs qa` fails the legacy GIF. This is a real implementation, not a façade. |
| W7 專業工作流 | 通過 | $0 batch, no Grok or fal calls, local path is the default and cheapest adequate path, cost table dated with recheck caveat. Acceptance written before the build, independent design review, official final.gif files not overwritten. |

**Batch verdict: 未達成.** W5 is applicable and 未通過. Everything else holds.

**Must-fix before claiming 達成**

1. **Flagship loop.** The hero clip is the default-flow showcase and it fails loop on speed. Either make the loop pass on this clip or pick a flagship clip whose default output passes loop, with the summary proving it.
2. **Acceptance conflict on interior magenta.** The connected key can breach magenta_share_max ≤ 0.02 on attack frames. Pick one: despill or tint the kept interior pixels so the trail is not magenta, or amend the acceptance with a stated rationale and make `vgs qa` report the share honestly. Right now the default output can fail the written spec.
3. **Human visual motion approval** of hero.gif and the C1–C3 outputs. W5 is "checkable" quality, and the check is still pending.
4. **Held-out real videos** through the plain `vgs make` path, at least two or three, with summaries attached. Without them W5 rests on a curated example, which the gate explicitly excludes.

**Later only**

- Capture the live GitHub README render at 390 px and 1440 px.
- Have one human time the first command from a fresh clone against the 30-second target.
- Turn the CI badge green or remove it from the first screen until it is.
- Decide a strategy for C2 busy backgrounds, or document it as out of scope in the README.
- Reduce the pops WARN on the flagship.
- Submit the Agensi pack once W5 passes.
