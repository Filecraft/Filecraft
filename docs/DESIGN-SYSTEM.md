# Filecraft visual system

## Website and repository identity

The website is for someone who needs a file ready to send. Lead with that task,
then show the download and browser workspace. Keep detailed format support,
checksums and implementation notes in the guides.

Use the original folded-paper mark in `docs/assets/filecraft-mark.svg`. Its three
shapes stay together. Do not stretch, outline or add shadows to the mark. Leave
at least one quarter of its width clear on each side. Repository banners and
avatar exports live beside the SVG. Public downloads: https://filecraft.github.io/brand/.

| Token | Light | Dark |
| --- | --- | --- |
| Paper | #faf9f6 | #171c1b |
| Surface | #ffffff | #222927 |
| Ink | #222824 | #f4f3ed |
| Secondary text | #61655f | #b5bcb6 |
| Text accent | #b54120 | #ffac8f |
| Rule | #dddfd7 | #414a45 |

The standalone logo uses #e77550. The illustrated paper stays light in either
mode. It is a labelled illustration, not a fake product screenshot. Use actual
workspace screenshots with synthetic samples when showing the software.

Use the system sans-serif stack. Large headings have close spacing; paragraph
text stays comfortably readable. No remote fonts, tracking scripts or UI framework.
The landing page pairs an oversized heading with an off-center paper composition.
Use rows for everyday tasks, not a wall of equal feature cards.

## Motion and language

Entry motion runs once. Buttons respond to hover and press. The three illustration
controls change the arrangement; they do not process a document. Disable transitions
and animation when the user prefers reduced motion. Do not hide essential content
behind animation or JavaScript.

English, French and Spanish landing pages are separate HTML routes. Language links
work without scripts. State clearly that the application and most guides are in
English. A theme switch applies for the current page without cookies or storage.

## Copy

Write what people can do and what they need to know. Prefer “Get your files ready
to send” to abstract claims about a document engine. No em dash punctuation in
project-owned copy. Preserve exact technical commands, measured evidence, license
notices and the maintainer's supplied disclosure figures.

Explain limitations at the decision point. The download page and landing page
must say Windows is unsigned and Mac apps are not notarized until that changes.
Never equate a matching receipt with authenticity, safety or acceptance by a portal.

## Accessibility and scope

Use visible focus, skip links, meaningful alt text, labelled buttons and large
touch targets. Verify narrow screens, light/dark modes, keyboard navigation,
reduced motion and no-JavaScript navigation. Automated checks are not WCAG certification.

This identity revision changes the website and repository presentation. Existing
application widgets, document processing and published packages are not redesigned
by this document. Originals, legal notices and historical release assets stay intact.
