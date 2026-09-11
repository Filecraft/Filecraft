# Landing-page address

Checked for v0.4.0 on 2026-09-11 using GitHub's public account API.

- `prepare` exists as a GitHub user: https://github.com/prepare.
- `https://prepare.github.io` returns 404. That does not make the username available.
- `getprepare`, `prepare-app`, and `prepareformac` return account API 404s.
  No public account found is not proof a name can be registered: it may be
  reserved or unavailable under GitHub policy. None has been claimed.

GitHub Pages root subdomains belong to the matching user or organization,
not to an arbitrary repository name. Creating `prepare.github.io` inside
`gonisulaimann` would not acquire `https://prepare.github.io`.

Decision: retain the working, HTTPS project site and canonical URL:
https://gonisulaimann.github.io/Prepare/

A future dedicated organization (after successful registration) or a verified
custom domain can provide a branded root URL. Do not publish a CNAME until
ownership and DNS have been verified. No account rename or repository transfer
was performed for this release.

Reference: https://pages.github.com/
