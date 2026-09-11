#!/usr/bin/env python3
"""Bounded public research: urllib transport + Scrapling parser; no browser evasion.
Run using build/filecraft-research-env/bin/python collect.py. Existing ledger resumes.
"""
import datetime, hashlib, json, time, urllib.request, urllib.error, urllib.robotparser
from pathlib import Path
from urllib.parse import urlsplit
from scrapling import Selector
ROOT = Path(__file__).resolve().parent
UA = 'FilecraftResearch/0.1 (bounded public workflow research; no training)'
URLS = [
('official','https://raw.githubusercontent.com/D4Vinci/Scrapling/main/README.md'),
('official','https://scrapling.readthedocs.io/en/latest/'),
('official','https://scrapling.readthedocs.io/en/latest/parsing/selection.html'),
('official','https://raw.githubusercontent.com/D4Vinci/Scrapling/main/docs/README_AR.md'),
('official','https://raw.githubusercontent.com/D4Vinci/Scrapling/main/docs/README_FR.md'),
('official','https://docs.readthedocs.com/platform/stable/tutorial/index.html'),
('official','https://docs.readthedocs.com/platform/stable/config-file/index.html'),
('reddit','https://www.reddit.com/r/pdf/comments/1mzkshm/how_to_email_a_pdf_larger_than_25mb/'),
('reddit','https://www.reddit.com/r/Wordpress/comments/1k0nnr7/file_size_limit_how_to_overcome/'),
('reddit','https://www.reddit.com/r/Adobe/comments/w4418p/how_do_i_email_a_pdf_that_is_larger_than_20mb/'),
('reddit','https://www.reddit.com/r/pdf/comments/1nctlr5/reduce_size_of_pdf_file_without_using_online_tool/'),
('github','https://github.com/Stirling-Tools/Stirling-PDF/issues/4442'),
('github','https://github.com/Stirling-Tools/Stirling-PDF/issues/4428'),
('github','https://github.com/Stirling-Tools/Stirling-PDF/issues/3489'),
('github','https://github.com/Stirling-Tools/Stirling-PDF/issues/5142'),
('github','https://github.com/ocrmypdf/OCRmyPDF/issues/1620'),
('forum','https://help.pdf24.org/en/questions/question/file-size'),
('forum','https://help.pdf24.org/en/questions/question/size-limitations'),
('forum','https://help.pdf24.org/en/questions/question/too-large-pdf/'),
('forum','https://help.pdf24.org/en/forums/topic/pdf24-v8-0-1-compression-issue'),
('forum','https://help.pdf24.org/en/forums/topic/merge-70-documents-9-pages-each-into-one-document/'),
('forum','https://help.pdf24.org/en/forums/topic/merge-big-files-doesnt-work-or-makes-blank-pages/'),
('official','https://ocrmypdf.readthedocs.io/en/latest/pdfsecurity.html'),
('official','https://ocrmypdf.readthedocs.io/en/latest/optimizer.html'),
('official','https://tools.pdf24.org/en/compress-pdf'),
('official','https://help.pdf24.org/en/how-to-merge-pdf-files-with-pdf24/'),
('forum','https://help.pdf24.org/en/forums/topic/pdf24-compress-only-save-reduced-size'),
]
assert len(URLS) <= 30
for folder in ('text','raw','robots'):
    (ROOT/folder).mkdir(exist_ok=True)
ledger = ROOT/'sources.jsonl'
seen = {json.loads(x)['url'] for x in ledger.read_text().splitlines()} if ledger.exists() else set()
robots_cache = {}
last = 0

def get(url):
    global last
    time.sleep(max(0, 1.2-(time.monotonic()-last)))
    last = time.monotonic()
    req = urllib.request.Request(url, headers={'User-Agent':UA})
    with urllib.request.urlopen(req, timeout=9) as r:
        body = r.read(2500000)
        return r.status, r.url, dict(r.headers), body

def allowed(url):
    host = '{0.scheme}://{0.netloc}'.format(urlsplit(url))
    if host not in robots_cache:
        robot_url=host+'/robots.txt'
        try:
            status, final, headers, body = get(robot_url)
            text = body.decode('utf-8','replace')
            p = urllib.robotparser.RobotFileParser()
            p.parse(text.splitlines())
            robots_cache[host]=(p, status, None)
            (ROOT/'robots'/(urlsplit(url).netloc+'.txt')).write_text(text)
        except urllib.error.HTTPError as e:
            robots_cache[host]=(None,e.code,None if e.code==404 else str(e))
        except Exception as e:
            robots_cache[host]=(None,None,str(e))
    p, status, error=robots_cache[host]
    return (not error and (p is None or p.can_fetch(UA,url))), {'url':host+'/robots.txt','status':status,'error':error}

for number,(kind,url) in enumerate(URLS,1):
    if url in seen: continue
    row={'id':number,'kind':kind,'url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'transport':'urllib.request','parser':'Scrapling Selector 0.4.15','training_use':False}
    try:
        ok, policy=allowed(url); row['robots']=policy
        if not ok:
            row['status']='robots_denied_or_unavailable'
        else:
            status,final,headers,body=get(url)
            row.update(http_status=status,final_url=final,headers=headers,raw_sha256=hashlib.sha256(body).hexdigest())
            raw=ROOT/'raw'/f'{number:02d}.body'; raw.write_bytes(body); row['raw_path']=str(raw.relative_to(ROOT))
            decoded=body.decode('utf-8','replace')
            if url.endswith('.md'):
                # Preserve Markdown source verbatim; use Scrapling to parse embedded HTML.
                selected=Selector(decoded); text=decoded; title=url.rsplit('/',1)[-1]
            else:
                selected=Selector(decoded)
                title=selected.css('title::text').get() or ''
                nodes=selected.css('article') or selected.css('main') or selected.css('body')
                text='\n'.join(nodes[0].xpath('.//text()[not(ancestor::script) and not(ancestor::style)]').getall()) if nodes else ''
                text='\n'.join(line.strip() for line in text.splitlines() if line.strip())
            if any(t in title.lower() for t in ('just a moment','access denied','blocked','robot or human')):
                row['status']='access_interstitial'
            elif len(text)<200:
                row['status']='empty_or_partial'
            else:
                row['status']='retrieved'
            path=ROOT/'text'/f'{number:02d}.txt'; path.write_text(text)
            row.update(title=title,text_path=str(path.relative_to(ROOT)),text_chars=len(text),text_sha256=hashlib.sha256(text.encode()).hexdigest())
    except urllib.error.HTTPError as e:
        row.update(status='http_denied_or_error',http_status=e.code,error=str(e))
    except Exception as e:
        row.update(status='error',error=repr(e))
    with ledger.open('a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(number,row['status'],url,flush=True)
rows=[json.loads(x) for x in ledger.read_text().splitlines()]
from collections import Counter
summary={'planned':len(URLS),'collected':len(rows),'unique':len({r['url'] for r in rows}),'statuses':dict(Counter(r['status'] for r in rows)),'kinds':dict(Counter(r['kind'] for r in rows))}
(ROOT/'collection-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
