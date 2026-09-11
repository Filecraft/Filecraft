# Filecraft identity migration

Filecraft continues Prepare. The repository was transferred, not copied: Git history,
issues and all nine existing releases retain their identities. Historical assets
keep their original names and licenses. Current source remains Apache-2.0.

Canonical repository: https://github.com/Filecraft/Filecraft
Canonical site: https://filecraft.github.io/

The protected personal website repository is not edited or redirected. The new
organization site is a separate repository. GitHub redirects the old project URL;
clients should update remotes to git@github.com:Filecraft/Filecraft.git.

## Compatibility decisions

- New desktop/workspace/extension artifacts are named Filecraft.
- Python `prepare_suite`, JS `PreparePDF`/`PrepareEngine`, receipt schema IDs,
  internal worker variables and profile IDs remain stable for existing consumers.
  They are compatibility identifiers, not current marketing names.
- Desktop CLI still accepts the existing command syntax.
- The unpublished Firefox developer extension adopts workspace@filecraft.github.io.
  Existing temporary/unpacked installs should be removed and replaced explicitly.
- The small Swift image app is retained as legacy source under its established
  bundle identity; it is not a new Filecraft desktop release or recommended surface.
- Native Android development and its workflow are retired. Source remains in tags
  through v0.9.0-beta.1 and historical unsigned releases remain available. No iOS or
  iPadOS native app was shipped; no mobile platform is claimed now.
- Previously distributed packages are not edited, renamed or relicensed.

## Scope and control

The main repository owns engine, desktop, CLI, web/extension adapters and docs.
The organization site repository owns static presentation only. Splitting each
small shared component into a separate repository would introduce version drift
without a demonstrated benefit.

Future online assistance is a separate consent/security boundary, not a silent
replacement for local transformations. There is no shipped fine-tuned model.
