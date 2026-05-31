#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

CET = ZoneInfo("Europe/Warsaw")


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    model = data.get("model", {}) or {}
    model_id = model.get("id", "") or ""
    model_name = model.get("display_name", "") or ""
    transcript = data.get("transcript_path", "") or ""
    cwd = (data.get("workspace", {}) or {}).get("current_dir", "") or ""

    ctx_max = 1_000_000 if "[1m]" in model_id else 200_000

    last_time = ""
    ctx_used = 0

    if transcript and os.path.isfile(transcript):
        last_assistant = None
        try:
            with open(transcript, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    if entry.get("type") == "assistant":
                        last_assistant = entry
        except Exception:
            last_assistant = None

        if last_assistant:
            ts = last_assistant.get("timestamp", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    last_time = dt.astimezone(CET).strftime("%H:%M:%S")
                except Exception:
                    pass
            usage = (last_assistant.get("message", {}) or {}).get("usage", {}) or {}
            ctx_used = (
                int(usage.get("input_tokens", 0) or 0)
                + int(usage.get("cache_read_input_tokens", 0) or 0)
                + int(usage.get("cache_creation_input_tokens", 0) or 0)
            )

    pct = int(round(ctx_used * 100 / ctx_max)) if ctx_max else 0
    dirname = os.path.basename(cwd.rstrip("/")) if cwd else ""

    parts = []
    parts.append(last_time if last_time else datetime.now(CET).strftime("%H:%M:%S"))
    parts.append(f"ctx {fmt_tokens(ctx_used)}/{fmt_tokens(ctx_max)} ({pct}%)")
    if model_name:
        parts.append(model_name)
    if dirname:
        parts.append(dirname)

    sys.stdout.write(" | ".join(parts))


if __name__ == "__main__":
    main()
