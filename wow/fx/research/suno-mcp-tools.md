# Suno MCP tools available in this session

Inspected: 2026-11-06 05:29:50 UTC (2026-11-06 13:29:50 Asia/Taipei).

Server: `suno`. Available tools: **35**.

Source: live tool metadata exposed to this session, plus the two read-only tool responses recorded below. This is an inventory of the connected server, not a catalog of every Suno website or public API feature.

Only `mcp__suno__account_usage({})` and `mcp__suno__library_list({"limit":10})` were invoked. No songs, sounds, speech, covers, extensions, stems, uploads, joins, downloads, or library changes were requested. These account/library reads do not spend credits.

## Schema format and limits

Each tool below includes its exact exposed description and complete TypeScript input declaration, preserving all available parameter comments, nested objects, enums, and optionality. `?` means optional; a property without `?` is required; `{}` accepts no named parameters. The runtime provides these declarations rather than the original MCP JSON Schema document. Constraints not present in the declarations or descriptions are not inferred. Return values are exposed as `CallToolResult`, not a detailed result schema.

## Requested capability map

| Capability | Exposed tools and parameters |
| --- | --- |
| Instrumental | `audio_create.instrumental?: boolean`; `audio_extensions_create.instrumental?: boolean`. Covers are described as instrumental when lyrics and voice are omitted. |
| Duration / length | `audio_create.duration?: number`, `duration_guidance?: boolean`, `duration_strict?: boolean`. Cover, extension, mashup and speech expose `duration`; their parameter comments specify a 15–360 second target. Speech also documents guidance and hard-cap behavior. The compact audio-create declaration gives no parameter comments, so its exact bounds/defaults are not separately verified. Sounds have model-selected length and no duration input. No literal `length` input is exposed. |
| Style / tags | `style?: string` and `negative_style?: string` on relevant creation tools; genre/style tags are carried as strings, not a separate `tags` array. Audio-create simple mode uses `description`; its description forbids mixing `description` with `style`. |
| Lyrics | `audio_create.lyrics`, cover/extension/mashup `lyrics`; `audio_edit.lyrics` changes library text. `audio_lyrics_alignment` retrieves timing. Full declarations below specify exact optionality. |
| BPM / tempo | `sounds_create.tempo?: number` explicitly means BPM. Song creation has no dedicated BPM/tempo field. `audio_analysis` reports measured tempo; `audio_listen` can answer tempo questions. |
| Musical key | `sounds_create.key` is an optional 24-value major/minor enum. Song creation has no dedicated musical-key input. Analysis/listen can report a measured key. `idempotency_key` is a retry identifier, not a musical key. |
| Extend / continue | `audio_extensions_create` requires `id` and `continue_at` (seconds). It creates only the continuation. `audio_full_song` joins the extension chain; joining is documented as free but was not invoked. |
| Cover | `audio_covers_create`, with source `id`, style, lyrics, voice, duration and controls. See the documentation inconsistency below concerning `title`. |
| Stems / separation | No dedicated stems/separation tool or output-format parameter is exposed. `audio_create` explicitly describes splitting stems via simple-mode `description` plus up to 10 `reference_audio_ids` for a signed-in Suno user. This is a creation route and was not invoked. Exact stem sets, isolation guarantees, and output packaging are not specified. |
| Download formats | `audio_download.format?: "mp3" | "wav"`; default MP3. A download may require a separate credit and explicit `confirm: true`. No downloads were requested. |
| Loop | `sounds_create.loop?: boolean` makes a seamless loop. No dedicated loop flag on song generation. |
| Advanced controls | Relevant song creation tools expose `controls.audio_influence`, `style_influence`, `weirdness`, and `variety`. Detailed declarations specify 0–1 sliders and integer variety 0–4; omitted values preserve model defaults. `model`, `max_mode`, voice and vocal-gender controls vary by tool. |

### Metadata inconsistency

`audio_covers_create` says in its prose that a cover always takes its source's title and there is no `title` field, but its exposed input declaration contains `title?: string` with a source-title default comment. Both are preserved verbatim below. Actual title behavior was not tested because that would create audio.

## Read-only account and library results

### Account usage

Call: `mcp__suno__account_usage({})`. Result: successful.

- Plan: **Premier Plan**, billing period **year**.
- Song-generation credits remaining: **8510**.
- Monthly usage: **1490 / 10000**.
- Download credits remaining: **67**.
- Allowed models: `v6-mini`, `v6`, `v6-wild`.
- `metered_features` is an empty object; no additional per-feature quota values were returned.
- Both `renews_on` and `cancel_on` are returned as `2026-11-28T00:15:35Z`; the response does not explain why they coincide. No additional billing-state inference is made.

Complete decoded response payload:

```json
{
  "allowed_models": [
    "v6-mini",
    "v6",
    "v6-wild"
  ],
  "features": [
    "generate.simple",
    "generate.custom",
    "generate.cover",
    "generate.mashup",
    "generate.extend",
    "audio.upload",
    "audio.download",
    "voices",
    "controls.advanced",
    "speech"
  ],
  "metered_features": {},
  "suno_account": {
    "cancel_on": "2026-11-28T00:15:35Z",
    "credits_remaining": 8510,
    "download_credits_remaining": 67,
    "monthly_limit": 10000,
    "monthly_usage": 1490,
    "plan": {
      "name": "Premier Plan",
      "period": "year"
    },
    "renews_on": "2026-11-28T00:15:35Z"
  }
}
```

