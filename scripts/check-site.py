"""Validate the legacy Pages redirect. Full site checks live in the site repo."""
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
DEST='https://gonisulaimann.github.io/'
class Redirect(HTMLParser):
    def __init__(self):super().__init__();self.canonical=None;self.refresh=None;self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href')
        if tag=='meta' and a.get('http-equiv')=='refresh':self.refresh=a.get('content')
        if tag=='a':self.links.append(a.get('href'))
p=Redirect();p.feed((ROOT/'docs/index.html').read_text())
assert p.canonical==DEST
assert p.refresh=='0;url='+DEST
assert DEST in p.links and DEST+'documentation/' in p.links
assert (ROOT/'docs/.nojekyll').is_file()
assert DEST in (ROOT/'README.md').read_text()
print('PASS legacy redirect, canonical and fallback website/documentation links')
