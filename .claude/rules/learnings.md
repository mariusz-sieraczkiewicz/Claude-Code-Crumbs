# Learnings (Project: Claude-Code-Crumbs)

## Companion visuals for daily-publishing — engine & method (2026-06-08)

Researched + tested image/diagram generation to add companion visuals to the
`daily-publishing` skill. Conclusions, proven by side-by-side tests in a scratch dir:

### Tool choice
- **Diagrams-as-code (D2, Mermaid, Excalidraw) are NOT publishable.** They optimize for
  git-diffable / in-sync-with-code, not beauty. Auto-layout (dagre/ELK/TALA) tops out at
  "functional but ugly" — sprawling layouts, arrows crossing container boxes, colliding
  labels. No amount of theming fixes this. Wrong category for content visuals.
- **Winner: Nano Banana Pro = Gemini 3 Pro Image.** Reasoning image model, best-in-class
  text rendering (labels crisp + correctly spelled), follows structured layout prompts,
  renders genuine dependency graphs (not just decoration). Dramatic quality gap vs D2.
  - Router alternate for very dense text/UI briefs: **GPT-Image-2** (better dense text,
    slower ~112s vs ~28s). Cheap/bulk tier: `gemini-3.1-flash-image` / Imagen 4 Fast.

### API specifics (verified)
- Endpoint (same one `@google/generative-ai` SDK defaults to):
  `https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent?key=$KEY`
- **Pin the GA model id `gemini-3-pro-image`** — NOT `gemini-3-pro-image-preview`. The
  `-preview` variant (referenced by most blogs) is deprecated, **shut down 2026-06-25**.
- Request: `generationConfig.responseModalities: ["IMAGE"]` +
  `generationConfig.imageConfig: { aspectRatio: "16:9", imageSize: "2K" }` (1K/2K/4K).
- **Output is JPEG even when you don't ask for PNG** — the model picks the encoding.
  Read `parts[].inlineData.{data(base64),mimeType}`; convert to PNG after if needed.
- **Billing is REQUIRED.** Free tier for `gemini-3-pro-image` is `limit: 0` →
  every call 429s with `RESOURCE_EXHAUSTED` naming `free_tier_requests`/`free_tier_input_token_count`.
  If the 429 still says `free_tier_*` after enabling billing, billing was enabled on the
  WRONG project (an API key is bound to one specific GCP project) or hasn't propagated yet
  (wait ~1 min; error gives a "retry in Ns" hint). Cost ≈ $0.13/image at 1K–2K, $0.24 at 4K.
- **Vertex is the other surface** (`aiplatform.googleapis.com`, OAuth + project, no API key).
  Use it to bypass the AI-Studio free-tier wall — but only with a PERSONAL GCP project.
  The machine's active gcloud project was a Roche corp project (`gcp-t-kiakia-lt3ym`);
  do NOT bill/log personal content there.

### Method that makes image-model diagrams correct (not "beautiful but wrong")
1. **Ground first.** Read the authoritative source (e.g. `subject.md`), extract the REAL
   structure/dependencies. Prompted from a bare word, the model draws a pretty wrong picture.
   (daily-publishing already requires verify-against-source in Phase 6 — reuse that.)
2. **State arrow semantics explicitly** in the prompt ("arrow A->B means A depends on B;
   all arrows point up"). The model honors it.
3. **Control density / altitude.** A concept diagram wants ~4–5 nodes, not a file dump.
   First lighthouses attempt (all 5 model files + engine) was correct but "too detailed";
   the 4-node version (Agent loop→Plan→Problem model→Lighthouses) was the right altitude.
   Push file-level detail into prose, keep the picture at concept level.
4. **Generate N candidates and pick.** Output is non-deterministic — same prompt gives
   different valid compositions. Mirror the existing "Phase 4 — Choose" pattern.
5. **Proofread labels.** Even Nano Banana Pro garbles ~1 label per *complex* diagram
   (saw "invariants cleners"). Simpler diagram = lower risk. Fix via an editing re-prompt
   ("change label X to Y, keep everything else identical").

### Secret handling
- Gemini key stored at `~/.config/daily-publishing/secrets.env` (chmod 600), OUTSIDE the
  git repo so it can never be committed. Source with `set -a; . <file>; set +a`.
- **Key precedence = env BEFORE file, branch on set-ness not emptiness.** An explicitly-set
  `GEMINI_API_KEY` (even empty) must win over the secrets file — use `[ -n "${GEMINI_API_KEY+set}" ]`,
  NOT `[ -z "$KEY" ]`. Reason (learned by burning ~$0.4 in real calls): if the file is sourced
  whenever the env var is empty, then testing "what happens with an empty key" while a real
  secrets.env exists silently fires REAL BILLED calls instead of the skip path. Env-overrides-file
  makes the helper test-safe. When testing skip paths, also isolate `HOME` (`env -i HOME=/tmp/x`)
  so a real `~/.config/.../secrets.env` can't leak in.