### Library
(omitted from the repo copy: user's private library titles/ids)

## Complete tool inventory

1. `mcp__suno__account_me` — Get the signed-in user
2. `mcp__suno__account_upgrade` — Get more credits
3. `mcp__suno__account_usage` — Get account usage
4. `mcp__suno__audio_analysis` — Retrieve audio analysis
5. `mcp__suno__audio_covers_create` — Create a cover
6. `mcp__suno__audio_create` — Generate audio
7. `mcp__suno__audio_download` — Download audio
8. `mcp__suno__audio_edit` — Edit a song
9. `mcp__suno__audio_extensions_create` — Create an extension
10. `mcp__suno__audio_full_song` — Get the whole song
11. `mcp__suno__audio_like` — Like or dislike a song
12. `mcp__suno__audio_listen` — Ask about audio
13. `mcp__suno__audio_listen_wait` — Wait for an answer about audio
14. `mcp__suno__audio_lyrics_alignment` — Retrieve lyric alignment
15. `mcp__suno__audio_mashups_create` — Create a mashup
16. `mcp__suno__audio_retrieve` — Retrieve audio
17. `mcp__suno__audio_unlike` — Unlike a song
18. `mcp__suno__audio_upload_complete` — Complete an upload
19. `mcp__suno__audio_upload_create` — Start an upload
20. `mcp__suno__audio_wait` — Wait for an audio clip to become playable
21. `mcp__suno__library_liked` — List liked suno.com songs
22. `mcp__suno__library_list` — List suno.com songs
23. `mcp__suno__library_search` — Search suno.com songs
24. `mcp__suno__playlists_add_clips` — Add songs to a playlist
25. `mcp__suno__playlists_create` — Create a playlist
26. `mcp__suno__playlists_list` — List playlists
27. `mcp__suno__playlists_list_clips` — List the songs in a playlist
28. `mcp__suno__playlists_remove_clips` — Remove songs from a playlist
29. `mcp__suno__sounds_create` — Generate a sound
30. `mcp__suno__speech_create` — Generate speech
31. `mcp__suno__voices_list` — List suno.com voices
32. `mcp__suno__voices_start` — Start creating a voice
33. `mcp__suno__workspaces_create` — Create a workspace
34. `mcp__suno__workspaces_list` — List workspaces
35. `mcp__suno__workspaces_update_clips` — File songs in a workspace

### 1. `mcp__suno__account_me`

Get the signed-in user

Returns the signed-in suno.com user's public profile. Only a suno.com sign-in can call it; an API key receives 403 `user_principal_required`.

exec tool declaration:
```ts
declare const tools: { mcp__suno__account_me(args: {}): Promise<CallToolResult>; };
```

### 2. `mcp__suno__account_upgrade`

Get more credits

Call this when a user signed in with Suno is out of credits (a creation tool
answered 402) or asks how to get more. Shows a button that opens suno.com to
upgrade their plan or buy credits, and returns the same link as `url` to
share where the button can't show.

exec tool declaration:
```ts
declare const tools: { mcp__suno__account_upgrade(args: {}): Promise<CallToolResult>; };
```

### 3. `mcp__suno__account_usage`

Get account usage

Returns the account's plan and current usage against metered features. For a suno.com sign-in, `suno_account` reports song-generation credits: uploads, library reads and organizing spend none, and uploads have no count limit.

exec tool declaration:
```ts
declare const tools: { mcp__suno__account_usage(args: {}): Promise<CallToolResult>; };
```

### 4. `mcp__suno__audio_analysis`

Retrieve audio analysis

Returns what the clip sounds like and its musical timing map. `terms` and
`labels` describe the audio itself, as heard by a tagging model rather than
taken from the prompt: the voice, instruments, genre, mood and how polished
the mix is. Use them to check a take against what was asked for, or to
compare takes and pick one, e.g. for a video.

The timing map has every beat with its position in the bar, the tempo, the
meter, structural sections and the key. This is what syncing video to music
needs, e.g. cutting on every downbeat (`bar_position: 1`) or changing scene
where a section starts. Sections that share a `label` repeat the same
material, so a recurring label is usually the chorus. For word timings use
`GET /v0/audio/{id}/lyrics-alignment`.

Analysis is a separate model run, so it is not ready the moment the clip
is. The first request starts the run; it is not charged, and repeating it
does not start a second one. The beats (with `bpm`, `time_signature` and
`key`), the sections (with `duration_s`) and the description (`terms` and
`labels`) are separate runs, and each part is served as soon as its run
completes, even while `status` is still `processing`. A run that fails is
tried again, up to three times in all, so a part can arrive minutes later.

`status` is `processing` while a run is expected, in flight or due to be
tried again; poll until it leaves `processing`, typically within a minute.
It is then `complete` when at least one part succeeded, or `unavailable`
when none did. Either way no further run starts, so stop polling; a part
left empty or null failed every try. `key` can also be null when the key
could not be determined.

A song in the caller's own suno.com library is analysed too, for a token
with `library:read`, five at a time: the rest read `processing` until one
of those finishes.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_analysis(args: {
  // Audio clip ID.
  id: string;
}): Promise<CallToolResult>; };
```

### 5. `mcp__suno__audio_covers_create`

Create a cover

Creates a new audio clip by covering an existing one with a new style or voice. The source must be `complete` (`400` otherwise). A voice always sings, so supplying voice_id keeps the vocals even with no lyrics. Signed in with Suno, the source may also be any suno.com song you may remix there: `404` if you can't see it, `403` if you can't remix it, `503` while it is still finishing. A cover always takes its source's title: there is no `title` field.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_covers_create(args: {
  // Optional generation-control sliders, each a 0–1 fraction (suno.com shows the same values as 0–100%) but `variety`, a whole number 0–4. Omit a slider to leave the model's own default alone — there is no value that means "no change", so `0` is a real setting, not an unset one. Requires the advanced-controls grant on your plan; sending one without it returns 403, and a value outside 0–1 returns 400.
  controls?: {
  // How closely the result resembles the source clip's audio. Low reinterprets freely; high stays near the original.
  audio_influence?: number;
  // How strongly the `style` tags are followed. Low is loose interpretation; high adheres tightly.
  style_influence?: number;
  // suno.com's Variety: how far the `style` tags are reinterpreted before the song is made. 0 Off (the tags as written), 1 Normal, 2 High, 3 Extra, 4 Max (a radical departure). A whole number; anything else returns 400. Omit it to keep the model's default. Signed in with Suno, it is not a paid feature.
  variety?: number;
  // How far the result may drift from expected results. Low stays conventional; high goes experimental.
  weirdness?: number;
};
  // Target length of the generated audio in seconds, 15–360. Omit to let the model choose. A value outside the range returns 400; the result is a target, not a guarantee.
  duration?: number;
  // Audio clip ID.
  id: string;
  // Opaque key for safely retrying a creation request. Keys contain 1–255 bytes,
  // are scoped to the authenticated account across all supported creation
  // operations, and are retained for at least 24 hours. Repeating the same key
  // with the same operation and parameters returns the original resource and sets
  // `Idempotency-Replayed: true`; reusing it with different input returns `409`.
  // A replay never re-emits webhooks. Audio replays return the current clip
  // status from a live read.
  idempotency_key?: string;
  // Lyrics to sing. The source's lyrics are not carried over: omitted, the cover is instrumental unless `voice_id` is set, so pass the source's lyrics to keep its vocals.
  lyrics?: string;
  // suno.com's Max Mode: more compute to keep the song consistent throughout, at a multiple of the song's credits. Set it only when the user asks for Max Mode by name, and only on the songs they ask it for; never turn it on yourself to improve a song. Only for a suno.com user's song on a plan with Max Mode: an API key or `test_mode` returns 400, and a plan without it returns 403.
  max_mode?: boolean;
  // Generation model label. Omit to use your plan's default. Labels beyond the default are granted per plan: an unknown label returns 400, one your plan does not hold returns 403. `GET /v0/account/usage` lists the labels you may send as `allowed_models`.
  model?: string;
  // Styles to steer away from (e.g. "polka, accordion"). Requires the advanced- controls grant on your plan; sending it without returns 403.
  negative_style?: string;
  // New style or genre tags to apply.
  style?: string;
  // Defaults to the source clip's title.
  title?: string;
  // ID of a voice to use, from POST /v0/voices. A voice always sings, so supplying one keeps the vocals even with no lyrics. The voice must belong to your account and be "ready" — an unknown voice returns 404, one still processing returns 400. Signed in with Suno, it is instead one of your suno.com voices, from GET /v0/voices.
  voice_id?: string;
  // A workspace to file the new song in, from `GET /v0/workspaces`. Only for a suno.com user's song: an API key or `test_mode` returns 400, and a workspace the user may not add to returns 403.
  workspace_id?: string;
}): Promise<CallToolResult>; };
```

### 6. `mcp__suno__audio_create`

Generate audio

Generates a new audio clip in one of two modes. **Simple:** `description`
alone; the lyrics and style are written for you. **Custom:** `lyrics`, usually
with `style` and `title`. Mixing the modes returns a `400`: `description` takes
no `style`, and no `lyrics` unless `instrumental` is `true`. With
`instrumental: true`, `lyrics` and `description` may both be omitted. For a
suno.com user, simple mode can also work from up to 10 of their songs in
`reference_audio_ids`, to remix, sample, remaster, restyle, mash up or split
stems from them, with `description` saying what to do. For a straight cover,
extension or two-song mashup, the dedicated routes give more control. Poll
`GET /v0/audio/{id}` for the result: the clip is playable once `status` is
`streaming`.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_create(args: { controls?: { audio_influence?: number; style_influence?: number; variety?: number; weirdness?: number; }; description?: string; duration?: number; duration_guidance?: boolean; duration_strict?: boolean; idempotency_key?: string; instrumental?: boolean; lyrics?: string; max_mode?: boolean; model?: string; negative_style?: string; reference_audio_ids?: Array<string>; style?: string; title?: string; vocal_gender?: "male" | "female"; voice_id?: string; workspace_id?: string; }): Promise<CallToolResult>; };
```

### 7. `mcp__suno__audio_download`

Download audio

Returns a URL for one of the signed-in suno.com user's own songs, as `mp3`
(default) or `wav`, under suno.com's own download rules and download
credits. Requires the `audio.download` feature. Only for a suno.com user
whose token grants `download`; an API key gets 403.

Call without `confirm` first. If the answer is `requires_credit`, the
download would spend one of the user's download credits: ask the user,
and only with their approval call again with `confirm: true`. Any format
may answer `processing` while suno.com prepares the file, including for a
song that is still finishing; call again, no more than once a second. The
`audio-download` MCP tool waits out `processing` itself for up to about 50
seconds: if it still answers `processing`, call audio-download again, never
audio-wait.

`url` saves the file under the song's title. Hosts that show apps render a
download button for it; elsewhere, share or fetch `url`.

Refusals from suno.com carry a `reason` alongside `error` and `code`:
`quota_exhausted` (402, `insufficient_credits`), `no_permission` (403,
`forbidden`), `plan_required` (403, `feature_not_on_plan`), `invalid_asset`
(404, `not_found`), `format_unsupported` / `invalid_format` (400,
`invalid_request`), `rate_limited` (429, `rate_limited`; back off) and
`daily_limit_exceeded` (429, `quota_exceeded`; stop until it resets).

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_download(args: {
  // Spend a download credit if the song needs one. Send only after the user approves a `requires_credit` answer.
  confirm?: boolean;
  format?: "mp3" | "wav";
  // Audio clip ID.
  id: string;
}): Promise<CallToolResult>; };
```

### 8. `mcp__suno__audio_edit`

Edit a song

Changes the title, lyrics or both of a song in the signed-in suno.com user's
library. It never changes who can see the song. Only for a suno.com user
whose token grants `library:write`; an API key gets 403.

