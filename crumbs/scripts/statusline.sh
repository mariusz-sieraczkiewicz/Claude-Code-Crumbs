#!/bin/bash
input=$(cat)

CLI="${HOME}/.local/bin/build-cli"
existing=""
if [ -x "$CLI" ]; then
    existing=$(echo "$input" | "$CLI" claude statusline 2>/dev/null)
fi

if ! command -v jq &>/dev/null; then
    echo "$existing"
    exit 0
fi

duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0')
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // 0')
input_tokens=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
output_tokens=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0')
model=$(echo "$input" | jq -r '.model.display_name // "unknown"')
session_id=$(echo "$input" | jq -r '.session_id // ""')
short_session="${session_id}"
effort=$(echo "$input" | jq -r '.effort.level // "high"')
project_dir=$(echo "$input" | jq -r '.workspace.project_dir // ""')

total_secs=$((duration_ms / 1000))
elapsed=$(printf "%02d:%02d:%02d" $((total_secs/3600)) $(((total_secs%3600)/60)) $((total_secs%60)))

used_tokens=$(awk "BEGIN {printf \"%.0f\", $used_pct / 100 * $ctx_size}")
if [ "$used_tokens" -ge 1000000 ]; then
    used_display=$(awk "BEGIN {printf \"%.1fM\", $used_tokens/1000000}")
elif [ "$used_tokens" -ge 1000 ]; then
    used_display=$(awk "BEGIN {printf \"%.1fk\", $used_tokens/1000}")
else
    used_display="$used_tokens"
fi

if [ "$ctx_size" -ge 1000000 ]; then
    ctx_display=$(awk "BEGIN {printf \"%.2fM\", $ctx_size/1000000}")
elif [ "$ctx_size" -ge 1000 ]; then
    ctx_display=$(awk "BEGIN {printf \"%.0fk\", $ctx_size/1000}")
else
    ctx_display="$ctx_size"
fi

pct=$(awk "BEGIN {printf \"%d\", $used_pct}")

project_name=""
if [ -n "$project_dir" ]; then
    project_name=$(basename "$project_dir")
fi

cet_time=$(TZ="Europe/Warsaw" date +%H:%M:%S)

status="${cet_time} | ctx ${used_display}/${ctx_display} (${pct}%) | ${model} ${effort} | ${project_name} | ${short_session}"

if [ -n "$existing" ]; then
    printf "%s\n%s" "$existing" "$status"
else
    echo "$status"
fi
