# Identity screening and migration boundary

Preferred name Preparo is not available as the exact GitHub owner:
https://github.com/preparo is an existing User account. A distinct App Store
product also uses Preparo: https://apps.apple.com/us/app/id6499164067
(Preparo: Tech Interview Prep). Do not claim namespace ownership or affinity.

Alternative candidate: **Preflio** (preflight + folio). It is format-neutral,
ASCII, short, and communicates preparation rather than editing. GitHub user lookup
returned 404 and repository search returned zero matches during this screening.
Neither result reserves a name or proves that organization signup will allow it.
Broader web screening was inconclusive: some searches were blocked or returned
unrelated results. No trademark clearance has been obtained. Do not label this
candidate legally cleared or silently publish a permanent rebrand on that basis.
Foliora and Readivo have active software products; Foliready is confusingly close
to FolioReady document software. Those candidates were rejected.

GitHub organization signup redirects this browser to login. CLI authentication
does not authenticate browser signup; `gh org` has no create subcommand here.
Only the owner can complete authentication and account/legal signup details.
No organization transfer, repository deletion, published asset replacement, or
bundle/application ID change has been performed. Existing Prepare releases and
identifiers remain valid. Brand-neutral engine internals let identity change
without rewriting document processing.

## Safe migration when ownership is established

1. Complete trademark/product screening appropriate to release markets and
   establish owner-controlled organization access.
2. Transfer the existing repository through GitHub's transfer mechanism, not a
   clone/delete replacement, to retain history, tags, issues and releases.
3. Verify each release asset hash and redirect after transfer; update remotes.
4. Deploy the matching OWNER/OWNER.github.io site before changing canonical URLs.
5. Keep the old Pages site as a tested redirect, including known documentation.
6. Preserve installed bundle/package identifiers unless an explicit tested
   upgrade path is supplied. Display-name changes do not require ID churn.
7. Retain the original licenses and notices in immutable historical releases.

Historical decision (superseded for new source): the maintainer then chose
Hippocratic License 3.0 core. The 0.9 development line transitions original
work to Apache-2.0; see LICENSING.md. Historical releases retain their terms.
