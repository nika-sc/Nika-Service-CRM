# Bootstrap PostgreSQL Dataset

This folder contains a sanitized public PostgreSQL bootstrap dump for local development.

## Files

- `nikacrm_public_sanitized.sql` - schema + reference data + demo accounts only.

## Import

```bash
createdb -h localhost -p 5432 -U postgres nikacrm
psql -h localhost -p 5432 -U postgres -d nikacrm -f database/bootstrap/nikacrm_public_sanitized.sql
```

## Demo credentials

- `admin` / `111111`
- `manager` / `111111`
- `master` / `111111`
- `viewer` / `111111`

Change passwords after first run in your environment.