Titles and lyrics pass the same content check suno.com runs: disallowed text
returns 400.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_edit(args: {
  // Audio clip ID.
  id: string;
  lyrics?: string;
  title?: string;
}): Promise<CallToolResult>; };
```

### 9. `mcp__suno__audio_extensions_create`

Create an extension

Continues the source clip (`id`) from `continue_at` seconds. The new clip
contains **only the continuation**, not the source followed by it — join the
chain with `POST /v0/audio/{id}/full-song` to get the whole song. The source
must be `complete` (`400` otherwise), and `continue_at` is relative to the
source clip's own audio.
A response with `clip_ids` made one continuation per id, each the end of its
own chain: extend or join the one you want, not both.
Signed in with Suno, the source may also be any suno.com song you may remix
there: `404` if you can't see it, `403` if you can't remix it, `503` while it
is still finishing. A chain that starts at such a song joins with `full-song`
like any other.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_extensions_create(args: {
  // Seconds into the source clip to continue from.
  continue_at: number;
  // Optional generation-control sliders, each a 0–1 fraction (suno.com shows the same values as 0–100%) but `variety`, a whole number 0–4. Omit a slider to leave the model's own default alone — there is no value that means "no change", so `0` is a real setting, not an unset one. Requires the advanced-controls grant on your plan; sending one without it returns 403, and a value outside 0–1 returns 400.
  controls?: {
  // How closely the continuation resembles the source clip's audio. Low drifts from the original; high stays near it.
  audio_influence?: number;
  // How strongly the `style` tags are followed. Low is loose interpretation; high adheres tightly.
  style_influence?: number;
  // suno.com's Variety: how far the `style` tags are reinterpreted before the song is made. 0 Off (the tags as written), 1 Normal, 2 High, 3 Extra, 4 Max (a radical departure). A whole number; anything else returns 400. Omit it to keep the model's default. Signed in with Suno, it is not a paid feature.
  variety?: number;
  // How far the result may drift from expected results. Low stays conventional; high goes experimental.
  weirdness?: number;
};
  // Target length of the generated audio in seconds, 15–360. Omit to let the model choose. A value outside the range returns 400; the result is a target, not a guarantee.
  duration?: number;
  // Audio clip ID.
  id: string;
  // Opaque key for safely retrying a creation request. Keys contain 1–255 bytes,
  // are scoped to the authenticated account across all supported creation
  // operations, and are retained for at least 24 hours. Repeating the same key
  // with the same operation and parameters returns the original resource and sets
  // `Idempotency-Replayed: true`; reusing it with different input returns `409`.
  // A replay never re-emits webhooks. Audio replays return the current clip
  // status from a live read.
  idempotency_key?: string;
  // Force a vocal-free continuation. Omitted, the extension matches the source: a source with vocals keeps singing, an instrumental source stays instrumental. A voice_id always sings, so it takes precedence over this flag.
  instrumental?: boolean;
  // Lyrics for the continuation. Omit to let the model continue the source's lyrics.
  lyrics?: string;
  // suno.com's Max Mode: more compute to keep the song consistent throughout, at a multiple of the song's credits. Set it only when the user asks for Max Mode by name, and only on the songs they ask it for; never turn it on yourself to improve a song. Only for a suno.com user's song on a plan with Max Mode: an API key or `test_mode` returns 400, and a plan without it returns 403.
  max_mode?: boolean;
  // Generation model label. Omit to use your plan's default. Labels beyond the default are granted per plan: an unknown label returns 400, one your plan does not hold returns 403. `GET /v0/account/usage` lists the labels you may send as `allowed_models`.
  model?: string;
  // Styles to steer away from (e.g. "polka, accordion"). Requires the advanced- controls grant on your plan; sending it without returns 403.
  negative_style?: string;
  // Style or genre tags for the continuation.
  style?: string;
  // Defaults to the source clip's title.
  title?: string;
  // ID of a voice to sing the continuation. Supplying one implies vocals, so it overrides an instrumental source. The voice must belong to your account and be "ready" — an unknown voice returns 404, one still processing returns 400. Signed in with Suno, it is instead one of your suno.com voices, from GET /v0/voices.
  voice_id?: string;
  // A workspace to file the new song in, from `GET /v0/workspaces`. Only for a suno.com user's song: an API key or `test_mode` returns 400, and a workspace the user may not add to returns 403.
  workspace_id?: string;
}): Promise<CallToolResult>; };
```

### 10. `mcp__suno__audio_full_song`

Get the whole song

Joins an extension (`id`) and everything it continues from into a single
track. The whole chain is resolved automatically, so you only name the last
extension. When an extension call returned `clip_ids`, name the one you
want: each is a separate chain end. Every clip in the chain must be `complete` (`400` otherwise), and
a chain is joinable up to 20 segments — the source plus 19 extensions. A
longer chain returns `400` and there is no partial join.

Signed in with Suno, a chain may start at a suno.com song you extended: the
join begins with that song and the songs it continues on suno.com, and
`concat_clip_ids` starts with its id; those earlier suno.com songs don't
count toward the 20. `404` if you can no longer see it,
`403` if you can no longer remix it.

Joining is free: no credits, no usage limit, since the extends that built
the chain were already metered. It is idempotent per chain — joining the
same chain again returns the first join's clip (with its current status)
instead of producing a second one, so retries are safe. A failed join can
be retried up to 3 times per chain; after that the failed clip is returned
instead of starting another job. A join that never reports back is retried
the same way once no worker could still finish it (30 minutes), which
also counts against the 3 attempts. Requires the same `generate.extend`
feature as creating the extension.

Poll `GET /v0/audio/{id}` for the result rather than blocking on the stream
endpoint — a cold join can exceed its wait window.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_full_song(args: {
  // Audio clip ID.
  id: string;
  // Opaque key for safely retrying a creation request. Keys contain 1–255 bytes,
  // are scoped to the authenticated account across all supported creation
  // operations, and are retained for at least 24 hours. Repeating the same key
  // with the same operation and parameters returns the original resource and sets
  // `Idempotency-Replayed: true`; reusing it with different input returns `409`.
  // A replay never re-emits webhooks. Audio replays return the current clip
  // status from a live read.
  idempotency_key?: string;
}): Promise<CallToolResult>; };
```

### 11. `mcp__suno__audio_like`

Like or dislike a song

Likes a song for the signed-in suno.com user, as suno.com's like button does,
or with `dislike: true` dislikes it, as its dislike button does. Either one
replaces the other. Any song the user can open by link may be liked or
disliked; one they cannot is a 404. Only for a suno.com user whose token
grants `library:write`; an API key gets 403.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_like(args: {
  // Dislike the song instead of liking it.
  dislike?: boolean;
  // Audio clip ID.
  id: string;
}): Promise<CallToolResult>; };
```

### 12. `mcp__suno__audio_listen`

Ask about audio

Asks a question about a finished clip. Suno's music agent listens to it
and measures it, then replies in text. Ask about anything you can hear:
the genre, mood and instruments, what the vocals do, how a section builds,
how polished the mix is, or how two parts compare. Tempo and key are
measured by Suno's own models. To get data back, ask for JSON and name the
fields, e.g. "End with a JSON block with bpm and key". The answer then ends
with a fenced `json` block holding those fields.

Returns a listen with `status: processing` at once. Read the answer with
getAudioListen (the `audio-listen-wait` MCP tool) by its `id`; it usually
takes under a minute. Nothing is made or changed and nothing is charged. A
caller may have five questions unanswered at once; one more is a 429
`concurrency_limit_exceeded`, and reading an answer frees its place. Past
200 questions in a UTC day, one more is a 429 `quota_exceeded`. The
answer never names a real artist or recording and quotes at most two lines
of lyrics. For a beat-by-beat timing map use audio-analysis, and for word
timings audio-lyrics-alignment.

Only a suno.com sign-in can call it; an API key receives 403
`user_principal_required`. A song in the caller's own suno.com library can
be asked about too, for a token with `library:read`.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_listen(args: {
  // Audio clip ID.
  id: string;
  // What to ask about the audio. Name the fields you want when asking for JSON.
  question: string;
}): Promise<CallToolResult>; };
```

### 13. `mcp__suno__audio_listen_wait`

Wait for an answer about audio

Reads a question asked with listenToAudio (the `audio-listen` MCP tool) by
the `id` it returned. `status` is `processing` until the agent answers, then
`complete` with the `answer`, or `error` with the reason. The
`audio-listen-wait` MCP tool checks every few seconds for up to about 50: if
it still answers `processing`, call audio-listen-wait again with the same id.
An answer stays readable for a day. Only a suno.com sign-in can call it; an
API key receives 403 `user_principal_required`.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_listen_wait(args: {
  // The listen id listenToAudio returned.
  id: string;
}): Promise<CallToolResult>; };
```

### 14. `mcp__suno__audio_lyrics_alignment`

Retrieve lyric alignment

Returns the clip's lyrics with the span of audio each word is sung over —
what a karaoke or caption display needs.

