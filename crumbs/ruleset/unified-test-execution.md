# Test Execution Rules

## Core Rule

Always have **live, real-time visibility** into test runs. Running blind and checking results at the end is forbidden — if something hangs or fails early, you must see it within seconds.

## Live Output

- Always use a live/streaming reporter — never rely on a reporter that is silent during the run
- Never truncate output with pipes (`tail -N`, `head -N`, `> /dev/null`) — they buffer everything and emit only after exit
- The application under test must emit progress logs at info level by default — a live reporter is useless if the system is silent
- For long pipeline tests, the test code itself must log per-phase progress — server logs alone get lost in noise

## Foreground vs Background

- **Default to foreground** — run directly with a live reporter and let the output stream
- **Background only when you have genuine parallel work** — background adds complexity and is easy to get wrong (silent buffering)
- For background runs: tee output to a file AND attach a monitor grepping for pass/fail/error events
- Without the monitor you are blind; without tee the file stays empty until the run ends

## Progress Updates

- During long runs (>3 minutes), provide a one-line status update every 2-3 minutes with concrete numbers (test count, latest test name, elapsed time)
- Silence is failure — if someone has to ask "what's happening?", this rule was violated
- If monitoring, the filter must include BOTH success AND failure markers — a monitor matching only successes goes silent on a crash loop

## When Visibility Is Lost

- If a test run is buffered/silent with no live signal possible, **kill it immediately and re-launch correctly**
- Do not "wait it out" — a silent run is wasted time

## Anti-Patterns

- Default reporter that produces output only at the end
- Background run without tee + monitor
- Piping output through truncation (`tail`, `head`, `/dev/null`)
- Monitor watching only successes (silent on hang/crash)
- Claiming "I am monitoring" without a log line every few seconds to prove it
