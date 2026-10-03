# Frontend

Plain Vite + Vue entry point, kept minimal on purpose: the repository is about
the pipeline, and this exists so the frontend build, lint, and test steps have
something real to run against.

## Scripts

| Command | Run by |
|---|---|
| `npm ci` | Gate 1 (install) |
| `npx eslint <files>` | Gate 1 (lint, changed files only) |
| `npm run test:run` | Gate 1 (unit tests) |
| `npm run build` | Gate 1 (production build smoke check) |
| `npm audit --audit-level=high` | Gate 3 (dependency CVEs) |

`npm ci` is used rather than `npm install` because it installs exactly what
`package-lock.json` pins and fails if the lockfile and `package.json` disagree.
That reproducibility is what makes the gate meaningful — `npm install` could
silently resolve a different tree than the one that passed review.

## Dockerfile

Not included for the frontend: a static frontend typically builds to files
served by the reverse proxy rather than running as its own service, and the
build step is already exercised by Gate 1. Add a Dockerfile here if your
frontend is served by its own container.
