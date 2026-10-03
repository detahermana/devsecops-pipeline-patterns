# DevSecOps Pipeline Patterns

A CI/CD architecture for a team where not everyone who writes code should be
able to reach production. Four automated quality gates on the forge where
contributors work, a single reviewed path to the forge that holds production
credentials, and a deploy that stays manual on purpose.

Written as a pattern library: the templates are generic, the reasoning is
documented alongside them, and a small example application is included so the
gates have something real to run against.

> Extracted as a reusable pattern from real client work. No client names,
> domains, hostnames, addresses, or account identifiers appear anywhere in this
> repository.

## The architecture in one picture

```
   GitHub                                            GitLab
   ──────                                            ──────
   main        (protected — owner merges only)  ──►  main    build: automatic
     ▲                   │                                    │
     │                   │  merge IS the approval              ▼
     │                   ▼                             deploy_production
     │              mirror job  ──── push ────►        (when: manual — owner)
     │              (sole holder of the
     │               GitLab push token)
     │
   staging      (contributors push freely)
                 └─ 4 gates run on every push and on the PR
```

Contributors never hold a GitLab account. They cannot see the deploy job, read
its variables, or reach the deploy host. The only thing that crosses the
boundary is reviewed code, pushed by one job that is itself part of the
reviewed repository.

Full reasoning, including what this design deliberately does *not* do and what
it costs: [`docs/access-model.md`](docs/access-model.md).

## What is in here

| Path | What it is |
|---|---|
| [`github-actions/quality-gates.yml`](github-actions/quality-gates.yml) | The four gates: lint + unit tests, integration tests against real Postgres, security scan, SonarQube quality gate |
| [`github-actions/mirror-to-gitlab.yml`](github-actions/mirror-to-gitlab.yml) | The single GitHub → GitLab path, and the token-scoping notes that took three attempts to get right |
| [`github-actions/flag-workflow-changes.yml`](github-actions/flag-workflow-changes.yml) | Loud PR comment when the pipeline's own definition changes — a guardrail that cannot be edited away |
| [`gitlab-ci/build-and-deploy.yml`](gitlab-ci/build-and-deploy.yml) | Build one image per service, deploy by commit SHA, prune old tags |
| [`docs/access-model.md`](docs/access-model.md) | Who can reach what, and why the split is worth its cost |
| [`docs/gate-design.md`](docs/gate-design.md) | What each gate answers, and the shape decisions inside each one |
| [`docs/incident-regression.md`](docs/incident-regression.md) | The silent migration failure that shaped Gate 2 |
| [`examples/app/`](examples/app) | A minimal FastAPI + Vite app so the gates run against something real |
| [`gitlab-ci/docker-compose.yml`](gitlab-ci/docker-compose.yml) | Deploy target, referencing images by commit SHA |

## The four gates

| Gate | Answers | Tools | Notes |
|---|---|---|---|
| 1. Lint + unit tests | Is the change internally consistent, does the logic work? | Ruff, pytest, ESLint, Vitest | Linting scoped to changed files — see below |
| 2. Integration tests | Does it work on real Postgres with real migrations? | pytest, Alembic, PostgreSQL | Verifies the DB *landed* on the migration head, not just that the command ran |
| 3. Security scan | Vulnerable dependency, or a dangerous pattern? | Trivy, Bandit, npm audit | Dependency CVEs + SAST + frontend audit |
| 4. Code quality | Does it meet the project's bar? | SonarQube Community Edition | Self-hosted, spun up per run |

### Full tool list