Alignment is produced by a separate model run, so it is not ready the
moment the clip is. Poll until `status` leaves `processing`, or subscribe
to the `audio.alignment.ready` webhook. The first request for a clip that
has no alignment yet starts the run; it is not charged, and repeating it
does not start a second one.

`status` is `complete` once the words are in hand (`words` is legitimately
empty for an instrumental), `processing` while a run is expected or in
flight, and `unavailable` when no alignment could be produced — a final
answer, so stop polling on it. Word timings are best-effort: a word the
aligner could not place carries `success: false` and a span inferred from
its neighbour.

A song in the caller's own suno.com library, for a token with
`library:read`, gets the alignment suno.com stored for it. No run starts
for one, so a song suno.com never aligned is `unavailable`, though one made
in the last ten minutes reads `processing` while suno.com aligns it.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_lyrics_alignment(args: {
  // Audio clip ID.
  id: string;
}): Promise<CallToolResult>; };
```

### 15. `mcp__suno__audio_mashups_create`

Create a mashup

Blends the source clip (`id`) with one additional clip. Mashups currently take
exactly two parents. Both must be `complete` (`400` otherwise).
Signed in with Suno, either may also be any suno.com song you may remix there:
`404` if you can't see it, `403` if you can't remix it, `503` while it is still
finishing.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_mashups_create(args: {
  // Audio clip ID to blend with the source clip.
  additional_audio_id: string;
  // Optional generation-control sliders, each a 0–1 fraction (suno.com shows the same values as 0–100%) but `variety`, a whole number 0–4. Omit a slider to leave the model's own default alone — there is no value that means "no change", so `0` is a real setting, not an unset one. Requires the advanced-controls grant on your plan; sending one without it returns 403, and a value outside 0–1 returns 400.
  controls?: {
  // How closely the result resembles the two source clips' audio. Low reinterprets freely; high stays near the originals.
  audio_influence?: number;
  // How strongly the `style` tags are followed. Low is loose interpretation; high adheres tightly.
  style_influence?: number;
  // suno.com's Variety: how far the `style` tags are reinterpreted before the song is made. 0 Off (the tags as written), 1 Normal, 2 High, 3 Extra, 4 Max (a radical departure). A whole number; anything else returns 400. Omit it to keep the model's default. Signed in with Suno, it is not a paid feature.
  variety?: number;
  // How far the result may drift from expected results. Low stays conventional; high goes experimental.
  weirdness?: number;
};
  // Target length of the generated audio in seconds, 15–360. Omit to let the model choose. A value outside the range returns 400; the result is a target, not a guarantee.
  duration?: number;
  // Audio clip ID.
  id: string;
  // Opaque key for safely retrying a creation request. Keys contain 1–255 bytes,
  // are scoped to the authenticated account across all supported creation
  // operations, and are retained for at least 24 hours. Repeating the same key
  // with the same operation and parameters returns the original resource and sets
  // `Idempotency-Replayed: true`; reusing it with different input returns `409`.
  // A replay never re-emits webhooks. Audio replays return the current clip
  // status from a live read.
  idempotency_key?: string;
  lyrics?: string;
  // suno.com's Max Mode: more compute to keep the song consistent throughout, at a multiple of the song's credits. Set it only when the user asks for Max Mode by name, and only on the songs they ask it for; never turn it on yourself to improve a song. Only for a suno.com user's song on a plan with Max Mode: an API key or `test_mode` returns 400, and a plan without it returns 403.
  max_mode?: boolean;
  // Generation model label. Omit to use your plan's default. Labels beyond the default are granted per plan: an unknown label returns 400, one your plan does not hold returns 403. `GET /v0/account/usage` lists the labels you may send as `allowed_models`.
  model?: string;
  // Styles to steer away from (e.g. "polka, accordion"). Requires the advanced- controls grant on your plan; sending it without returns 403.
  negative_style?: string;
  // Style or genre tags.
  style?: string;
  title?: string;
  // A workspace to file the new song in, from `GET /v0/workspaces`. Only for a suno.com user's song: an API key or `test_mode` returns 400, and a workspace the user may not add to returns 403.
  workspace_id?: string;
}): Promise<CallToolResult>; };
```

### 16. `mcp__suno__audio_retrieve`

Retrieve audio

Retrieves the current state of an audio clip. Poll after any creation call.
A generated clip is playable once `status` reaches `streaming`: play it
through `GET /v0/audio/{id}/stream`, or share `song_url` when it is present.
Keep polling until `complete` or `error` only when you need the finished
file or its duration. It reads one clip per call, by `id`; through MCP,
audio-wait takes several clips' `ids` at once.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_retrieve(args: {
  // Audio clip ID.
  id: string;
}): Promise<CallToolResult>; };
```

### 17. `mcp__suno__audio_unlike`

Unlike a song

Clears the signed-in suno.com user's like or dislike on a song. Only for a
suno.com user whose token grants `library:write`; an API key gets 403.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_unlike(args: {
  // Audio clip ID.
  id: string;
}): Promise<CallToolResult>; };
```

### 18. `mcp__suno__audio_upload_complete`

Complete an upload

Starts processing the file sent to an upload session's `upload_url` or
`upload_page_url`, exactly as `POST /v0/audio/uploads` would. Returns `409`
if the file is sent again while this call runs, and while no file has arrived: if the user is uploading through the page, wait
until they say it finished. Completing the same session again returns `409`
while the first call is still starting it, then the clip that call started.

Poll `GET /v0/audio/{id}` until `status` is `complete` or `error`.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_upload_complete(args: {
  // Upload session ID, from POST /v0/audio/upload-sessions.
  id: string;
  // Optional display title, replacing the one the session was created with.
  title?: string;
}): Promise<CallToolResult>; };
```

### 19. `mcp__suno__audio_upload_create`

Start an upload

Starts an upload whose file goes straight to storage rather than through the
request body. Use it for files too large to send inline, and whenever the
file's bytes are not at hand, such as a file the user attached in a chat.
Call it as soon as the user wants to use their own audio, before they attach
anything, so the uploader is where they drop the file.

When the user attached the file in this chat, pass it as `file`: the upload
starts at once and the response is the clip, as from
`POST /v0/audio/upload-sessions/{id}/complete`, with nothing left to send.

Otherwise the response holds the clip `id` the upload will become and two ways to send
the file, each good for one file for one hour:

- `upload_url`: send the raw file bytes in one HTTP `PUT`, for example
  `curl -T song.mp3 "<upload_url>"`. Quote the URL.
- `upload_page_url`: a page where the user picks the file in their browser.
  Give it to the user when you cannot read the file yourself.

If the user attached a file in the chat but you passed no `file`, or the call
refused it, and you can't `PUT` it yourself, still call this endpoint so the
uploader opens, then ask them to pick the same file there or at `upload_page_url`.

Both are credentials for this one upload, so share them only with the
person uploading. Once the file is sent, call
`POST /v0/audio/upload-sessions/{id}/complete`, then poll
`GET /v0/audio/{id}` as for `POST /v0/audio/uploads`. Formats and limits are
the same as that endpoint's. When the uploader reports the upload, carry on
with what the user asked for, such as a cover of it, without asking again.

This endpoint requires the `audio.upload` feature.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_upload_create(args: {
  // The audio file the user attached in this chat. Pass the attachment
  // itself; the chat app turns it into this object.
  file?: { download_url: string; file_id: string; file_name?: string; mime_type?: string; };
  // Optional display title. Pass the file's name if you know it.
  title?: string;
}): Promise<CallToolResult>; };
```

### 20. `mcp__suno__audio_wait`

Wait for an audio clip to become playable

Call this after audio-create, audio-covers-create, audio-mashups-create,
audio-extensions-create or audio-full-song instead of polling audio-retrieve.
It checks every few seconds and returns the clip as soon as `status` is
`streaming` (the clip plays live and `song_url` works), `complete` or `error`,
or after about 50 seconds with the clip still pending. If it is still pending,
call audio-wait again. A creation that returned `clip_ids` made one song per id:
call audio-wait once with all of them in `ids`, so one player shows every song. Once
every one is settled it returns the first song's fields with every song, in order, under
`clips`, a clip it couldn't read as its `id` and `error`.

exec tool declaration:
```ts
declare const tools: { mcp__suno__audio_wait(args: {
  // Audio clip ID returned by a creation tool.
  id?: string;
  // Every clip ID a creation returned in `clip_ids`, instead of `id`. At most 4 per call: for more, call audio-wait again with the rest.
  ids?: Array<string>;
  // `playable` returns once the clip is streaming; `complete` waits for the finished file.
  until?: "playable" | "complete";
}): Promise<CallToolResult>; };
```

### 21. `mcp__suno__library_liked`

List liked suno.com songs

