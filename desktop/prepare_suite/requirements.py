"""Declarative personal requirements and hash-bound, non-certifying receipts.

Matches version-1 shared engine profile fields. No executable recipes or I/O in
validation/evaluation. A hash match is byte identity, not authenticity or safety.
"""
import hashlib
import json
import re
from pathlib import Path

MAX_INTEGER=9007199254740991

def _object(value,keys):
    if not isinstance(value,dict) or set(value)-set(keys):
        raise ValueError('Invalid requirements: expected an object with known fields.')

def _integer(value,minimum=0,maximum=MAX_INTEGER):
    if type(value) is not int or not minimum<=value<=maximum:
        raise ValueError('Invalid requirements: integer outside supported bounds.')

def validate_profile(profile):
    if len(json.dumps(profile,ensure_ascii=False).encode('utf-8'))>1048576:
        raise ValueError('Invalid requirements: profile exceeds 1 MiB.')
    _object(profile,('version','id','description','constraints'))
    if type(profile.get('version')) is not int or profile['version']!=1 or not isinstance(profile.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}',profile['id']):
        raise ValueError('Invalid requirements: version or profile ID.')
    if 'description' in profile and (not isinstance(profile['description'],str) or not 1<=len(profile['description'])<=1000 or re.search(r'[\x00-\x1f\x7f]',profile['description'])):
        raise ValueError('Invalid requirements: description.')
    rules=profile.get('constraints');_object(rules,('bytes','pageCount','formats','dimensions','orientation','filename'))
    for key in ('bytes','pageCount'):
        if key in rules:
            r=rules[key];_object(r,('min','max'))
            if not r:raise ValueError('Invalid requirements: empty range.')
            for v in r.values():_integer(v,0 if key=='bytes' else 1)
            if r.get('min',0)>r.get('max',MAX_INTEGER):raise ValueError('Invalid requirements: inverted range.')
    if 'formats' in rules:
        f=rules['formats']
        if not isinstance(f,list) or not f or len(f)>3 or not all(isinstance(v,str) and v in ('png','jpeg','pdf') for v in f) or len(set(f))!=len(f):raise ValueError('Invalid requirements: formats must be PNG, JPEG or PDF.')
    if 'orientation' in rules and rules['orientation'] not in ('portrait','landscape','square'):raise ValueError('Invalid requirements: orientation.')
    if 'dimensions' in rules:
        d=rules['dimensions'];_object(d,('unit','minWidth','maxWidth','minHeight','maxHeight'))
        if d.get('unit') not in ('px','pt') or len(d)<2:raise ValueError('Invalid requirements: dimensions.')
        for k,v in d.items():
            if k!='unit':_integer(v,1,1000000)
        for axis in ('Width','Height'):
            if d.get('min'+axis,0)>d.get('max'+axis,1000000):raise ValueError('Invalid requirements: inverted dimensions.')
    if 'filename' in rules:
        n=rules['filename'];_object(n,('extensions','maxLength','asciiOnly'))
        if not n:raise ValueError('Invalid requirements: empty filename rule.')
        if 'maxLength' in n:_integer(n['maxLength'],1,255)
        if 'asciiOnly' in n and type(n['asciiOnly']) is not bool:raise ValueError('Invalid requirements: ASCII flag.')
        if 'extensions' in n:
            e=n['extensions']
            if not isinstance(e,list) or not 1<=len(e)<=16 or not all(isinstance(x,str) and re.fullmatch(r'[a-z0-9]{1,10}',x) for x in e) or len(set(e))!=len(e):raise ValueError('Invalid requirements: filename extensions.')
    return json.loads(json.dumps(profile))