| Layer | Tools |
|---|---|
| Forges | GitHub, GitHub Actions, GitLab, GitLab CI/CD |
| Containers & registry | Docker, Docker Compose, GitLab Container Registry |
| Backend language | Python 3.11, FastAPI, SQLAlchemy (async), Pydantic |
| Frontend language | Node.js 20, Vite, Vue |
| Build | Docker multi-stage builds, Vite production build |
| Lint / style | Ruff (Python), ESLint (JavaScript) |
| Test | pytest, pytest-asyncio, pytest-cov, Vitest |
| Database & migrations | PostgreSQL 15, Alembic, asyncpg |
| Security scanning | Trivy (dependency CVEs), Bandit (Python SAST), npm audit (frontend CVEs) |
| Code quality | SonarQube Community Edition (quality gate) |
| Deployment | SSH, `docker compose pull/up`, `scp` |
| Secrets handling | GitLab File-type CI/CD variables, GitHub Environment secrets |

### Why linting is scoped to changed files

Turning a linter on repo-wide fails on an unknown number of pre-existing
violations unrelated to the change under review. That is a blocked pipeline,
not a useful gate. Scoping to changed files still **blocks** on any violation
in a changed line — every new and modified line is held to the standard from
day one — while the rest of the codebase is cleaned up incrementally as files
are touched.

### Why Gate 2 verifies the migration result

A migration once failed silently in production: the command exited without an
error, the schema change rolled back, and the database stayed on the previous
revision — while the deploy reported success. Running migrations in CI would
not have caught it, because the migration command *succeeded*. So Gate 2 reads
back the revision the database actually reports and compares it to the
migration head. Details in
[`docs/incident-regression.md`](docs/incident-regression.md).

## The example application

The pipelines need a real target. `examples/app/` is a deliberately small
FastAPI backend plus a Vite frontend:

```
examples/app/
├── backend/
│   ├── app/main.py            # a health route, a read route, a pure function
│   ├── tests/
│   │   ├── test_unit.py       # fast, in-memory — Gate 1
│   │   └── test_integration.py # real Postgres — Gate 2
│   ├── alembic/               # one migration, with the revision-length warning
│   ├── Dockerfile             # multi-stage, non-root
│   ├── requirements.txt       # runtime only
│   └── requirements-dev.txt   # test + lint tooling, never in the image
└── frontend/
    ├── src/api.js             # two exported functions
    ├── src/api.test.js
    └── package.json
```

The dependency split matters: the Dockerfile installs only
`requirements.txt`, so test and lint tooling never reaches the production
image.

## Adapting this to your project

**Paths.** The workflows point at `examples/app/backend` and
`examples/app/frontend`. Replace those with your real layout — every location
is marked with a `PROJECT PATH` comment.

**Secrets.** Two, on a named environment (`gitlab-mirror`), never at repository
level:

| Variable | Type | Value |
|---|---|---|
| `GITLAB_TOKEN` | environment secret | Fine-grained PAT, resource *Code*, permission *Push*, scoped to one project |
| `GITLAB_REPO` | environment secret | `<group>/<project>` — no scheme, no host, no `.git` |

Plus, on GitLab:

| Variable | Type | Purpose |
|---|---|---|
| `SSH_PRIVATE_KEY` | variable | Deploy key |
| `SSH_HOST`, `SSH_USER` | variable | Deploy target |
| `ROOT_ENV`, `BACKEND_ENV` | **File** | Environment files shipped to the host |

A plain (non-File) variable is single-line only and silently truncates a
multi-line env file to its first line. Multi-line values must be File-type.

**Settings that live outside the YAML.** Branch protection, required status
checks, CODEOWNERS resolution — these cannot be expressed in a workflow file
and have to be configured once by hand. [`docs/access-model.md`](docs/access-model.md)
lists them with the reasoning.

## A note on scope

Not every project needs this. The two-forge split exists to separate
"can write code" from "can deploy", and that only matters once those are
different people. On a single-person project, one forge and the four gates are
the right shape; the mirror is overhead for no benefit. The design earns its
cost when at least one contributor must work without production access.

## Verifying these files

```bash
# Every YAML in this repository parses and every workflow has the expected jobs
python -c "
import yaml, glob
for f in glob.glob('**/*.yml', recursive=True):
    yaml.safe_load(open(f))
    print('ok', f)
"
```

## License

MIT — see [LICENSE](LICENSE).
