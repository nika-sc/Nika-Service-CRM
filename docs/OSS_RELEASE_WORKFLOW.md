# OSS Release Workflow

## Repositories

- Private production repository (current): `master` and `production`
- Public repository (new): `Nika-Service-CRM` (`main`)

## Private Delivery Flow (unchanged)

1. Develop and test in `master`
2. Commit and push to `master`
3. Merge to `production` only by explicit release command
4. Deploy `production` to VPS

## Public OSS Flow

1. Start from private `master` using release branch:
   - `oss/release-YYYYMMDD`
2. Run sanitization process (reference-only dataset policy)
3. Build public export package (exclude secrets, DB dumps, uploads, private infra docs)
4. Validate package:
   - secret scan
   - no sensitive artifacts
   - startup + migration smoke test
5. Sync export into local public workspace `../Nika-Service-CRM`
6. Commit and push to public `main`

## Hard Rules

- Never publish private `production` branch to public repository.
- Never publish `.env`, backups, dumps, attachment files, or private host data.
- Public repository history must remain clean of operational data.

## Recommended Automation (next step)

- Add a helper script that:
  - prepares sanitized export
  - runs secret scan
  - updates local `../Nika-Service-CRM`
  - creates release summary
