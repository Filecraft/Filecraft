# Contributing to Filecraft

I'm Goni Sulaiman. I maintain Filecraft independently, with community contributions.
I want it to help someone finish an application, not become another account they
have to create. I welcome small fixes, accessibility feedback,
Windows/Linux testing, clear bug reports and documentation just as much as code.

## Before you spend a weekend on it

I ask you to search existing issues and discuss large changes with me first.
I want to understand the user problem, the offline approach, the download and
memory costs, and how you will test the result. I may say no to a useful idea
if it would make this particular tool too large or too hard to maintain.

I ask for synthetic samples, never real identity documents or medical records.
I use [SECURITY.md](SECURITY.md) for private vulnerability reports and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for participation expectations.
My decision process is in [GOVERNANCE.md](GOVERNANCE.md).

## How I build and test

I maintain the Python/Tk desktop app for Windows, macOS and Linux, and the
local browser PDF workspace. The desktop CLI uses the same processing code.

### Desktop

Use Python 3.13 with Tk installed:

```sh
git clone https://github.com/Filecraft/Filecraft.git
cd Filecraft
python3 -m venv .venv
.venv/bin/python -m pip install -r desktop/requirements.txt
.venv/bin/python desktop/launch.py
PYTHONPATH=desktop .venv/bin/python -m unittest discover -s desktop/tests -v
```

On Windows use `.venv\Scripts\python.exe`; set `PYTHONPATH` using your shell.
Tesseract and FFmpeg are optional, separately installed tools. I use synthetic
fixtures for tests. See [the desktop guide](desktop/README.md).

### Browser and extensions

```sh
npm --prefix portable ci
npm --prefix portable exec -- playwright install chromium firefox
npm --prefix portable test
python3 extension/tests/test_package.py
```

The workspace opens from `workbench/index.html`. I test real file-URL workflows,
network isolation and exported files. Browser download prompts are controlled by
the browser, not an exclusive filesystem write in Filecraft.

### Website and release checks

The website has its own [repository](https://github.com/Filecraft/filecraft.github.io).
Its README explains layout, language and privacy tests. In this repository:

```sh
python3 scripts/test_filecraft_identity.py
python3 scripts/test_migration_tools.py
python3 scripts/test_presentation_copy.py
git diff --check
```

The Swift app and older portable image tool remain in source for historical
continuity. Their old byte budgets are not the current desktop suite's budgets.
Use [the release guide](docs/RELEASING.md) for current packaging and qualification.

## What I look for in a pull request

I ask for one concern per PR, a failing regression before the fix, and the
passing output afterward. For image changes I need rendered-pixel checks,
not just a PDF file that exists. I want keyboard, small-window, cancellation,
invalid-input and stale-result behavior checked too.

I protect these boundaries: no uploads, telemetry, accounts, hidden lookups,
auto-updaters or runtime downloads. I keep processing serial and bounded.
I invalidate output and review acknowledgments after edits. I don't overwrite
originals. In Portable I rely on the browser's download UI and say plainly
that I cannot enforce an exclusive filesystem write there.

I ask contributors to update behavior docs, use readable small functions and
avoid unrelated reformatting. I require disclosure of substantial AI help;
I still expect the contributor to understand, review and test every line.
I won't merge a generated patch on confidence alone.

## Licensing and review

For the 0.9 development line onward, contributions to original Filecraft work
are accepted under Apache-2.0. Contribute only work you have permission to
license, retain upstream notices, and identify third-party imports. No copyright
assignment or separate CLA is required. Earlier releases retain their supplied
licenses; see [licensing scope](docs/LICENSING.md).

I make the final scope and release decisions, and I try to explain them.
I don't promise a response SLA. I welcome a focused follow-up, but I would
rather ship one checked improvement than rush a queue of unverified changes.
