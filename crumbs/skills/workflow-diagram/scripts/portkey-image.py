#!/usr/bin/env python3
"""portkey-image.py — generate one workflow-diagram image via the Roche Galileo
Portkey gateway (OpenAI-compatible images API) and save it.

This is the "portkey" backend of the workflow-diagram skill. generate-diagram.sh
dispatches here when config.toml selects backend = "portkey"; it is not called
directly by the skill. Mirrors generate-diagram.sh's CLI contract so the skill's
Phase-3 (generate) and Phase-4 (repair) invocations are backend-agnostic.

Run via uv so portkey-ai need not be installed in any project venv:
    uv run --with portkey-ai python portkey-image.py --prompt-file ... --out ...

CLI (same flags as generate-diagram.sh):
    --prompt-file PATH   file with the full prompt text. Required.
    --out PATH           where to write the image (extension corrected to .png). Required.
    --aspect AR          16:9 (default) etc. Maps to a supported pixel size.
    --size SIZE          1K (default) | 2K | 4K. Maps to a supported pixel size.
    --edit-image PATH    repair mode. The gateway does NOT expose images.edit, so this
                         REGENERATES from the prompt (the skill writes the fix
                         instruction into --prompt-file); the image is not edited.

Backend settings come from generate-diagram.sh via env:
    PORTKEY_BASE_URL  gateway base url (e.g. https://us.aigw.galileo.roche.com/v1)
    PORTKEY_MODEL     image model id (e.g. gpt-image-1.5-2025-12-16)
    PORTKEY_KEY_ENV   name of the secrets.env var holding the API key (e.g. PORTKEY_AZURE_API_KEY)

Key resolution (mirrors the gemini path): the var named by PORTKEY_KEY_ENV, if SET in
the environment, wins even when empty (lets tests force not-configured safely); else the
secrets file ~/.config/workflow-diagram/secrets.env is sourced and the var read from it.

Exit codes (match generate-diagram.sh): 0 saved (path to stdout, usage to stderr);
2 not configured (no usable key) — caller skips; 3 API/response error — caller skips
this candidate; 1 usage/argument error.
"""
import argparse
import base64
import os
import re
import sys
from pathlib import Path


def err(msg: str) -> None:
    print(msg, file=sys.stderr)


SECRETS_FILE = Path.home() / ".config" / "workflow-diagram" / "secrets.env"


def read_key(key_env: str) -> str:
    """Env var named by key_env wins if set (even empty); else read from secrets.env."""
    if key_env in os.environ:
        return os.environ[key_env]
    if SECRETS_FILE.is_file():
        for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key_env:
                # Strip optional surrounding quotes, mirroring shell `set -a` sourcing.
                return v.strip().strip('"').strip("'")
    return ""


# Pixel size by requested tier + aspect. gpt-image-1.5 supports 1024x1024, 1536x1024
# (landscape), 1024x1536 (portrait). The diagrams are 16:9 -> use the widest landscape.
def resolve_size(aspect: str, size: str) -> str:
    portrait = aspect in {"9:16", "4:5", "2:3", "3:4"}
    if portrait:
        return "1024x1536"
    if aspect == "1:1":
        return "1024x1024"
    # 16:9 / 1.91:1 / 3:2 and anything else -> landscape
    return "1536x1024"


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--size", default="1K")
    ap.add_argument("--edit-image", default="")
    args = ap.parse_args()

    prompt_path = Path(args.prompt_file)
    if not prompt_path.is_file():
        err(f"prompt file not found: {args.prompt_file}")
        return 1
    if args.edit_image and not Path(args.edit_image).is_file():
        err(f"edit-image not found: {args.edit_image}")
        return 1

    base_url = os.environ.get("PORTKEY_BASE_URL", "").strip()
    model = os.environ.get("PORTKEY_MODEL", "").strip()
    key_env = os.environ.get("PORTKEY_KEY_ENV", "PORTKEY_AZURE_API_KEY").strip()
    if not base_url or not model:
        err("diagrams not configured: portkey backend missing base_url/model in config.toml.")
        return 2

    key = read_key(key_env)
    if key in ("", "REPLACE_ME"):
        err(f"diagrams not configured: no usable {key_env} (set it in {SECRETS_FILE} or the environment).")
        return 2

    prompt = prompt_path.read_text(encoding="utf-8")
    if args.edit_image:
        # The gateway does not expose images.edit; regenerate from the prompt instead.
        # The skill writes the fix instruction into --prompt-file for repair, so the
        # prompt already carries the correction.
        err("portkey backend: images.edit unavailable on gateway — regenerating from prompt instead of editing.")

    try:
        from portkey_ai import Portkey
    except Exception as e:  # pragma: no cover - environment issue
        err(f"portkey backend: cannot import portkey_ai ({e}). Run via 'uv run --with portkey-ai'.")
        return 3

    px = resolve_size(args.aspect, args.size)
    try:
        client = Portkey(api_key=key, base_url=base_url, timeout=300.0)
        resp = client.images.generate(model=model, prompt=prompt, size=px, n=1)
    except Exception as e:
        name = type(e).__name__
        text = str(e)
        # A connection/timeout failure to the Roche gateway is almost always a missing
        # VPN — surface that prominently so the user checks it first.
        looks_like_conn = (
            "Connection" in name
            or "Timeout" in name
            or "timed out" in text.lower()
            or "connection" in text.lower()
            or "getaddrinfo" in text.lower()
            or "name resolution" in text.lower()
        )
        if looks_like_conn:
            err(
                f"Portkey gateway unreachable ({name}). The Galileo gateway "
                f"({base_url}) requires the Roche VPN / Corporate Network — this error is "
                "most likely because you are NOT connected to the VPN. Connect and retry."
            )
        else:
            err(f"Portkey API error: {name}: {text[:300]}")
        return 3

    try:
        datum = resp.data[0]
        b64 = getattr(datum, "b64_json", None)
        url = getattr(datum, "url", None)
    except Exception as e:
        err(f"Portkey API: response had no image data ({e}).")
        return 3
    if not b64:
        err(f"Portkey API: 200 but no b64_json image in response (url={url}).")
        return 3

    out = args.out
    root, cur = os.path.splitext(out)
    if cur.lower() != ".png":
        out = root + ".png"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    raw = base64.b64decode(b64)
    with open(out, "wb") as fh:
        fh.write(raw)

    usage = getattr(resp, "usage", None)
    tokens = getattr(usage, "total_tokens", "?") if usage else "?"
    err(f"generated {out}  (portkey {model}, {len(raw) // 1024} KB, ~{tokens} tokens)")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
