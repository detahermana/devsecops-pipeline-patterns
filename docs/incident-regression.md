# The incident that shaped Gate 2: a migration that failed silently

This is the reason Gate 2 verifies the database revision instead of just
running the migration and assuming it worked. It is written down because the
check looks redundant until you know what it is protecting against.

## What happened

A database migration was merged and deployed. The deploy log showed the
migration command running. No error appeared in the log. The deploy was
reported as successful.

The schema change had not been applied. The database was still on the previous
revision, and the application was now running code that assumed the new schema
existed.

## Why it failed, and why it failed quietly

The migration's revision identifier was longer than the column that stores it.
The migration tracking table uses a fixed-width column for the current
revision. A revision identifier longer than that column fails the insert.

In most setups this failure does not abort loudly. The migration step exits, the
schema change rolls back, and the database stays where it was — while the
command itself appears to have completed. Nothing checks the result.

A second, compounding problem: the deployment script that ran the migration did
not check the exit code. So even a non-zero exit would have been passed over
rather than stopping the deploy.

## The two fixes

**Shorten revision identifiers.** The immediate cause was a long identifier.
Keeping them short avoids the column-width problem directly, and the migration
template carries a comment saying so.

**Make the pipeline prove the migration landed.** This is the durable fix, and
it addresses the class of problem rather than the instance:

1. Run the real migrations against a real database in CI (Gate 2), so a broken
   migration fails before it can reach production.
2. **Read back the revision the database actually reports and compare it to the
   migration head.** A mismatch fails the build.

Step 2 is the important one. Step 1 alone would still have passed in this
incident — the migration command "succeeded". Verifying the outcome, not the
command, is what catches a silent failure.

3. Check the exit code in the deploy path, so a failing migration stops the
   deploy instead of being reported as success.

## What this generalises to

The lesson is broader than migrations:

**Verify outcomes, not commands.** A command that exits zero has not
necessarily done what it was supposed to. Where the consequence of a silent
failure is a broken production state, check the state afterwards.

**A gate that cannot fail is not a gate.** If a step's failure mode is "logs an
error and continues", it is documentation, not a check. Gate 2 fails the build
on a revision mismatch — that is why it is a gate.

**Silent failures are worse than loud ones.** This one cost time precisely
because nothing was wrong in the log. Production would have been better served
by a failed deploy than by a successful-looking one that shipped mismatched
code and schema.

**Write the reason down next to the check.** The verification step in
`quality-gates.yml` carries a pointer to this document. Without it, the next
person to read the workflow sees a check that looks redundant and removes it.

## Where it lives in the pipeline

`github-actions/quality-gates.yml`, Gate 2, in two steps:

- `Run migrations against a real Postgres database` — runs the migration,
  fails on non-zero exit
- `Verify the database landed on the migration head` — reads back
  `alembic current`, compares to `alembic heads`, fails on mismatch

Both steps are required status checks on the protected branch, so neither can
be merged past.
