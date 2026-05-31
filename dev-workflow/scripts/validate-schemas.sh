#!/usr/bin/env bash
set -euo pipefail

# validate-schemas.sh
# Validate project YAML/JSON files against the plugin's JSON Schemas.
# Usage: ./validate-schemas.sh   (no args; scans the project from CWD)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCHEMA_DIR="${SCRIPT_DIR}/../schemas"

STACK_SCHEMA="${SCHEMA_DIR}/stack.schema.json"
EPICS_SCHEMA="${SCHEMA_DIR}/epics.schema.json"
RUN_PHASE_SCHEMA="${SCHEMA_DIR}/run-phase.schema.json"

# Pre-flight: python3 + libs must be available.
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required. Install Python 3.8+ and then run:" >&2
    echo "  pip install pyyaml jsonschema   # or: pipx install jsonschema" >&2
    exit 2
fi

if ! python3 -c "import yaml, jsonschema" >/dev/null 2>&1; then
    echo "Error: missing Python libs (pyyaml, jsonschema). Install with:" >&2
    echo "  pip install pyyaml jsonschema   # or: pipx install jsonschema" >&2
    exit 2
fi

EXIT_CODE=0

validate_one() {
    schema="$1"
    file="$2"
    if [ ! -f "$schema" ]; then
        echo "FAIL ${file}: schema not found at ${schema}"
        EXIT_CODE=1
        return
    fi
    out="$(SCHEMA_FILE="$schema" TARGET_FILE="$file" python3 -c '
import os, sys, json
import yaml, jsonschema
schema_path = os.environ["SCHEMA_FILE"]
file_path = os.environ["TARGET_FILE"]
try:
    with open(schema_path, "r", encoding="utf-8-sig") as f:
        schema = json.load(f)
    with open(file_path, "r", encoding="utf-8-sig") as f:
        if file_path.endswith((".yaml", ".yml")):
            data = yaml.safe_load(f)
        else:
            data = json.load(f)
    jsonschema.validate(instance=data, schema=schema)
    # Cross-check task_id vs parent directory for runs/ phase JSONs.
    # WARNING only — does not change exit code. Stderr.
    if "/.claude/runs/" in file_path or file_path.startswith(".claude/runs/"):
        if isinstance(data, dict):
            expected_task_id = os.path.basename(os.path.dirname(file_path))
            actual_task_id = data.get("task_id")
            if actual_task_id and expected_task_id.startswith("T-") and actual_task_id != expected_task_id:
                sys.stderr.write("WARN: task_id mismatch in " + file_path + ": dir=" + expected_task_id + " json=" + str(actual_task_id) + "\n")
    print("OK")
except jsonschema.ValidationError as e:
    msg = e.message.replace("\n", " ")
    path = "/".join(str(p) for p in e.absolute_path) or "<root>"
    print("FAIL: at " + path + ": " + msg)
except json.JSONDecodeError as e:
    print("FAIL: schema or file is malformed JSON: " + e.msg + " at line " + str(e.lineno) + " col " + str(e.colno))
except yaml.YAMLError as e:
    mark = getattr(e, "problem_mark", None)
    if mark:
        print("FAIL: YAML parse error at line " + str(mark.line + 1) + " col " + str(mark.column + 1) + ": " + str(e))
    else:
        print("FAIL: YAML parse error: " + str(e))
except Exception as e:
    print("FAIL: " + type(e).__name__ + ": " + str(e))
' 2>&1 || true)"
    case "$out" in
        OK)
            echo "OK ${file}"
            ;;
        FAIL:*)
            reason="${out#FAIL: }"
            echo "FAIL ${file}: ${reason}"
            EXIT_CODE=1
            ;;
        *)
            echo "FAIL ${file}: ${out}"
            EXIT_CODE=1
            ;;
    esac
}

# 1) .claude/stack.yaml
if [ -f ".claude/stack.yaml" ]; then
    validate_one "$STACK_SCHEMA" ".claude/stack.yaml"
fi

# 2) docs/planning/epics.yaml
if [ -f "docs/planning/epics.yaml" ]; then
    validate_one "$EPICS_SCHEMA" "docs/planning/epics.yaml"
fi

# 3) .claude/runs/**/*.json
if [ -d ".claude/runs" ]; then
    # find is POSIX; -print0 + read -d works on BSD + GNU.
    # Warn (but do not fail) on symlinked phase JSONs.
    while IFS= read -r -d '' file; do
        if [ -L "$file" ]; then
            echo "WARN: symlink found in runs/, skipping: $file" >&2
            continue
        fi
        validate_one "$RUN_PHASE_SCHEMA" "$file"
    done < <(find ".claude/runs" -name "*.json" -print0)
fi

exit "$EXIT_CODE"
