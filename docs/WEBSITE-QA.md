# v0.4.0 website verification

The site is a static HTML/CSS page with a dependency-free local preset guide.
It never processes user documents. Canonical URL and domain findings:
[DOMAIN.md](DOMAIN.md).

## Executed browser checks

- Viewports 1440, 768, 390 and 320 px: no horizontal document overflow.
- Local icon and real app screenshot load successfully.
- All three preset buttons switch displayed settings and `aria-pressed` state.
- Keyboard Enter activates the focused preset button.
- Native FAQ expansion and download-section anchor navigation work.
- Reduced motion reports `scroll-behavior: auto` and zero button transition duration.
- With JavaScript disabled, download links and installation guidance remain usable;
  a `noscript` message explains the nonessential preset guide.
- No window errors observed during the exercised interactions.
- All preset buttons have at least 44 px height at tested widths.
- Desktop, mobile and preset-section screenshots inspected. Smaller privacy labels
  were enlarged and the product screenshot brought closer to the hero.

These are targeted checks, not full accessibility certification or every-browser
coverage. The development screenshot was replaced with a real 0.4.0 window capture
showing synthetic-only source-color versus grayscale output.

## Automated checks

`python3 scripts/check-site.py` checks assets, anchors, unique IDs, image alt text,
HTTPS links, one H1, versioned download URL, local-only deferred script, no runtime
network/storage APIs, reduced-motion/focus styles, script <5 KB and markup/style/script
<50 KB combined. These static checks do not prove complete accessibility.

`node scripts/test-site.cjs` exercises preset values, invalid keys and independent
state. Node is only required to run website tests, not to build or use the app.

## Design review

Decide/Learn surface. Original forest-green editorial composition, alternating
paper-light review section, deliberate Helvetica Neue/Georgia/system-mono typography,
real app imagery and a functional settings guide. No remote fonts, WebGL, video,
framework runtime, fabricated testimonials or invented compression ratios.

Self-audit: no generic feature-tile grid, all-centered composition, decorative metrics,
icon toppers or violet gradient treatment. Color is not used as the only selected-state
signal: preset buttons expose `aria-pressed` and corresponding written settings.
