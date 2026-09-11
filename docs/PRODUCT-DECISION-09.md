# Product decision: prepare for a requirement, verify the copy

Status: working decision for 0.9; not a shipped-capability announcement.

## Evidence, not market-size claims

Research on 2026-09-11 found recurring examples of target-size trial-and-error,
quality uncertainty and configuration overload. This is qualitative problem
research, not a representative survey or proof of market size.

- [Stirling issue 4442](https://github.com/Stirling-Tools/Stirling-PDF/issues/4442)
  reports over-compression relative to a requested target. It is closed; do not
  advertise it as a current unfixed competitor defect.
- [Stirling issue 7760](https://github.com/Stirling-Tools/Stirling-PDF/issues/7760)
  reports long target-size runs and options overridden by auto mode. Open when
  checked. A reporter's experience is not our benchmark.
- [PDF Arranger issue 389](https://github.com/pdfarranger/pdfarranger/issues/389)
  requests toolbar ordering that follows the workflow rather than feature groups.
- [Apple Preview documentation](https://support.apple.com/guide/preview/prvw1509/mac)
  explicitly warns that compression quality and resulting size vary.
- [OCRmyPDF cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html)
  warns about destructive preprocessing and refuses signed PDF modification by
  default. Preserve this safety expectation instead of burying it in a footer.
- [PDF24 Creator](https://tools.pdf24.org/en/creator) already offers offline tools.
  [Clop](https://lowtechguys.com/clop/) already integrates local optimisation and
  an SDK. Local processing and format breadth alone are not novel advantages.

Search also returned apparent promotional community posts. They were not counted
as independent demand evidence. Some search/extract requests were denied by the
search service; direct official pages and GitHub API were used where available.
No private documents, accounts or competitor customer data were accessed.

## Decision

Prepare is the workspace between a file and its next destination. Its primary
object is a prepared copy with explicit personal requirements and inspectable
evidence—not a converter menu, opaque health score or acceptance certificate.

Build the missing connective tissue:

1. Reuse the same version-1 requirement profile between browser and desktop.
2. Measure the actual output before publication; fail closed on failed rules.
3. Distinguish mechanical checks, unknown facts and human visual review.
4. Offer an optional receipt binding input/output byte hashes, measured facts,
   requirements and engine version. No document text, paths or names by default.
5. Verify a subsequently selected output against its receipt. Explain that an
   unsigned, editable receipt establishes byte identity, not authenticity.
6. Make a browser extension that opens this local preparation workspace beside
   an application tab. Explicit file selection, no browsing-history access,
   no upload interception, no host permissions, no background download monitoring.

Browser downloads metadata does not by itself grant the bytes of a local file.
Re-fetching authenticated download URLs would introduce credentials, permissions,
networking and expiration errors. Do not pretend to offer transparent handoff.

## Priority reasoning

| Direction | Value / differentiation | Cost and risk | Decision |
| --- | --- | --- | --- |
| Requirements + actual-output receipts | Connects recurring size/review friction across tools; composable CLI/UI contract | Bounded rule evaluation; must prevent false pass and stale evidence | Build |
| Local browser workspace | Meets user at upload time without accessing the portal | Packaging/CSP/browser qualification; store accounts are external gates | Build |
| Contextual desktop controls | Reduces configuration overload while retaining working adapters | Low architectural churn; must retain cancellation and keyboard access | Build |
| Universal conversion | Weak center, impossible fidelity promise | High maintenance and dependency/legal surface | Reject |
| Automatic upload interception | Convenient but fragile and privacy-invasive | Broad permissions, site dependence, credential risks | Defer |
| OCR/readability confidence score | Tempting but misleading without calibration | Hard to establish meaningful ground truth | Reject for this release |
| Native mobile rewrites | Long-term useful | Device/signing/toolchain qualification not established | Preserve honest experimental status |

Frequency/severity evidence is directional, not quantified. Willingness to pay,
retention and market size are unproven. Reusable team requirements and automation
could support a future business without paywalling privacy or imposing artificial
file limits. Do not introduce monetisation before validating repeat use.

## Identity and distribution

Keep Prepare and existing repository/package IDs; a generic descriptive name is
not proof of trademark clearance. Do not claim ownership of other namespaces.
Create one machine-readable product/distribution catalog and generate public
claims from it. Historical binaries retain their historical license and scope.

Store boundaries: Chrome requires developer registration, fee and agreement;
Edge requires Partner Center registration; AMO requires Mozilla submission and
signing; Safari requires Xcode, a containing app and Apple distribution identity.
No legal terms will be accepted and no payments made autonomously.

Sources: [Chrome](https://developer.chrome.com/docs/webstore/register),
[Edge](https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/create-dev-account),
[Firefox consent](https://extensionworkshop.com/documentation/develop/firefox-builtin-data-consent),
[Safari](https://developer.apple.com/documentation/safariservices/distributing-your-safari-web-extension).
