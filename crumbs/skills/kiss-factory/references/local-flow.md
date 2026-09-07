# Running the factory locally, one task at a time

Same fleet, no cloud. The supervisor starts each role as its own Claude session on this machine and
watches it through its transcript. One task runs at a time.

Most of `SKILL.md` still holds. What this file carries is the part that cannot be derived from
anything else: the commands, and the handful of rules that change when there is no race for the base
branch.

## What stops applying

Everything that existed to survive disposable cloud machines and five lanes at once: keep-alive, the
per-environment model probe, the `lane-*` and `verify-*` names, the two-call delete, the limit of
five, the ordering of merges, and the merge-verifier role entirely — it existed only to check that a
conflict resolution had not eaten the other task's intent, and with one task at a time there is no
conflict to resolve.

**Merge the moment the gate passes. Never collect a batch.** Measured on this factory's own output:
of the pull requests merged within a quarter of an hour of being ready, none came back; of those that
waited an hour or more, five in eight did. Waiting is what turns finished work into rework, and that
holds whether the wait came from a queue or from nobody being at the desk.

## What still applies, and matters more here

**Each role is its own session.** An agent that judges its own work passes it — a fresh context is
the entire value of a reviewer. Folding the roles together to save starting a process throws away
the only reason they exist. This has nothing to do with parallelism and does not change here.

**Two liveness thresholds, because one worker is now the whole factory.** With five lanes a dead
worker cost a fifth of throughput; with one it costs everything.

- **A trace within ten minutes of starting**: a draft pull request and a plan comment on the issue.
  Nothing by then is a failed launch, not a slow start — from outside, a session frozen on a prompt
  and one thinking hard look identical, and making itself visible is the implementer's first
  instruction.
- **A plan written before any code.** It is what a restart resumes from. A worker that wrote nothing
  down leaves nothing to resume.

**The gate, minus what the race caused.** Gone: conflicts, mergeability, merge ordering, cleaning up
machines. What remains is what a single worker cannot judge about itself:

- **The traces exist, and they were written before the work was handed over.** Posted afterwards,
  they reviewed a decision already taken.
- **Read the diff against `.claude/rules`,** using `added-comments.sh` for the comment rule rather
  than hunting by eye.
- **Read any commit that landed after the last review yourself.** Nobody else has seen it. A worker
  that fixes one more thing after its reviewer has finished has just put unreviewed code into a pull
  request that looks fully reviewed.

## The commands

### Start the application

Never on the shared `kiakia` database — as of 2026-09-05 it carries Flyway checksums that no longer
match the migrations in the repository, and startup fails validation. Make a throwaway one:

```bash
podman exec kiakia-postgres psql -U kiakia -d postgres \
  -c "create database kiakia_verify owner kiakia"
```

Postgres runs in podman as `kiakia-postgres` on 5432, user and password `kiakia`.

```bash
SERVER_PORT=8099 \
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/kiakia_verify \
SPRING_DATASOURCE_USERNAME=kiakia \
SPRING_DATASOURCE_PASSWORD=kiakia \
SPRING_LDAP_URLS=ldap://directory.invalid:389 \
SPRING_LDAP_USERNAME='cn=kiakia-directory-reader,ou=service-accounts,dc=example,dc=com' \
SPRING_LDAP_PASSWORD=not-a-real-password \
KIAKIA_DIRECTORY_LDAP_SEARCH_BASE='ou=people,dc=example,dc=com' \
KIAKIA_JWT_SECRET=local-verification-secret-not-for-production \
KIAKIA_LOCAL_DEFAULT_PASSWORD=local-fixture-password \
KIAKIA_BOOTSTRAP_ADMINS=local-admin \
KIAKIA_RECON_ENABLED=false \
./gradlew bootRun
```

Port 8099 rather than the default, so it does not collide with an end-to-end run on 8080. The
directory address is deliberately unreachable; nothing here needs it. `KIAKIA_BOOTSTRAP_ADMINS` plus
`KIAKIA_LOCAL_DEFAULT_PASSWORD` are what give you an account to sign in with.

`e2e/global-setup.ts` (lines 141–169) is the authority for this list — if a variable is added there,
add it here.

Sign in for an API token:

```bash
curl -s localhost:8099/web/identity/sign-in \
  -H 'Content-Type: application/json' \
  -d '{"login":"local-admin","password":"local-fixture-password"}'
```

It answers with `accessToken`, which goes in an `Authorization: Bearer` header.

Drop it when you are done:

```bash
podman exec kiakia-postgres psql -U kiakia -d postgres -c "drop database kiakia_verify"
```

### Reach the application-configured model

Local verification must exercise the model the application is configured to use. Do not set
`KIAKIA_LLM_MODEL` as a routine test step. The current repository default is
`gpt-5.6-luna-2026-07-09`, declared in `src/main/resources/application.yaml`; treat that application
configuration, rather than this document, as the authority.

The credentials live in the repository's `.env`. Source it in the process that starts the application:

```bash
set -a; . ./.env; set +a
```

Use the ordinary `PORTKEY_AZURE_API_KEY` paired with that configured model. For a repeatable test,
override only the temperature:

```bash
KIAKIA_LLM_TEMPERATURE=0
```

Before driving a model-backed path, run the probe in `references/secrets.md`, adapting its workspace
path to the local checkout. It resolves the model from the environment or application configuration
and must return HTTP 200. If it does not, follow that reference's failure procedure; do not switch to
another model merely to make the probe pass. Override the model only when a task's acceptance criteria
explicitly require a different one, and verify that model with its matching gateway key first.

### Watch a worker

Local sessions write a transcript per session, named by its identifier:

```bash
ls -t ~/.claude/projects/<working-directory-with-slashes-as-dashes>/*.jsonl | head -1
```

For this checkout that directory is
`~/.claude/projects/-Users-sieracm2-KiakiaAINativeProjects-kiakia-ai-native-worktrees-arch-analysis`.

Reading the newest entries is how you tell a worker that is thinking from one that has stopped. Do
not judge by the process: it stays resident after the work ends. `references/ona.md` explains the
same distinction for the cloud, and it is the same distinction here.
