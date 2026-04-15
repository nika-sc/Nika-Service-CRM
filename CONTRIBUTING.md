# Contributing to Nika-Service-CRM

## Getting Started

1. Fork the repository.
2. Create a feature branch from `main`.
3. Run the project locally and verify your changes.
4. Open a pull request with a clear description and test notes.

## Development Rules

- Keep changes focused and atomic.
- Do not commit secrets, private dumps/backups, or uploaded files.
- The only allowed SQL dataset is `database/bootstrap/nikacrm_public_sanitized.sql`.
- Follow existing project style and naming patterns.
- Add or update tests for behavior changes when possible.

## Pull Request Checklist

- [ ] Code builds and app starts locally
- [ ] No sensitive data in changed files
- [ ] Documentation updated (if behavior changed)
- [ ] Migration added if DB schema changed

## Security Note

If you find a security issue, do not open a public issue immediately.  
Use private reporting instructions in `SECURITY.md`.