For a user signed in with Suno whose token grants `library:read`: lists the songs
they liked on suno.com, by anyone, most recently liked first, as Liked Songs does.
Each item is the audio-retrieve object with the creator's `handle`; play it at its
`song_url`. Songs since hidden, trashed, or by a creator who blocked the user are
left out, so a page can be short; keep paging with `next_cursor`. Through MCP,
items leave out `metadata.lyrics`. An API-key account, or a token without the
scope, gets a 403.

exec tool declaration:
```ts
declare const tools: { mcp__suno__library_liked(args: {
  // The `next_cursor` of the previous page.
  cursor?: string;
  limit?: number;
}): Promise<CallToolResult>; };
```

### 22. `mcp__suno__library_list`

List suno.com songs

For a user signed in with Suno whose token grants `library:read`: lists the
finished songs in their suno.com library, newest first, as My Songs does. Each
item is the audio-retrieve object; play it at its `song_url`. Page with
`next_cursor`. Pass `workspace_id` to list what is in a workspace, and `liked`,
`visibility`, `downloaded` or `origin` to filter as My Songs does. For songs the
user liked by anyone, use library-liked. Through MCP, items leave out
`metadata.lyrics`; audio-retrieve returns them for the user's own songs. An
API-key account, or a token without the scope, gets a 403.

exec tool declaration:
```ts
declare const tools: { mcp__suno__library_list(args: {
  // The `next_cursor` of the previous page.
  cursor?: string;
  // Only songs the user has downloaded, or exported from Studio.
  downloaded?: boolean;
  // Only the user's own songs they have liked.
  liked?: boolean;
  limit?: number;
  // Only songs made this way, as My Songs' type filter names it.
  origin?: "upload" | "cover" | "extension" | "remaster";
  // Only public songs, or only private ones.
  visibility?: "public" | "private";
  // Only the user's own songs filed in this workspace, from workspaces-list. Collaborators' songs in a shared workspace are not listed.
  workspace_id?: string;
}): Promise<CallToolResult>; };
```

### 23. `mcp__suno__library_search`

Search suno.com songs

For a user signed in with Suno whose token grants `library:search`: lists the
finished songs in their suno.com library whose title or style contains `query`,
newest first. Use it to find a song the user names. Items, paging and filters are
those of library-list. An API-key account, or a token without the scope, gets a 403.

exec tool declaration:
```ts
declare const tools: { mcp__suno__library_search(args: {
  // The `next_cursor` of the previous page.
  cursor?: string;
  // Only songs the user has downloaded, or exported from Studio.
  downloaded?: boolean;
  // Only the user's own songs they have liked.
  liked?: boolean;
  limit?: number;
  // Only songs made this way, as My Songs' type filter names it.
  origin?: "upload" | "cover" | "extension" | "remaster";
  // Text the song's title or style contains.
  query?: string;
  // Only public songs, or only private ones.
  visibility?: "public" | "private";
  // Only the user's own songs filed in this workspace, from workspaces-list. Collaborators' songs in a shared workspace are not listed.
  workspace_id?: string;
}): Promise<CallToolResult>; };
```

### 24. `mcp__suno__playlists_add_clips`

Add songs to a playlist

Adds songs to a playlist the signed-in suno.com user owns. Each song that
could not be added is listed in `failed` with the reason.

exec tool declaration:
```ts
declare const tools: { mcp__suno__playlists_add_clips(args: {
  clip_ids: Array<string>;
  // Playlist ID.
  id: string;
}): Promise<CallToolResult>; };
```

### 25. `mcp__suno__playlists_create`

Create a playlist

Creates a playlist in the signed-in suno.com user's library, private unless
`visibility` is `public`. The name passes the same content check suno.com
runs: disallowed text returns 400.

exec tool declaration:
```ts
declare const tools: { mcp__suno__playlists_create(args: { description?: string; name: string; visibility?: "public" | "private"; }): Promise<CallToolResult>; };
```

### 26. `mcp__suno__playlists_list`

List playlists

Lists the playlists the signed-in suno.com user owns, most recently updated
first. Pass `next_cursor` back as `cursor`, with the same `query`, for the next
page; it is absent on the last. Use `query` to find a playlist the user names.

exec tool declaration:
```ts
declare const tools: { mcp__suno__playlists_list(args: {
  cursor?: string;
  limit?: number;
  // Text the playlist's name contains, ignoring case.
  query?: string;
}): Promise<CallToolResult>; };
```

### 27. `mcp__suno__playlists_list_clips`

List the songs in a playlist

Lists the songs in a playlist the signed-in suno.com user owns, in the
playlist's order. Each item is the audio-retrieve object with the creator's
`handle`; play it at its `song_url`. Songs since hidden, trashed, or by a creator
who blocked the user are left out, so a page can be short; keep paging with
`next_cursor`. Through MCP, items leave out `metadata.lyrics`. Another user's
playlist, an album, or an unknown id returns 404.

exec tool declaration:
```ts
declare const tools: { mcp__suno__playlists_list_clips(args: {
  // The `next_cursor` of the previous page.
  cursor?: string;
  // Playlist ID, from playlists-list.
  id: string;
  limit?: number;
}): Promise<CallToolResult>; };
```

### 28. `mcp__suno__playlists_remove_clips`

Remove songs from a playlist

Takes songs out of a playlist the signed-in suno.com user owns. The songs stay
in their library. Every requested id is listed in `removed`, including any that
were not in the playlist. Adding a song back puts it at the end, not where it was.

exec tool declaration:
```ts
declare const tools: { mcp__suno__playlists_remove_clips(args: {
  clip_ids: Array<string>;
  // Playlist ID.
  id: string;
}): Promise<CallToolResult>; };
```

### 29. `mcp__suno__sounds_create`

Generate a sound

Generates two short sound effects, one-shots or loops from a description, not
songs, as suno.com's Sounds does. Set `loop` for a seamless loop, and `tempo` and
`key` to fit it to a track. Both are ordinary clips, named in `clip_ids` — poll
`GET /v0/audio/{id}` for each. The model is chosen for you, and the length is up
to the model. Only a signed-in suno.com user can call it: the sounds land in their
suno.com library, each charged 1 credit like suno.com's Sounds. An API key receives 403 `user_principal_required`, and a
user on a suno.com plan below Pro (Free or Basic) 403 `feature_not_on_plan`.

exec tool declaration:
```ts
declare const tools: { mcp__suno__sounds_create(args: {
  // What the sound is, e.g. "rain on a tin roof" or "boom bap drums".
  description: string;
  // Opaque key for safely retrying a creation request. Keys contain 1–255 bytes,
  // are scoped to the authenticated account across all supported creation
  // operations, and are retained for at least 24 hours. Repeating the same key
  // with the same operation and parameters returns the original resource and sets
  // `Idempotency-Replayed: true`; reusing it with different input returns `409`.
  // A replay never re-emits webhooks. Audio replays return the current clip
  // status from a live read.
  idempotency_key?: string;
  // Musical key, major or minor. Omit to let the model choose.
  key?: "C" | "C#" | "D" | "D#" | "E" | "F" | "F#" | "G" | "G#" | "A" | "A#" | "B" | "Cm" | "C#m" | "Dm" | "D#m" | "Em" | "Fm" | "F#m" | "Gm" | "G#m" | "Am" | "A#m" | "Bm";
  // Make a seamless loop rather than a one-shot.
  loop?: boolean;
  // Beats per minute. Omit to let the model choose.
  tempo?: number;
  // Defaults to the description.
  title?: string;
}): Promise<CallToolResult>; };
```

### 30. `mcp__suno__speech_create`

Generate speech

Generates spoken-word audio. Exactly one of `script` (spoken verbatim) or
`prompt` (the AI writes the words) must be provided. Providing `style`
alongside `prompt` returns a `400`. The result is an ordinary clip — poll
`GET /v0/audio/{id}`, and stream or mint a playback URL for it the same way.
Speech always generates on the default model, so there is no `model` to
choose, and no `instrumental` — speech is the voice. Requires the speech grant
on your plan.

