# Small design system

Prepare uses restrained editorial typography and a workbench, not a dashboard.
The browser products share the same visual vocabulary; native apps retain
platform controls instead of imitating a website.

## Tokens

- Body: system UI, 16px / 1.5; no external fonts.
- Headings: Georgia/system serif, 28px section and 42px product heading.
- Spacing: 6, 8, 12, 16, 20, 24, 32px; borders rather than shadows.
- Dark canvas #0d1916, panel #172823, text #f2f3e9, muted #b3c6b9,
  accent #c5ee9b, divider #45594f.
- Light colors are defined in the browser stylesheet's light media query.
- Buttons: visible labels, 44px minimum height in the PDF workbench,
  4px corner radius; do not communicate an action through color alone.
- Focus: 3px accent outline with offset, never suppressed.

## Layout and interaction

A compact left rail holds source inputs and output requirements. The larger
right area holds pages, reversible actions and output review. Stack these
at narrow widths without horizontal scrolling. Use real labels, native
inputs, keyboard-operable buttons and an unobscured skip link. Filename
strings are text nodes, never HTML. Long names wrap.

Actions that change pages or requirements invalidate the generated copy.
Cancel terminates PDF parsing workers. Destructive workspace clearing asks
for confirmation; original documents are never changed. Import and Clear
reset history explicitly. Do not imply persisted state where none exists.

## Validation

PASS, FAIL and UNKNOWN are words, not color-only dots. Show actual values,
expected ranges/units and remediation. Parsing is not visual, accessibility
or standards certification. Keep uncertainty visible even after byte/page
checks pass. Report failures in an aria-live status region.

## Motion and theme

No decorative motion or transitions are required. Honor system light/dark
preferences and reduced motion. Avoid remote assets and runtime theme
storage. Browser theme and native appearance may differ by platform.

## Review gates

Check populated and empty states, long names, error paths, keyboard focus,
390/768/1440px widths, light/dark and no-JavaScript explanatory content.
Processing requires JavaScript; navigation/privacy/download documentation
must not pretend otherwise. Never replace real verification with screenshots.
