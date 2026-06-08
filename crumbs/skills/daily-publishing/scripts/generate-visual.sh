#!/usr/bin/env bash
set -euo pipefail

# generate-visual.sh — generate one companion image/diagram via Gemini 3 Pro Image
# (Nano Banana Pro) and save it. Called by the daily-publishing Visuals phase, once
# per candidate. Generates exactly ONE image per invocation; the phase loops to make N
# candidates. Reads the API key from config — the key is NEVER stored in this repo.
#
# Usage:
#   generate-visual.sh --prompt-file PATH --out PATH [--aspect 16:9] [--size 2K]
#
#   --prompt-file PATH   File containing the full prompt text (a file, not an inline
#                        arg, so long multi-line prompts need no shell escaping). Required.
#   --out PATH           Where to write the image. The extension is corrected to match
#                        the bytes the model actually returns (JPEG even when not asked).
#                        Required.
#   --aspect AR          Aspect ratio: 16:9 (default), 1:1, 4:5, 1.91:1, 9:16, etc.
#   --size SIZE          Image size: 1K | 2K (default) | 4K.
#
# Key resolution (in order):
#   1. $GEMINI_API_KEY already exported in the environment (explicit override wins)
#   2. ~/.config/daily-publishing/secrets.env  (sourced; expects GEMINI_API_KEY=...)
# Empty, unset, or a placeholder ("REPLACE_ME") key => "visuals not configured":
# print to stderr and exit non-zero so the caller treats this as a skip, not a crash.
#
# Exit codes:
#   0  image saved (path printed to stdout; cost/usage to stderr)
#   2  not configured (no usable key) — caller skips visuals
#   3  API/non-200 error (e.g. 429 RESOURCE_EXHAUSTED) — caller skips this asset
#   1  usage / argument error

err() { printf '%s\n' "$*" >&2; }

# Model is pinned to the GA id below. Do NOT switch to the deprecated pre-release
# variant of this model (shut down 2026-06-25). The free tier for this model is
# limit:0, so billing must be enabled on the key's GCP project or every call returns 429.
MODEL="gemini-3-pro-image"
ENDPOINT="https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent"

ASPECT="16:9"
SIZE="2K"
PROMPT_FILE=""
OUT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --prompt-file) PROMPT_FILE="${2:-}"; shift 2 ;;
    --out)         OUT="${2:-}"; shift 2 ;;
    --aspect)      ASPECT="${2:-}"; shift 2 ;;
    --size)        SIZE="${2:-}"; shift 2 ;;
    -h|--help)
      err "usage: generate-visual.sh --prompt-file PATH --out PATH [--aspect 16:9] [--size 2K]"
      exit 1 ;;
    *) err "unknown argument: $1"; exit 1 ;;
  esac
done

if [ -z "$PROMPT_FILE" ] || [ -z "$OUT" ]; then
  err "usage: generate-visual.sh --prompt-file PATH --out PATH [--aspect 16:9] [--size 2K]"
  exit 1
fi
if [ ! -f "$PROMPT_FILE" ]; then
  err "prompt file not found: $PROMPT_FILE"
  exit 1
fi

# --- Resolve the API key ---------------------------------------------------------
# An explicitly-set GEMINI_API_KEY takes precedence over the secrets file — even if it
# is empty. This makes the environment a true override and lets tests force an
# empty/placeholder key safely (no accidental billed call against a real secrets file).
SECRETS_FILE="${HOME}/.config/daily-publishing/secrets.env"
if [ -n "${GEMINI_API_KEY+set}" ]; then
  KEY="${GEMINI_API_KEY}"
else
  if [ -f "$SECRETS_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$SECRETS_FILE"
    set +a
  fi
  KEY="${GEMINI_API_KEY:-}"
fi

case "$KEY" in
  ""|"REPLACE_ME")
    err "visuals not configured: no usable GEMINI_API_KEY (set it in ${SECRETS_FILE} or the environment)."
    exit 2 ;;
esac

# --- Build the request body (python3 json-encodes the prompt safely) -------------
REQ_BODY="$(PROMPT_FILE="$PROMPT_FILE" ASPECT="$ASPECT" SIZE="$SIZE" python3 - <<'PY'
import json, os
with open(os.environ["PROMPT_FILE"], "r", encoding="utf-8") as fh:
    prompt = fh.read()
body = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "responseModalities": ["IMAGE"],
        "imageConfig": {
            "aspectRatio": os.environ["ASPECT"],
            "imageSize": os.environ["SIZE"],
        },
    },
}
print(json.dumps(body))
PY
)"

# --- Call the API; capture body + HTTP status separately -------------------------
RESP_FILE="$(mktemp)"
trap 'rm -f "$RESP_FILE"' EXIT
HTTP_CODE="$(curl -sS -o "$RESP_FILE" -w '%{http_code}' \
  -X POST "${ENDPOINT}?key=${KEY}" \
  -H 'Content-Type: application/json' \
  --data-binary "$REQ_BODY" || true)"

if [ "$HTTP_CODE" != "200" ]; then
  # Surface the API error message (e.g. 429 RESOURCE_EXHAUSTED naming free_tier_*).
  MSG="$(python3 - "$RESP_FILE" <<'PY'
import json, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        data = json.load(fh)
    e = data.get("error", {})
    print(f"{e.get('status','')} {e.get('message','')}".strip() or json.dumps(data)[:500])
except Exception:
    try:
        with open(sys.argv[1], "r", encoding="utf-8") as fh:
            print(fh.read()[:500])
    except Exception:
        print("(no response body)")
PY
)"
  err "Gemini API error (HTTP ${HTTP_CODE}): ${MSG}"
  exit 3
fi

# --- Parse 200: decode the image, fix extension from mimeType, report usage ------
SAVED="$(OUT="$OUT" SIZE="$SIZE" python3 - "$RESP_FILE" <<'PY'
import base64, json, os, sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    sys.stderr.write("Gemini API: 200 OK but response body was not valid JSON.\n")
    sys.exit(3)

inline = None
for cand in data.get("candidates", []):
    for part in cand.get("content", {}).get("parts", []):
        d = part.get("inlineData") or part.get("inline_data")
        if d and d.get("data"):
            inline = d
            break
    if inline:
        break

if not inline:
    sys.stderr.write("Gemini API: 200 OK but no inlineData image in response.\n")
    sys.exit(3)

mime = (inline.get("mimeType") or inline.get("mime_type") or "image/jpeg").lower()
ext = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
       "image/webp": ".webp"}.get(mime, ".jpg")

out = os.environ["OUT"]
root, cur = os.path.splitext(out)
if cur.lower() != ext:
    out = root + ext

os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
with open(out, "wb") as fh:
    fh.write(base64.b64decode(inline["data"]))

# Cost approximation: ~$0.13/image at 1K-2K, ~$0.24 at 4K.
size = os.environ.get("SIZE", "2K").upper()
cost = "~$0.24" if size.startswith("4") else "~$0.13"
usage = data.get("usageMetadata", {}) or {}
tokens = usage.get("totalTokenCount", "?")
sys.stderr.write(f"generated {out}  (mime {mime}, ~{tokens} tokens, cost {cost})\n")
print(out)
PY
)" || { err "failed to decode/save image from API response."; exit 3; }

# stdout = the final saved path (extension may differ from --out if the model
# returned a different encoding); stderr already carries usage + cost.
printf '%s\n' "$SAVED"
