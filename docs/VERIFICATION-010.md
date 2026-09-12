# Filecraft 0.10.0-beta.1 verification

Release source: `6a706c978a520f0e4b7442b583361a20b4cfe08e`.

- 84 desktop tests passed locally and independently; 52 browser tests passed.
- Five migration-tool tests passed and received a separate independent review.
- Installed Chromium, Edge and temporary Firefox extension workflows passed.
- Exact-tag native CI [34660148289](https://github.com/Filecraft/Filecraft/actions/runs/34660148289) passed Windows x64, Linux x64, macOS ARM64 and macOS x64. Each exercises frozen exports, PDF rendering/encryption and original/optimized auto-fit.
- [Staging audit 34660588526](https://github.com/Filecraft/Filecraft/actions/runs/34660588526) downloaded and audited those four exact archives, validated sidecar checksums, and uploaded unchanged files to the draft release.
- All seven public release ZIPs and checksum files were subsequently fetched without authentication and matched expected lengths and SHA-256 values.
- Site: 58 pages, 232 responsive layout checks, real preparation workflow. Cookie/third-party-resource/missing-alt checks returned zero; the loaded hosted workspace exported successfully with networking disabled.
- All nine prior release IDs, asset IDs, filenames, sizes and recorded digests were preserved through repository transfer. Historical source/assets keep their original licenses.

Release audits: [native-audit.json](https://github.com/Filecraft/Filecraft/releases/download/v0.10.0-beta.1/native-audit.json).

These are bounded tests, not independent security certification or universal document-fidelity guarantees. Windows remains unsigned and macOS not notarized. Browser and desktop capabilities differ. No custom neural model, extension marketplace listing or public Read the Docs instance is claimed.