exec tool declaration:
```ts
declare const tools: { mcp__suno__speech_create(args: {
  // Keep a music bed under the speech. Default is no music at all.
  backing_music?: boolean;
  // Target length of the generated audio in seconds, 15–360. Omit to let the model choose. A value outside the range returns 400; the result is a target, not a guarantee.
  duration?: number;
  // Size AI-written words to `duration` so short targets produce short speech (on by default when `duration` is set). Only meaningful with `duration` — sending it alone returns 400. A `script` is never rewritten either way.
  duration_guidance?: boolean;
  // Guarantee the clip never runs longer than `duration` (on by default when `duration` is set): generation is hard-capped at the target, so audio that would overrun is truncated at the cap. Set false to keep `duration` as a soft target. Only meaningful with `duration` — sending it alone returns 400.
  duration_strict?: boolean;
  // Opaque key for safely retrying a creation request. Keys contain 1–255 bytes,
  // are scoped to the authenticated account across all supported creation
  // operations, and are retained for at least 24 hours. Repeating the same key
  // with the same operation and parameters returns the original resource and sets
  // `Idempotency-Replayed: true`; reusing it with different input returns `409`.
  // A replay never re-emits webhooks. Audio replays return the current clip
  // status from a live read.
  idempotency_key?: string;
  // Styles to steer away from (e.g. "polka, accordion"). Only valid alongside caller-supplied tags — sending it with `prompt` returns 400, since there are no tags of your own to steer. Requires the advanced-controls grant on your plan; sending it without returns 403.
  negative_style?: string;
  // What the speech should say; the AI writes the words. Exactly one of `script` or `prompt` is required. The spoken-word instruction shares the engine's prompt budget, so the cap is 2947 characters, or 2887 with `backing_music`.
  prompt?: string;
  // The words to speak, performed verbatim. Exactly one of `script` or `prompt` is required.
  script?: string;
  // Delivery tags (e.g. "calm narrator, warm"), and the music bed's style when `backing_music` is set. Only valid with `script` — sending it with `prompt` returns 400.
  style?: string;
  title?: string;
  // Force the gender of the generated vocals. Omit to let the model choose. A `voice_id` takes precedence — a named voice already has a gender — and any other value returns 400. Requires the advanced-controls grant on your plan; sending it without returns 403.
  vocal_gender?: "male" | "female";
  // Optional voice ID to speak in. Choose from the preset voices listed in the Quickstart, or, if your plan includes voice cloning, one of your own voices. The voice must belong to your account and be "ready" — an unknown voice returns 404, one still processing returns 400. Signed in with Suno, it is instead one of your suno.com voices, from GET /v0/voices.
  voice_id?: string;
  // A workspace to file the new clip in, from `GET /v0/workspaces`. Only for a suno.com user's clip: an API key or `test_mode` returns 400, and a workspace the user may not add to returns 403.
  workspace_id?: string;
}): Promise<CallToolResult>; };
```

### 31. `mcp__suno__voices_list`

List suno.com voices

For a user signed in with Suno: lists the voices in their suno.com library, newest
first. Pass a voice's `id` as `voice_id` to audio-create, speech-create,
audio-covers-create or audio-extensions-create to sing in it. `collection` picks
the user's own voices (the default) or the ones they loved. Page with
`next_cursor`. Pass `query` to find a voice by name or id instead of paging. A name
is searched only within `collection`, so if `own` has no match, try `loved`. An
API-key account gets a 403.

exec tool declaration:
```ts
declare const tools: { mcp__suno__voices_list(args: {
  collection?: "own" | "loved";
  // The `next_cursor` of the previous page.
  cursor?: string;
  limit?: number;
  // Text the voice's name contains, searched within `collection`, or a voice's id, which finds the user's own voice or any public one they may sing in.
  query?: string;
}): Promise<CallToolResult>; };
```

### 32. `mcp__suno__voices_start`

Start creating a voice

Call this as soon as a user signed in with Suno wants a custom voice, before
asking for any audio. Never ask them for recordings or files.

Returns a suno.com `url` where the user creates and verifies the voice. Once
it's ready it appears in voices-list, and its `id` sings as `voice_id`.
An API-key account gets a 409 and creates
voices with the recording, verification and create endpoints instead.

exec tool declaration:
```ts
declare const tools: { mcp__suno__voices_start(args: {}): Promise<CallToolResult>; };
```

### 33. `mcp__suno__workspaces_create`

Create a workspace

Creates a workspace in the signed-in suno.com user's library. The name and
description pass the same content check suno.com runs: disallowed text
returns 400, and 503 means the check could not run — retry later.

exec tool declaration:
```ts
declare const tools: { mcp__suno__workspaces_create(args: { description?: string; name: string; }): Promise<CallToolResult>; };
```

### 34. `mcp__suno__workspaces_list`

List workspaces

Lists the workspaces the signed-in suno.com user owns or was invited to, most
recent activity first. Pass `next_cursor` back as `cursor`, with the same
`query`, for the next page; it is absent on the last. Songs in no workspace are
not listed as one. Use `query` to find a workspace the user names.

exec tool declaration:
```ts
declare const tools: { mcp__suno__workspaces_list(args: {
  cursor?: string;
  // Text the workspace's name contains, ignoring case.
  query?: string;
}): Promise<CallToolResult>; };
```

### 35. `mcp__suno__workspaces_update_clips`

File songs in a workspace

Adds songs to a workspace and takes others out of it. A song is in at most one
workspace, so adding moves it out of the one it was in. A song the user may not
file or remove is left where it is and listed in `skipped`, so check it rather
than assuming every id moved. Workspace ids and playlist ids are different.

exec tool declaration:
```ts
declare const tools: { mcp__suno__workspaces_update_clips(args: {
  add?: Array<string>;
  // Workspace ID.
  id: string;
  remove?: Array<string>;
}): Promise<CallToolResult>; };
```

## Exact tool-call response envelopes

The decoded payloads above are repeated here inside the original result envelopes for completeness. No other Suno tools were invoked.

