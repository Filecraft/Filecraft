# Documentation hosting

Canonical public documentation is https://filecraft.github.io/documentation/.
The repository also includes a Read the Docs v2 configuration and an MkDocs technical guide.

Reproduce the technical docs build:

    python -m pip install -r docs/requirements.txt
    python -m mkdocs build --strict -f docs/mkdocs.yml

The Read the Docs import endpoint redirects to its login page. GitHub CLI credentials are not a Read the Docs account. No readthedocs.io hostname, project ownership or hosted build is claimed.

An organization maintainer can sign in at https://app.readthedocs.org/, import https://github.com/Filecraft/Filecraft, authorize its GitHub integration and select the default branch. Keep the Pages documentation canonical until the actual hosted project is verified. Review Read the Docs hosting, analytics, advertising and cookie settings independently; the Filecraft site’s no-cookie statement does not cover third-party domains.
