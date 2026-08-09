# Vendored UI assets

These files are committed so self-hosted installations work without a CDN or
Node.js build step.

| Package | Version | Upstream | License |
| --- | --- | --- | --- |
| AdminLTE | 4.2.0 | https://github.com/ColorlibHQ/AdminLTE | MIT |
| Bootstrap | 5.3.8 | https://github.com/twbs/bootstrap | MIT |
| Bootstrap Icons | 1.13.1 | https://github.com/twbs/icons | MIT |

Do not edit minified vendor files. Put Service CRM public-landing customizations in
`static/css/nika-service-public.css`.

To upgrade, download the pinned `dist`/`font` assets from the corresponding
release and retain each package's `LICENSE` file.
