# Server hardening templates for Nika Service CRM

Used by [`scripts/linux_hardening.sh`](../../scripts/linux_hardening.sh).

| Path | Purpose |
|------|---------|
| `fail2ban/` | sshd + nginx scan-path jails + `recidive` (вечный бан повторчиков) |
| `nginx/host-proxy.conf.example` | Host TLS proxy → Docker :8080 |
| `nginx/modsecurity-snippet.conf.example` | Merge into host `server {}` |
| `modsecurity/` | DetectionOnly WAF config |

See [`docs/DEPLOY.md`](../../docs/DEPLOY.md) § Production hardening.
