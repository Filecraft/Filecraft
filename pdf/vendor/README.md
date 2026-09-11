# Vendored PDF dependency

`pdf-lib.min.js` is the unmodified 525,099-byte UMD distribution from
[pdf-lib 1.17.1](https://github.com/Hopding/pdf-lib/releases/tag/v1.17.1), fetched
with `npm pack pdf-lib@1.17.1 --ignore-scripts` outside this repository.
Registry source: https://registry.npmjs.org/pdf-lib/-/pdf-lib-1.17.1.tgz

SHA-256 of UMD:
`0f9a5cad07941f0826586c94e089d89b918c46e5c17cf2d5a3c6f666e3bc694f`

The published UMD includes upstream dependencies; there are no runtime npm imports.
Retained licenses cover pdf-lib (MIT), @pdf-lib/standard-fonts (MIT), @pdf-lib/upng
(MIT), pako (MIT plus the separately retained `LICENSE.pako.zlib` source header),
and tslib (Apache-2.0 plus Microsoft
copyright notice). Pinned direct dependency versions were read from pdf-lib's
published package and yarn lockfile. The upstream lock also includes pako 1.0.10;
the supplementary 1.0.11 source notice is not proof of every embedded module
version. The zlib notice is not present in the minified UMD. Its verbatim header
comes from `package/lib/zlib/deflate.js`; source and notice hashes are recorded
in `PROVENANCE.json`. These supplementary license packages were packed
only to retain their original notices, not installed into runtime code.

`PROVENANCE.json` records registry tarballs, SHA-512 integrity and SHA-256 hashes
for each retained file. `node --test pdf/test/vendor.test.cjs` checks retained file
hashes. `python3 pdf/vendor-refresh.py` reproduces the maintainer download/copy step
in a temporary directory, verifies registry SHA-512, and updates provenance.
That script requires npm/network; **production and normal tests do not**.
Hashes establish byte identity, not security or signature verification. This is a
pinned older release, not a claim that upstream or its dependencies are free of
vulnerabilities. Audit before changing the pin or widening accepted PDF features.

Original Prepare source in the 0.9 development line uses Apache-2.0; historical
releases retain their supplied terms. Vendor components (including the vendor
portion of generated `workbench/worker-bundle.js`) retain their own licenses,
not a blanket original-code grant. See `../../docs/LICENSING.md`.
