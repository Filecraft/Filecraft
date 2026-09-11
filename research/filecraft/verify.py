#!/usr/bin/env python3
"""Offline audit and human-readable source ledger; no network requests."""
import collections, hashlib, importlib.metadata, json
from pathlib import Path
R=Path(__file__).resolve().parent
rows=sorted([json.loads(x) for x in (R/'sources.jsonl').read_text().splitlines()],key=lambda r:r['id'])
assert len(rows)==len({r['url'] for r in rows})==len({r['id'] for r in rows})==27
for row in rows:
    if row['status']=='retrieved':
        for part in ('raw','text'):
            path=R/row[part+'_path']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==row[part+'_sha256'],str(path)
        assert row['text_chars']>=200
counts=dict(collections.Counter(r['status'] for r in rows))
assert counts=={'retrieved':23,'robots_denied_or_unavailable':4}
report=(R/'REPORT.md').read_text()
# Every direct-retrieval evidence link should resolve to a ledger entry.
import re
links=set(re.findall(r'\]\((https?://[^)]+)\)',report))
known={r['url'] for r in rows}|{'https://github.com/D4Vinci/Scrapling'}
assert not links-known, links-known
lines=['# Source ledger','','Status is collection status, not a claim the issue remains unresolved. GitHub extraction includes visible issue body, not necessarily all comments. Reddit bodies were not requested because robots disallowed collection.','','| ID | Kind | Source | Collection | Local text |','|---|---|---|---|---|']
for r in rows:
    title=r.get('title') or r['url'].rstrip('/').split('/')[-1]
    title=title.replace('|',' / ').replace('\n',' ')
    path=r.get('text_path')
    lines.append(f"| S{r['id']:02d} | {r['kind']} | [{title}]({r['url']}) | {r['status']} | {f'[{path}]({path})' if path else 'not fetched'} |")
(R/'SOURCE_LEDGER.md').write_text('\n'.join(lines)+'\n')
result={'source_count':len(rows),'status_counts':counts,'raw_and_text_hashes':'all verified','report_source_links':'all ledger-backed','scrapling_version':importlib.metadata.version('scrapling')}
(R/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
