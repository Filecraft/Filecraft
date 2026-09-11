# Contributing to Prepare

I'm Goni Sulaiman. I maintain Prepare as an independent, community-driven
utility. I want it to help someone finish an application, not become another
account they have to create. I welcome small fixes, accessibility feedback,
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

I keep two frontends: a native Mac app and a downloadable browser companion.
I don't describe the companion as a Windows EXE or Linux native binary.

### Native Mac

I use macOS 14+ and Swift 6. I ship Apple Silicon builds; Intel native builds
are not release-tested. I don't add third-party Swift packages.

```sh
git clone --depth 1 https://github.com/gonisulaimann/Prepare.git
cd Prepare
swift run Prepare
swift run PrepareChecks --ui-contract
swift run -c release PrepareChecks --ui-contract --stress
swift build -c release -Xswiftc -warnings-as-errors -Xswiftc -strict-concurrency=complete
bash scripts/package.sh
codesign --verify --strict build/Prepare.app
```

I use `PrepareChecks`, an executable integration harness, rather than XCTest.
I generate synthetic fixtures and check PDF geometry, rendered pixels, byte
budgets, original protection, metadata handling and cancellation.

### Portable companion (Windows, Linux and Mac)

I open `portable/index.html` directly in a current desktop Chrome, Edge or
Firefox browser. I don't need a server or build step to use it. For development
checks I use Node 22+, Python 3.9+ and these test-only dependencies:

```sh
cd portable
npm ci --ignore-scripts
npx playwright install --with-deps chromium firefox
npm test
cd ..
python -m pip install pymupdf==1.26.5
python scripts/check-portable-pdf.py
python scripts/test_portable_budget.py
python scripts/package_portable.py
```

I recommend a Python virtual environment. I keep Node, Playwright, browsers
and PyMuPDF out of the release archive. I test actual file-URL workflows with
networking disabled, then independently render the exported PDFs. I run the
same browser checks on Windows and Linux CI; I don't infer support from a Mac
browser test alone.

### Website and release guards

```sh
python3 scripts/check-site.py
node scripts/test-site.cjs
python3 scripts/test_release_budget.py
git diff --check
```

I enforce decimal-byte budgets: Mac executable below 2 MB, app files below
3 MB and ZIP below 1.5 MB; Portable below 200 KB expanded and 100 KB zipped.
I exclude the user's existing browser and OS frameworks, not hidden bundled
runtimes. I document prerequisites because those downloads are not tiny.

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

For the 0.9 development line onward, contributions to original Prepare work
are accepted under Apache-2.0. Contribute only work you have permission to
license, retain upstream notices, and identify third-party imports. No copyright
assignment or separate CLA is required. Earlier releases retain their supplied
licenses; see [licensing scope](docs/LICENSING.md).

I make the final scope and release decisions, and I try to explain them.
I don't promise a response SLA. I welcome a focused follow-up, but I would
rather ship one checked improvement than rush a queue of unverified changes.
