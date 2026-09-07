# The application's secrets in an environment

The application needs a `.env` file it cannot get from the repository — `.env` is gitignored, so it
does not travel with the clone, and the `app` service defined in `.ona/config.yaml` exits without
it. Ona supplies it as a **project secret**, mounted into every environment created from that
project.

The part that matters most is the key to the model gateway. A wrong key does not crash anything:
every path through the model degrades quietly to "unavailable". An implementer then debugs code that
is fine, and a tester writes up findings that never happened. It looks exactly like work right up
until somebody reads it.

Read this file when you dispatch a lane, when the application says the assistant is unavailable, or
when you are setting the factory up on a new project.

**Read it at the moment you need it, not once at the start.** A supervisor meets an environment for
the first time in the middle of a round, and that is when the probe below has to be right. Memorise
it instead and you are carrying a copy in your head that nobody can correct — which is worse than a
copy in a second file, because at least a file can be edited. The expression that reads the model
name out of the application's configuration has already changed once.

## Prove the key is live

One request answers it. Run it inside the environment:

```bash
ona environment ssh <env> -- bash -s <<'PROBE'
set -a; . /workspaces/<repo>/.env 2>/dev/null; set +a
: "${PORTKEY_AZURE_API_KEY:?SECRETS: no key in /workspaces/<repo>/.env}"
url="${PORTKEY_ENDPOINT_SPRING_URL:-https://eu.aigw.galileo.roche.com}"
model="${KIAKIA_LLM_MODEL:-$(sed -n 's/.*KIAKIA_LLM_MODEL:\([^}]*\)}.*/\1/p' \
  /workspaces/<repo>/src/main/resources/application.yaml | head -1)}"
code=$(curl -sS -m 25 -o /tmp/probe.json -w '%{http_code}' \
  -X POST "$url/v1/chat/completions" \
  -H "Authorization: Bearer $PORTKEY_AZURE_API_KEY" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"say ok\"}],
       \"max_completion_tokens\":5}")
echo "SECRETS: HTTP $code $(head -c 160 /tmp/probe.json)"
PROBE
```

It must print `SECRETS: HTTP 200`.

Read the model name and the endpoint out of the environment and the application's own configuration
exactly as written above, never from memory. A key is entitled to particular models, so the key and
the model name are one choice — a probe against a model the application does not use proves nothing
about the application.

## When it does not print 200

**A single failure is not a verdict.** When the human replaces the key, a running environment picks
the new file up on its own, but with a lag of minutes. So wait a few minutes and probe again before
you conclude anything, and never destroy an environment on the first failure.

What a second failure, well after any key change, means:

| Reading | What it is | What you do |
| --- | --- | --- |
| `HTTP 412`, `model_not_allowed_error` | this key is not entitled to the model the application runs | replace the environment with a fresh one; if a **fresh** one repeats it, the project secret itself is out of date — escalate |
| `HTTP 401` or `403` | the key is rejected outright | same: replace once, escalate if a fresh environment repeats it |
| `SECRETS: no key`, or no `.env` at all | the secret is not mounted on this project | escalate. A new environment will not conjure it |
| a redirect to a login page, or a timeout | the environment cannot reach the gateway | platform, not credentials: try one other environment, and if it repeats, stop dispatching this cycle |

**Escalating stops the factory feeding this base branch — it does not turn one lane red.** Every
lane will hit the same wall, so do not spend the backlog discovering it task by task. Comment the
exact status line and response body on the issue, label it `needs-human`, and dispatch nothing
further this cycle. Only the human can replace the secret; the analyst carries the question to them.

**A key that starts working does not clean up after itself.** Anything driven through the model
while the key was dead has to be driven again — say so on the issue rather than assuming the lane
will notice.

**The cockpit never needs any of this.** The planner never starts the application, so the key means
nothing to it, and replacing that environment only kills the planner.

## The other key, which this probe says nothing about

There are two. The application uses one to call the model when a tester drives a screen — that is
the one above. **The agents themselves use a different one to run at all.** A green probe therefore
sits happily above an environment that cannot start an agent.

The second key announces itself as the last line of an agent's transcript:

```
API Error: 412 Portkey Error: Portkey API Key Usage Limit Exceeded. Error Code: 04
```

When an allowance runs out, every agent in every environment stops at once, each going `idle`
mid-task, and a fresh launch dies within a minute. Nothing is lost: the work is on its branches.

**Stop relaunching.** A launch that fails the same way twice is the platform rather than the task,
and further attempts only burn the transcript you would read to diagnose it. Freeze, say which of
the two keys it was and what you measured, and leave it there. A spent allowance is the human's to
raise; it is not a fault in these instructions and not an issue to file against them.

## Putting the secret in place

First time on a project:

```bash
ona project secret create <ona-project-id> --name dotenv \
  --value-from-file .env --file-path /workspaces/<repo>/.env
```

Afterwards it is `update`, against the secret's own id. A second `create` gives you a duplicate, not
a new value:

```bash
ona project secret list <ona-project-id>     # the id and mount path of `dotenv`
ona project secret update <secret-id> --value-from-file .env
```

**You cannot read the value back to check it.** `ona project secret get` answers
`permission_denied: only environments can access secret value`, by design. The probe above is the
only honest verification, and it has to run inside an environment.