def evaluate(facts,profile):
    rules=validate_profile(profile)['constraints'];checks=[]
    def check(code,state):checks.append({'code':code,'state':state})
    def ranged(value,r):
        return 'unknown' if value is None else 'pass' if r.get('min',0)<=value<=r.get('max',MAX_INTEGER) else 'fail'
    for key in ('bytes','pageCount'):
        if key in rules:check(key,ranged(facts.get(key),rules[key]))
    if 'formats' in rules:check('format','unknown' if facts.get('format') in (None,'unknown') else 'pass' if facts['format'] in rules['formats'] else 'fail')
    if 'filename' in rules:
        n=rules['filename'];name=facts.get('filename')
        ok=name is not None and len(name)<=n.get('maxLength',MAX_INTEGER) and (not n.get('asciiOnly') or all(32<=ord(c)<=126 for c in name)) and ('extensions' not in n or Path(name).suffix.lstrip('.').lower() in n['extensions'])
        check('filename','unknown' if name is None else 'pass' if ok else 'fail')
    for kind in ('dimensions','orientation'):
        if kind not in rules:continue
        pages=facts.get('pages',[])
        if not pages or len(pages)!=facts.get('pageCount'):check(kind,'unknown')
        for i,p in enumerate(pages):
            w,h=p.get('width'),p.get('height');state='unknown'
            if w is not None and h is not None:
                if kind=='orientation':state='pass' if ('square' if w==h else 'landscape' if w>h else 'portrait')==rules[kind] else 'fail'
                elif p.get('unit')==rules[kind]['unit']:
                    d=rules[kind];state='pass' if d.get('minWidth',0)<=w<=d.get('maxWidth',MAX_INTEGER) and d.get('minHeight',0)<=h<=d.get('maxHeight',MAX_INTEGER) else 'fail'
            check(kind+':'+str(i+1),state)
    status='NOT_READY' if any(c['state']=='fail' for c in checks) else 'NEEDS_REVIEW' if not checks or any(c['state']=='unknown' for c in checks) else 'CHECKS_PASSED'
    return {'status':status,'checks':checks,'scope':'Only listed mechanical requirements; not portal acceptance, visual quality, accessibility or security.'}

def output_facts(path,target,password='',filename=None):
    path=Path(path);fmt={'jpg':'jpeg','ocr-pdf':'pdf'}.get(target,target)
    facts={'format':fmt,'bytes':path.stat().st_size,'pageCount':None,'pages':[],'filename':filename or path.name}
    if fmt=='pdf':
        from .pdf_ops import inspect
        info=inspect(str(path),password=password)
        facts['pageCount']=info['page_count']
        facts['pages']=[{'width':p['width'],'height':p['height'],'unit':'pt'} for p in info['pages']]
    elif fmt in ('png','jpeg','webp','tiff','bmp','gif','ico','ppm'):
        from PIL import Image,ImageOps
        with Image.open(path) as im:
            image=ImageOps.exif_transpose(im)
            facts['pageCount']=1;facts['pages']=[{'width':image.width,'height':image.height,'unit':'px'}]
    return facts

def receipt(input_hash,input_bytes,output_hash,facts,profile,version):
    profile=profile or {'version':1,'id':'no-requirements','constraints':{}}
    return {'schema':'prepare-receipt','version':1,'engineVersion':version,'input':{'sha256':input_hash,'bytes':input_bytes},'output':{k:v for k,v in facts.items() if k!='filename'}|{'sha256':output_hash},'profile':validate_profile(profile),'readiness':evaluate(facts,profile),'visualReviewVerified':False,'authenticityVerified':False}

def verify_receipt(value,path):
    if not isinstance(value,dict) or value.get('schema')!='prepare-receipt' or value.get('version')!=1 or not isinstance(value.get('output'),dict):raise ValueError('Invalid Prepare receipt.')
    output=value['output'];digest=output.get('sha256');size=output.get('bytes')
    if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest) or type(size) is not int or not 1<=size<=100*1024*1024:raise ValueError('Invalid receipt output fingerprint.')
    from .core import regular,MAX_BYTES
    path=regular(path);h=hashlib.sha256();total=0
    import os,stat
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode):raise ValueError('Verification input must remain a regular file.')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as f:
        opened=os.fstat(f.fileno())
        if not stat.S_ISREG(opened.st_mode) or (before.st_dev,before.st_ino)!=(opened.st_dev,opened.st_ino):raise ValueError('Verification input changed while opening.')
        while chunk:=f.read(1048576):
            total+=len(chunk)
            if total>MAX_BYTES:raise ValueError('File grew beyond verification limit.')
            h.update(chunk)
    return {'matches':total==size and h.hexdigest()==digest,'bytes':total,'sha256':h.hexdigest(),'scope':'Byte identity only. The receipt is editable, unsigned and not proof of authenticity or acceptance.'}
