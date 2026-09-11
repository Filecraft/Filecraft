#!/usr/bin/env python3
"""Offline checks for the dependency-free project website."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.images = []
        self.h1_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.ids, "Duplicate element ID"
            self.ids.add(attrs["id"])
        if tag == "h1":
            self.h1_count += 1
        if tag == "html":
            assert attrs.get("lang") == "en"
        if tag == "script":
            raise AssertionError("Website must remain script-free")
        if tag in {"img", "link"}:
            target = attrs.get("src") if tag == "img" else attrs.get("href")
            if target:
                self.links.append(target)
        if tag == "img":
            assert "alt" in attrs, "All images need alt text (empty for decoration)"
            self.images.append(attrs["src"])
        if tag == "a":
            assert attrs.get("href"), "Empty link"
            self.links.append(attrs["href"])


def check():
    text = (SITE / "index.html").read_text()
    page = Page()
    page.feed(text)
    assert page.h1_count == 1
    assert "viewport" in text and "canonical" in text
    for link in page.links:
        parts = urlsplit(link)
        if parts.scheme:
            assert parts.scheme == "https", f"Unexpected external scheme: {link}"
            continue
        if parts.path:
            assert (SITE / parts.path).is_file(), f"Missing asset: {link}"
        elif parts.fragment:
            assert parts.fragment in page.ids, f"Missing anchor: {link}"
    css = (SITE / "style.css").read_text()
    assert "prefers-reduced-motion" in css and ":focus-visible" in css
    assert "@import" not in css and "url(http" not in css
    version_match = re.search(r'version = "([^"]+)"', (ROOT / "scripts/package.py").read_text())
    assert version_match is not None, "Packaging version is missing"
    version = version_match.group(1)
    assert f"/v{version}/Prepare-{version}-arm64.zip" in text
    assert "not notarized" in text and "not an OSI-approved" in text
    assert (SITE / ".nojekyll").is_file()
    print(f"PASS: website assets, {len(page.links)} links, anchors, accessibility basics, offline policy and v{version} download path")


if __name__ == "__main__":
    check()
