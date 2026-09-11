"""Human CLI over the same bounded desktop JSON worker. No shell or GUI import."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

def main(argv=None):
    parser=argparse.ArgumentParser(prog='prepare',description='Prepare a local copy; verify bytes, not acceptance.')
    sub=parser.add_subparsers(dest='action',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('source');prep.add_argument('--output',required=True);prep.add_argument('--target',required=True)
    prep.add_argument('--profile');prep.add_argument('--max-bytes',type=int);prep.add_argument('--max-pages',type=int)
    verify=sub.add_parser('verify');verify.add_argument('source');verify.add_argument('--receipt',required=True)
    caps=sub.add_parser('formats');caps.add_argument('source')
    args=parser.parse_args(argv)
    try:
        req={'source':args.source}
        if args.action=='prepare':
            from .requirements import validate_profile
            profile={'version':1,'id':'cli-personal','constraints':{}}
            if args.profile:
                with open(args.profile,'rb') as f:raw=f.read(65537)
                if len(raw)>65536:raise ValueError('Profile exceeds request budget.')
                profile=validate_profile(json.loads(raw))
            for key,val in [('bytes',args.max_bytes),('pageCount',args.max_pages)]:
                if val is not None:profile['constraints'].setdefault(key,{})['max']=val
            req.update(output=args.output,target=args.target,profile=validate_profile(profile))
        elif args.action=='verify':
            with open(args.receipt,'rb') as f:raw=f.read(65537)
            if len(raw)>65536:raise ValueError('Receipt exceeds request budget.')
            req.update(mode='verify-receipt',receipt=json.loads(raw))
        else:req['mode']='capabilities'
        raw=json.dumps(req).encode('utf-8')
        if len(raw)>65536:raise ValueError('Request exceeds 64 KiB.')
        cmd=[sys.executable,'--worker'] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve().parents[1]/'launch.py'),'--worker']
        kw={'start_new_session':True} if os.name=='posix' else {'creationflags':subprocess.CREATE_NO_WINDOW}
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,**kw)
        try:out,_=proc.communicate(raw,timeout=180)
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
            else:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=10)
            proc.kill();proc.communicate()
            raise ValueError('Interrupted or timed out. A copy completed just before interruption may remain.')
        if len(out)>1000000:raise ValueError('Worker response exceeds budget.')
        result=json.loads(out);print(json.dumps(result,ensure_ascii=True))
        return 1 if not result.get('ok') else 2 if args.action=='verify' and not result['result']['matches'] else 0
    except (ValueError,OSError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)[:800]}));return 1
