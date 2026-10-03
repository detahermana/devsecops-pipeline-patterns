# Gate design: why these four, and why each one is shaped the way it is

Four gates, each answering a different question. A change has to pass all four
before a human looks at it — the point is that by the time the reviewer reads
the diff, the mechanical objections are already settled and their attention
goes to the parts only a human can judge.

| Gate | Question it answers |
|---|---|
| 1. Lint + unit tests | Is the change internally consistent and does the logic work? |
| 2. Integration tests | Does it work against a real database with real migrations? |
| 3. Security scan | Does it introduce a vulnerable dependency or a dangerous pattern? |
| 4. Code quality | Does it meet the project's quality bar? |

## Gate 1 — lint and unit tests

Fast, in-memory, no external services. This is the gate that should fail fastest
so a contributor gets feedback in a minute rather than ten.

**Why linting is scoped to changed files.** Switching a linter on repo-wide
fails immediately on an unknown number of pre-existing violations that have
nothing to do with the change under review. That is not a useful gate — it is a
blocked pipeline with a hundred irrelevant complaints. Scoping the linter to
the files that changed still *blocks* on any violation in a changed line, so
every new and modified line is held to the standard from day one, and the rest
of the codebase gets cleaned up incrementally as files are touched naturally.
That beats one large, unreviewable cleanup PR before linting can be switched on
at all.

The scope is computed by diffing against the merge-base on a PR, or against
the pre-push commit on a direct push. If no usable base exists (the first push
of a new branch), it lints *nothing* rather than guessing a base that could
wrongly include unrelated files.

**Why the frontend production build rides along here.** It is not a test, but a
broken production build is exactly the kind of mistake the pipeline exists to
catch before review, and it is cheap. It does not warrant its own job.

## Gate 2 — integration tests against real Postgres

The same test suite as Gate 1, pointed at a real database. This is not
redundant: an in-memory database quietly tolerates things a real Postgres does
not — real constraint behaviour, real types, real transaction semantics. A test
that passes on the fast database and fails on the real one has found something
the fast database cannot see.

**Why migrations are run for real, and the result verified.** Running
`alembic upgrade head` against a real database and failing the job on any
non-zero exit is the check that was missing when a migration failed silently in
production. It is not enough to run the migration and assume it worked — the
job reads back the revision the database actually landed on and compares it to
the migration head. A mismatch fails the build. See
`incident-regression.md` for the incident that made this necessary.

**Why `PYTHONPATH` is set.** A console script's `sys.path` does not include the
invoking working directory the way `python some_script.py` does. Without
`PYTHONPATH=.`, the migration environment's `from app.main import Base` fails
with `ModuleNotFoundError`. Production does the same thing in its compose file,
so the CI job mirrors it rather than inventing a second convention.

## Gate 3 — security scan

Three tools, because they look for different things:

- **Dependency CVEs** — a filesystem scan across the whole repository, so a
  vulnerable dependency is caught wherever it is pinned, not only in the paths
  the rest of the workflow covers.
- **Static analysis (SAST)** on the application source, for dangerous patterns a
  dependency scanner does not see.
- **Frontend dependency audit**, because the frontend lockfile is a separate
  dependency tree with its own advisories.

**On pinned versions of third-party Actions.** Version tags on Actions are
mutable — an attacker with compromised credentials can force-push a malicious
commit onto an existing tag, and every pipeline referencing that tag runs it.
This is not theoretical: it happened to the scanner Action used here in 2026,
with malicious code pushed onto 76 of its 77 existing tags. The file carries a
note to replace the tag with the full 40-character commit SHA before production
use. This rule applies to every third-party Action, not just this one. Tags can
be force-pushed; commit SHAs cannot.

**When a scan fails on something you cannot fix yet.** A pre-existing
transitive advisory with no available fix is a real signal, not a broken gate.
The response is to triage it — fix, bump, or record an accepted risk — never to
loosen the audit level. Loosening it is how the gate stops finding things.

## Gate 4 — code quality

A quality gate against a self-hosted SonarQube Community Edition, started fresh
inside the job and discarded afterwards. Chosen over the hosted offering
deliberately: no lines-of-code cap on private repositories, and no third-party
service holding the source.

**The trade-off, accepted knowingly:** spinning SonarQube up per run means
there is no persistent quality-trend dashboard across runs — only this run's
pass/fail. The alternative (a small long-lived instance next to the deployment
target) trades CI minutes for that history. On a project where the trend
matters more than the run cost, the long-lived instance is the better call.

**Why the raw scanner image is used rather than an "official" one-liner.**
SonarQube's embedded Elasticsearch refuses to start without a raised
`vm.max_map_count`, so the job raises it explicitly before starting the
container. Being explicit about that is worth more than a shorter config.

## What the gates do not cover, and why that is stated plainly

The example app in `examples/app/` exists to give the gates something real to
run against. In a real project, adding a second service (an AI service, a
worker) means deciding explicitly whether it gets its own gates. It is
legitimate to say "not yet" — as long as it is *said*, in the workflow file, so
the next person knows it was a decision rather than an oversight. Silent gaps
become assumptions.

## Adding a fifth gate

Before adding one, ask what question it answers that the existing four do not.
A gate that duplicates an existing concern adds time without adding safety.
If it does answer a new question, give it the same two properties as the rest:
it must be able to fail the build (a warning-only gate is decoration), and it
must be wired into the required status checks on the protected branch, or it
does not actually gate anything.
