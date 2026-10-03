# Access model: separating who writes code from who can reach production

This is the part of the design that matters most, and the part that is least
visible in the YAML files. The pipeline works, but its real value is that it
lets a team grow without handing everyone the keys to production.

## The problem

A single repository where everyone can push anywhere has a quiet property: the
same access that lets someone fix a typo also lets them change a deployment
step, rewrite a gate, or push straight to production. That is tolerable for
one person. It stops being tolerable the moment a second person — a junior, a
contractor, an agency — is added, because the blast radius of a mistake or a
compromised account is now "everything".

The obvious fix, "give them a restricted account", does not work, because the
*repository* is the thing that carries production reach: its pipeline holds
the deploy credentials.

## The design

Split the repository from the deployment target, and make exactly one
automated job the bridge between them.

```
   GitHub                                    GitLab
   ──────                                    ──────
   main        (protected, owner only)  ──►  main   (build stage, automatic)
   │              │                              │
   │              │  merge = the approval         │
   │              ▼                              ▼
   │         mirror job  ── push ──►        deploy_production
   │         (sole holder of the           (when: manual — owner only)
   │          GitLab push token)
   │
   staging    (contributors push here
   │           freely; four gates run)
   └── PR  staging → main  (owner reviews, CODEOWNERS requires it)
```

The people doing day-to-day work never hold a GitLab account. They cannot see
the deploy job, cannot read its variables, and cannot reach the host. The only
thing that crosses the boundary is reviewed code, pushed by one job that is
itself part of the reviewed repository.

## The rules, and why each one exists

**Contributors push only to the working branch.** The gates run there, so
feedback is immediate without a review round-trip.

**Every path to the protected branch goes through a reviewed PR.**
`CODEOWNERS` requires the owner's review; branch protection requires that
review before merge. This is the only human approval gate in the whole design,
and it is one that cannot be skipped — merging *is* the approval.

**The mirror job is the only writer to GitLab.** Nothing pushes to GitLab by
hand. A single job holding a single scoped token is auditable in a way that
"everyone has access" never is.

**The mirror token is scoped to one project.** See the token notes at the
bottom of `.github/workflows/mirror-to-gitlab.yml`: a Deploy Token cannot push, a
Project Access Token is unavailable on a free group project, and a legacy
personal token over-grants. A fine-grained personal access token, resource
*Code*, permission *Push*, for one project, is the shape that actually fits.

**Secrets live on a named environment, not on the repository.**
`GITLAB_TOKEN` and `GITLAB_REPO` are set on the `gitlab-mirror` environment.
Any job that wants them must declare `environment: gitlab-mirror`; a job
running from a contributor's branch/PR cannot read them at all. Repository-wide
secrets would be readable by every workflow run, including one triggered from
an untrusted branch.

**Production deploy stays manual.** The build stage is automatic so nobody
waits on a human for a routine build, but `deploy_production` is
`when: manual`. The owner presses that button. It is the last, independent
gate, and it does not share a failure mode with the others.

**Editing the pipeline is itself a flagged change.**
`flag-workflow-changes.yml` comments loudly on any PR touching
`.github/workflows/**` or `CODEOWNERS`. The choice was not to block these
edits — Git already shows them in the diff and the reviewer is the right
control — but to make sure they are never scrolled past in a large PR. It
cannot be defeated by deleting it, because deleting it is itself such a change.

**Nobody, including the owner, bypasses the settings.** Branch protection is
configured with "do not allow bypassing" and no direct-push allowance. A
"just this once" force-push is how protection quietly stops being protection.

## What this design deliberately does not do

**It does not hide what the contributor can see.** They can read every file in
the repository, including the workflow that mirrors to GitLab. That is
intentional: the workflow file holds no secret (the token is on the
environment, referenced as `${{ secrets.* }}`), so reading it tells them the
process but grants them nothing. Hiding it would add complexity for no
security gain.

**It does not create a staging environment.** The gates run against ephemeral,
in-CI resources — an in-memory database, a throwaway Postgres container, a
throwaway SonarQube container. A staging server would be a fifth thing to keep
in sync with production; the gates do not need it. If a staging environment is
ever genuinely required (for manual QA, say), it is a separate decision and
should be a separate branch protection story, not bolted onto these gates.

**It does not add a second approval click on the mirror.** One was designed in
and then removed: GitHub does not offer environment protection rules
(required reviewers) for a private repository on its free plan. Rather than pay
for a plan tier to get a redundant second click, the approval was collapsed
into the one gate that already exists and cannot be skipped — the merge to the
protected branch. If a paid plan is added later, a required reviewer on the
mirror environment can be switched on without changing anything else.

## Cost and trade-offs

- Plus: production secrets are decoupled from code access. A contributor's
  compromised account cannot reach production. The path from code to
  production is one reviewable job.
- Minus: two forges (GitHub + GitLab) instead of one. That is real operational
  overhead — two sets of tokens, two sets of UI, one more thing to learn — and
  it is only worth it if the access separation is the requirement. On a
  single-person project, one forge is better.
- Minus: the mirror adds a hop between merge and build. Acceptable; the mirror
  runs in seconds and deliberately never cancels an in-progress push.

## Adapting it

If you are a solo developer, most of this is unnecessary. Take the gates and
skip the split. The split earns its cost when at least one person must be able
to contribute *without* being able to deploy.