```json
[
  {
    "name": "mcp__suno__account_usage",
    "arguments": {},
    "result": {
      "status": "fulfilled",
      "value": {
        "content": [
          {
            "type": "text",
            "text": "{\"allowed_models\":[\"v6-mini\",\"v6\",\"v6-wild\"],\"features\":[\"generate.simple\",\"generate.custom\",\"generate.cover\",\"generate.mashup\",\"generate.extend\",\"audio.upload\",\"audio.download\",\"voices\",\"controls.advanced\",\"speech\"],\"metered_features\":{},\"suno_account\":{\"cancel_on\":\"2026-11-28T00:15:35Z\",\"credits_remaining\":8510,\"download_credits_remaining\":67,\"monthly_limit\":10000,\"monthly_usage\":1490,\"plan\":{\"name\":\"Premier Plan\",\"period\":\"year\"},\"renews_on\":\"2026-11-28T00:15:35Z\"}}"
          }
        ]
      }
    }
  },
  {
    "name": "mcp__suno__library_list",
    "arguments": {
      "limit": 10
    },
    "result": {
      "status": "fulfilled",
      "value": {
        "content": [
          {
            "type": "text",
            "text": "{\"items\":[{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_5470a75e-d353-4be2-b246-b80875fc82b4.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_5470a75e-d353-4be2-b246-b80875fc82b4.jpeg\",\"created_at\":\"2026-11-04T11:30:20.446Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"5470a75e-d353-4be2-b246-b80875fc82b4\",\"liked\":false,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ani],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs, Death growl],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope]\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":244.48,\"style\":\"Experimental Japanese visual kei cyberpunk art-rock anthem with gothic orchestral metal tension and slowcore contrast. Begin with a brief instrumental opening of isolated glassy bell-synth notes and distant bowed strings; verses stay narrow, dry, and intimate over a lurching half-time pulse, sub-bass, and clipped electronic percussion. Use sudden cut-to-silence breaks, unexpected tempo pivots, reversed impacts, and a brief virtuosic lead-piano / synthesizer solo; build into a double-time arena chorus with a piercing male tenor, theatrical chest-to-falsetto switches, expressive vibrato glides, controlled consonant attacks, and memorable Japanese melodic phrasing. Add discreet female whisper-chant responses and layered male harmonies. Make the climax vocal wet, wide, and huge while keeping the lead intelligible; widen the chorus, then strip back to a fragile open-ended instrumental outro. Modulate upward for the final battle-cry lift, then leave the ending unresolved. Detailed cinematic depth, punchy controlled low end, glossy but articulate top end, release-ready studio mix and loud master.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/5470a75e-d353-4be2-b246-b80875fc82b4\",\"status\":\"complete\",\"title\":\"盤をひっくり返せ\",\"visibility\":\"private\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_aa537e81-b259-4996-9eeb-f5c23f90bc41.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_aa537e81-b259-4996-9eeb-f5c23f90bc41.jpeg\",\"created_at\":\"2026-11-04T11:30:20.446Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"aa537e81-b259-4996-9eeb-f5c23f90bc41\",\"liked\":false,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ani],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs, Death growl],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope]\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":284.88,\"style\":\"Experimental Japanese visual-kei art rock with cinematic gothic metal and cyberpunk breakbeat accents; open with a brief vocal-free slowcore passage of bell-like bounce synthesizer, bowed strings, and distant metallic impacts; verses stay narrow, dry, and controlled over syncopated pulse, distorted synth bass, and ominous orchestral details; use sudden stop-time silence, unexpected half-time and double-time shifts, rubato transitions, and dramatic key changes; build into wide arena choruses with soaring expressive male tenor, piercing vibrato, smooth falsetto lifts, soulful runs, clipped consonants, and layered chant harmonies; add occasional female whisper-chant responses, panned vocoder textures, reverse effects, and cinematic impacts; bridge turns sparse and unsettling before a cathartic final chorus; finish with a wordless instrumental outro, unresolved but hopeful; wet, wide vocal reverb in climaxes, verses dry and intimate, clear centered lead, deep controlled low end, expansive stereo depth, polished release-ready mastering.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/aa537e81-b259-4996-9eeb-f5c23f90bc41\",\"status\":\"complete\",\"title\":\"盤を裂け\",\"visibility\":\"private\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_5e76d2e8-37c0-43d3-8792-fc373227e183.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_5e76d2e8-37c0-43d3-8792-fc373227e183.jpeg\",\"created_at\":\"2026-11-04T11:24:58.589Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"5e76d2e8-37c0-43d3-8792-fc373227e183\",\"liked\":false,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs, Death growl],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],[ani]\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope],\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":242.84,\"style\":\"Experimental Japanese visual-kei cyberpunk art rock fused with cinematic gothic metal and slowcore dynamics. Open with an instrumental-only, sparse bell motif, bowed strings, and a sudden reversed impact; verses stay dry, narrow, intimate, and rhythmically uneasy. Use a breathy male high tenor with theatrical range, controlled low-mid phrasing, clipped consonants, expressive vibrato, falsetto lifts, and brief soulful runs; add restrained female whisper-chant responses and layered male harmonies. Build through syncopated percussion and distorted synth bass, with abrupt silence before a wide, wet, soaring arena chorus and stacked chant hook. Add a cyberpunk break with vocoder fragments, metallic percussion, and a short expressive electric-guitar solo; shift tempo and key between sections for disorienting momentum, then return to the central bell motif in an instrumental outro. Rich stereo depth, focused center vocal, punchy controlled low end, polished high-detail release-ready master.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/5e76d2e8-37c0-43d3-8792-fc373227e183\",\"status\":\"complete\",\"title\":\"盤の向こうで\",\"visibility\":\"private\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_82915e34-a706-4a75-a8a0-ffa7425b0232.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_82915e34-a706-4a75-a8a0-ffa7425b0232.jpeg\",\"created_at\":\"2026-11-04T11:24:58.589Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"82915e34-a706-4a75-a8a0-ffa7425b0232\",\"liked\":true,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs, Death growl],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],[ani]\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope],\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":213.6,\"style\":\"Experimental Japanese visual-kei cyberpunk art rock fused with cinematic gothic metal and slowcore dynamics. Open with an instrumental-only, sparse bell motif, bowed strings, and a sudden reversed impact; verses stay dry, narrow, intimate, and rhythmically uneasy. Use a breathy male high tenor with theatrical range, controlled low-mid phrasing, clipped consonants, expressive vibrato, falsetto lifts, and brief soulful runs; add restrained female whisper-chant responses and layered male harmonies. Build through syncopated percussion and distorted synth bass, with abrupt silence before a wide, wet, soaring arena chorus and stacked chant hook. Add a cyberpunk break with vocoder fragments, metallic percussion, and a short expressive electric-guitar solo; shift tempo and key between sections for disorienting momentum, then return to the central bell motif in an instrumental outro. Rich stereo depth, focused center vocal, punchy controlled low end, polished high-detail release-ready master.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/82915e34-a706-4a75-a8a0-ffa7425b0232\",\"status\":\"complete\",\"title\":\"神の遊戯\",\"visibility\":\"public\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_ac4f2c8d-aafe-4dae-8153-6d0edd95f0f4.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_ac4f2c8d-aafe-4dae-8153-6d0edd95f0f4.jpeg\",\"created_at\":\"2026-11-04T11:22:54.706Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"ac4f2c8d-aafe-4dae-8153-6d0edd95f0f4\",\"liked\":false,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],[ani song],\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope],\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":257.72,\"style\":\"Experimental Japanese visual kei cyberpunk art-rock anthem with cinematic gothic metal and slowcore contrast. Open on a brief vocal-free passage of isolated bouncing bell synth, bowed low strings, and distant metallic impacts; keep the first verse dry, narrow, restrained, and rhythmically rubato over sparse sub pulses. Layer distorted synth bass, orchestral strings, and syncopated electronic percussion gradually. Break suddenly into near-silence before a huge arena chorus with wide soaring male tenor, sharp consonant attacks, expressive falsetto flips, long electric-vibrato glides, soulful runs, and layered male chant answers. Use a surprising half-time cyberpunk break, then an accelerating double-time lift and a brief harmonic key rise into the final chorus. Vocoder-like whispered counterlines and reversed transitions add tension; make the climax wet, wide, and spacious while keeping the lead centered and intelligible. Finish with a vocal-free unresolved instrumental outro, aching but open-ended. Detailed stereo depth, punchy controlled low end, glossy upper detail, polished release-ready loud master.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/ac4f2c8d-aafe-4dae-8153-6d0edd95f0f4\",\"status\":\"complete\",\"title\":\"王冠のない王\",\"visibility\":\"private\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_d9f1b9ec-f8a9-4f50-862f-b05cc065f1df.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_d9f1b9ec-f8a9-4f50-862f-b05cc065f1df.jpeg\",\"created_at\":\"2026-11-04T11:22:54.705Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"d9f1b9ec-f8a9-4f50-862f-b05cc065f1df\",\"liked\":true,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],[ani song],\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope],\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":244.96,\"style\":\"Experimental Japanese visual-kei cyberpunk art-rock with cinematic gothic metal tension and slowcore-to-arena scale. Open with a brief wordless intro: isolated bell-like bounce synthesizer, distant orchestral strings, and a sudden suspended silence. Verses stay dry, narrow, restrained, and rhythmically fractured; add distorted synth bass, metallic impacts, and intricate syncopated percussion in layers. Build through a tempo lift and rising chromatic strings into a wide, high-impact chorus with a soaring male tenor, sharp consonant attacks, dramatic falsetto switches, expressive vibrato slides, and soulful runs. Add female whisper-chant responses and layered choral answers. Use a surprising half-time cyberpunk break, then a tense instrumental passage with a virtuosic orchestral-string and synth lead exchange. Return with a modulated final chorus, maximal vocal width and wet space, controlled punchy low end, glossy detailed top, cinematic stereo depth, and release-ready loud mastering. Finish with a wordless unresolved outro, leaving the outcome open.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/d9f1b9ec-f8a9-4f50-862f-b05cc065f1df\",\"status\":\"complete\",\"title\":\"王冠のない王\",\"visibility\":\"private\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_6715be87-d451-4665-97c0-d89142ec01e0.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_6715be87-d451-4665-97c0-d89142ec01e0.jpeg\",\"created_at\":\"2026-11-04T11:20:30.634Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"6715be87-d451-4665-97c0-d89142ec01e0\",\"liked\":false,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope],\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":243.64,\"style\":\"Experimental Japanese visual-kei cyberpunk art-rock with cinematic gothic metal scale, slowcore opening that snaps into a tense syncopated industrial pulse, sudden half-time drops and double-time surges, modulating upward into an explosive arena chorus. Bright bouncing bell synthesizer motif, distorted synth bass, orchestral strings, prepared piano, metallic impacts, taiko accents, granular reverse effects, and a sharp instrumental solo blending electric violin with glitching synth. Male lead: piercing expressive tenor, breathy falsetto turns, controlled low-mid verses, clipped consonants, dramatic glides, soulful runs and sustained vibrato. Female whisper-chant responses and layered male harmonies. Verses dry and narrow; pre-chorus lifts in octave; chorus opens wide with wet expansive vocals, stacked chants, glossy top end, deep controlled low end, cinematic stereo depth and polished release-ready loud master. Brief vocal-free intro and instrumental vocal-free outro. Grief-struck yet defiant, theatrical, high tension, unpredictable, catchy anime battle anthem.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/6715be87-d451-4665-97c0-d89142ec01e0\",\"status\":\"complete\",\"title\":\"ゲーム開始\",\"visibility\":\"private\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_5f7d98df-83e0-4407-841c-706b8c74c432.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_5f7d98df-83e0-4407-841c-706b8c74c432.jpeg\",\"created_at\":\"2026-11-04T11:20:30.634Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"5f7d98df-83e0-4407-841c-706b8c74c432\",\"liked\":true,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope],\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":229.72,\"style\":\"Experimental Japanese visual-kei cyberpunk art-rock with cinematic gothic metal scale, slowcore opening that snaps into a tense syncopated industrial pulse, sudden half-time drops and double-time surges, modulating upward into an explosive arena chorus. Bright bouncing bell synthesizer motif, distorted synth bass, orchestral strings, prepared piano, metallic impacts, taiko accents, granular reverse effects, and a sharp instrumental solo blending electric violin with glitching synth. Male lead: piercing expressive tenor, breathy falsetto turns, controlled low-mid verses, clipped consonants, dramatic glides, soulful runs and sustained vibrato. Female whisper-chant responses and layered male harmonies. Verses dry and narrow; pre-chorus lifts in octave; chorus opens wide with wet expansive vocals, stacked chants, glossy top end, deep controlled low end, cinematic stereo depth and polished release-ready loud master. Brief vocal-free intro and instrumental vocal-free outro. Grief-struck yet defiant, theatrical, high tension, unpredictable, catchy anime battle anthem.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/5f7d98df-83e0-4407-841c-706b8c74c432\",\"status\":\"complete\",\"title\":\"ゲーム開始\",\"visibility\":\"private\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_8eb07da3-945b-4cf6-96a0-c3d5fffeb53e.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_8eb07da3-945b-4cf6-96a0-c3d5fffeb53e.jpeg\",\"created_at\":\"2026-11-04T11:17:25.583Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"8eb07da3-945b-4cf6-96a0-c3d5fffeb53e\",\"liked\":false,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope],\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":253.72,\"style\":\"Experimental Japanese visual-kei cyberpunk art-rock anthem with cinematic gothic metal weight and slowcore-to-arena dynamics. Open with a brief wordless, sparse bell-and-breath texture; keep verses narrow, dry, controlled, and syncopated over bowed strings, ticking metallic percussion, and a distorted synth bass. Build with sudden dropouts, reversed swells, cinematic impacts, and a surprising half-time cyberpunk break that snaps into double-time. Use bright bouncing synthesizer bells, orchestral strings, taiko-like low percussion, and a short virtuosic shamisen solo; no guitars. Male lead tenor with dramatic chest-to-falsetto switches, expressive vibrato glides, crisp consonant attacks, breathy restrained phrasing, and soulful runs; add female whisper-chant answers and layered vocal harmonies. Make the chorus a soaring, memorable battle-cry hook, with wet wide vocals and panned layered whispers at the climax, then pull back for an unresolved, aching-hope ending. Modulate upward for the final refrain, with a brief tempo lift followed by a sudden deceleration. Detailed stereo depth, punchy controlled low end, glossy top end, polished studio mix, release-ready loud master.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/8eb07da3-945b-4cf6-96a0-c3d5fffeb53e\",\"status\":\"complete\",\"title\":\"神の盤\",\"visibility\":\"private\"},{\"cover_image_large_url\":\"https://cdn1.suno.ai/image_large_1b51d705-d07f-4afd-86c4-52ef5575bc67.jpeg\",\"cover_image_url\":\"https://cdn1.suno.ai/image_1b51d705-d07f-4afd-86c4-52ef5575bc67.jpeg\",\"created_at\":\"2026-11-04T11:17:25.583Z\",\"error\":null,\"handle\":\"wizardx07\",\"id\":\"1b51d705-d07f-4afd-86c4-52ef5575bc67\",\"liked\":false,\"metadata\":{\"description\":\"[experimental],[Bounce Synthesizer Bell],[ethereal],[arena],[expressive breathy Addictive male tenor, smooth falsetto, soulful vocal runs],[cyberpunk break],[slowcore],[Intro no vocal],[outro no vocal],\\n\\n[Alternative],[Addictive],[Modulation],[Aggressive],[Rubato],  [Empty],[Futuristic],\\n\\n[sensual visual-kei male vocals, atmospheric visual, Erotic, Sexual Vibe, young male sexual voice, sexual moans],\\n\\n[Male lead vocal: piercing tenor with electric vibrato, staccato punch on consonants, dramatic glides in chorus],[expressive high-tenor with signature vibrato pull, aggressive consonant bursts, soaring chorus glide],[Verse: tight control, low-mid pitch, minor vibrato overlays],[Pre-chorus: lifted octave falsetto, broken phrasing for emotional charge],[Chorus: sustained long-note vibrato slides with aggressive consonant clipping on backbeat],[Bridge: layered vocoder whispers overlapping live lead lines, echoing in panned chorus],\\n\\n[Male lead vocal (visual-kei trained): subtle yodel entries, glottal restraint, falsetto breath play, overtone resonance], [Male Vocalist: Visual Kei style with extreme vocal range, dramatic tenor to falsetto switches, theatrical emotional delivery, breathy whispers to powerful belting],\\n\\n[SFX, Coloratura-style runs with Peking Opera ornamentation, Chill, Young Male Vocalist: lazy with Peking Opera color tone, sultry delivery, conversational rap flow, Clear young male lead with diva projection, emotional soul phrasing, vocal slide, vocal glissando, vocal runs, vocal heavy autotune, reverse FX, glossy top-end, polished billboard-ready mix, broadcast-ready master],\\n\\n[Deep emotional ethereal arena visual-kei with male multi-vocal layering: resonant male lead moving between falsetto rap and deep chest voice, female whisper-chant answers and airy harmonies, Dynamic tempo shifts from restrained pulse to driving double-time lift and back, cinematic depth, detailed stereo space, punchy controlled low end, polished release-ready loud master],\\n\\n[Catchy, Impact building, high tension, Insane, Captivating vibe, Fashion Ani Song],\\n\\n[Layer gradually, reversed FX and cinematic impacts, Keep verses dry and narrow, choruses wider, center clear, grief-stricken],\\n\\n[Tragic, heroic anime anthem with cinematic storytelling. Fragile verses build through syncopated rhythms and recurring motifs. Sudden silence ignites a soaring chorus: wide melodic leaps, powerful vocals, layered chants, unforgettable hook. Instrumental passages deepen tension and doubt. The main theme returns as a cathartic battle cry, wounded yet fearless. End in aching hope],\\n\\n---\\n\\n你是專業的音樂製作 做一首實驗性大及各種抓耳元素的日文歌\\n主題 遊戲開始(被神明玩弄, 神明的棋子, 被視為遊戲,Checkmate)\\n\\n抓耳 音樂高張力 出乎意料外\\nVariety: MAX\\n\\n加入其他你認為合適的元素樂器配器\\n合適的升調降調\\n合適的升速降速\\n歌詞帶有點詩意 自然通順 整首歌敘事連貫 敘述合理 合乎邏輯 可以適當的加一點英文 有新意的破題 開放式結局 儘量不要重複歌詞和同樣\\n不要AI感\\n音樂風格, 音樂結構, 間奏, solo, 樂器, 歌詞內容 押韻 flow 都交給你來決定\\n加上豐富細節的meta tag 描述\\n\\n合適的演唱歌手\\n合適的合聲\\n\\n高潮處人聲wet and wide\\n\\n加強整體音樂豐富度和音樂空間感\\n音樂響度開到最大\\n整體令人為之一亮\\n吸引人抓耳\\n\\n錄音室等級製作\\n音質最好最專業和EQ也最合適\\n\\n適合發行的版本\\n排行榜等級的品質\",\"duration\":256.4,\"style\":\"Experimental Japanese visual-kei cyberpunk art-rock anthem with cinematic gothic metal weight and slowcore-to-arena dynamics. Open with a brief wordless, sparse bell-and-breath texture; keep verses narrow, dry, controlled, and syncopated over bowed strings, ticking metallic percussion, and a distorted synth bass. Build with sudden dropouts, reversed swells, cinematic impacts, and a surprising half-time cyberpunk break that snaps into double-time. Use bright bouncing synthesizer bells, orchestral strings, taiko-like low percussion, and a short virtuosic shamisen solo; no guitars. Male lead tenor with dramatic chest-to-falsetto switches, expressive vibrato glides, crisp consonant attacks, breathy restrained phrasing, and soulful runs; add female whisper-chant answers and layered vocal harmonies. Make the chorus a soaring, memorable battle-cry hook, with wet wide vocals and panned layered whispers at the climax, then pull back for an unresolved, aching-hope ending. Modulate upward for the final refrain, with a brief tempo lift followed by a sudden deceleration. Detailed stereo depth, punchy controlled low end, glossy top end, polished studio mix, release-ready loud master.\",\"type\":\"generate\"},\"song_url\":\"https://suno.com/song/1b51d705-d07f-4afd-86c4-52ef5575bc67\",\"status\":\"complete\",\"title\":\"神の盤\",\"visibility\":\"private\"}],\"next_cursor\":\"eyJjcmVhdGVkX2F0IjogIjIwMjYtMTEtMDRUMTE6MTc6MjUuNTgzNDkxKzAwOjAwIiwgImNsaXBfaWQiOiAiMWI1MWQ3MDUtZDA3Zi00YWZkLTg2YzQtNTJlZjU1NzViYzY3In0=\"}"
          }
        ]
      }
    }
  }
]
```

