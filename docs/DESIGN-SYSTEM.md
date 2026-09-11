# Filecraft visual system

Identity: local preparation, measured evidence, honest unknowns.

## Tokens

| Token | Light | Dark |
| --- | --- | --- |
| Paper | #f4f1e8 | #17201d |
| Surface | #fffdf7 | #202d27 |
| Ink | #172c26 | #f1eee3 |
| Secondary text | #52625c | #b9c9bf |
| Accent | #174f40 | #bbd9c7 |
| Rule | #bbc6be | #53645a |

System sans-serif for controls and reading; Georgia for editorial headings;
system monospace for numbered stages, measurements and fingerprints. No network
fonts. Spacing follows 4/8/12/16/24/32/48/64px steps; fluid page margins. Borders
organize evidence; they are not decorative card shadows. No gradient identity.

Website mode: decide and learn. Broad editorial headings and a six-stage process
introduce the product; the actual workspace is one click away, not a fake demo.
Workspace mode: operate. Controls stay labeled, document measurements are not
presented as thumbnails, output state invalidates when its inputs change.
Desktop mode: native Tk controls respect platform conventions; the same stage
names and evidence semantics matter more than forcing CSS into native widgets.

## States and accessibility

Use explicit pass/fail/unknown text, never color alone. Unknown is not green.
No document health percentage or acceptance certification. Visible focus rings,
keyboard skip links, explicit file-input labels, touch-sized primary controls,
reduced-motion support and light/dark tests are required. No drag-only action.

Output ready means available to review—not that review has occurred. Receipts
are optional JSON evidence, unsigned and editable. Error copy states what failed,
what was preserved and what can be tried next. Do not promise cancellation can
undo a copy already published just before interruption.

Website/documentation share one layout generator; workspace shares the palette
but gives controls precedence. Preserve no-JS navigation and state clearly that
actual local processing needs JavaScript. Automated layout tests are not a
blanket WCAG certification or complete screen-reader qualification.
