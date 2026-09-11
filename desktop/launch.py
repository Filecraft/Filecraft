"""Prepare desktop entrypoint and bounded JSON worker transport."""
import json
import os
import sys


def worker():
    try:
        if os.name=='posix':
            import resource
            resource.setrlimit(resource.RLIMIT_CPU,(180,180))
            resource.setrlimit(resource.RLIMIT_FSIZE,(105*1024*1024,105*1024*1024))
            if sys.platform!='darwin':resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('Request exceeds 64 KiB.')
        request=json.loads(raw)
        if not isinstance(request,dict):raise ValueError('Request must be an object.')
        from prepare_suite.core import execute,capabilities,regular
        mode=request.get('mode','convert')
        if mode=='capabilities':result=capabilities(request['source'])
        elif mode=='inspect':
            from prepare_suite.pdf_ops import inspect
            result=inspect(str(regular(request['source'])),password=request.get('options',{}).get('password',''))
        elif mode=='verify-receipt':
            from prepare_suite.requirements import verify_receipt
            result=verify_receipt(request['receipt'],request['source'])
        elif mode=='convert':result=execute(request)
        else:raise ValueError('Unknown operation.')
        print(json.dumps({'ok':True,'result':result},ensure_ascii=True),flush=True)
        return 0
    except Exception as exc:
        # Do not return parser diagnostics or user passwords in JSON/logs.
        message=str(exc) if isinstance(exc,(ValueError,FileExistsError)) else 'Unable to process this file. Check the format, options and local engine installation.'
        print(json.dumps({'ok':False,'error':message[:800]},ensure_ascii=True),flush=True)
        return 1

if __name__=='__main__':
    if '--check-runtime' in sys.argv:
        # Synthetic packaging diagnostic only; never reads user documents.
        import io
        import pypdfium2 as pdfium
        from pypdf._crypt_providers import _cryptography
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(width=100,height=200)
        plain=io.BytesIO();writer.write(plain)
        with pdfium.PdfDocument(plain.getvalue()) as document:
            page=document[0];bitmap=page.render();bitmap.close();page.close()
        writer.encrypt('synthetic-runtime-password',algorithm='AES-256')
        encrypted=io.BytesIO();writer.write(encrypted)
        print('PASS PDF renderer and AES runtime');sys.exit(0)
    if '--worker' in sys.argv:sys.exit(worker())
    if '--cli' in sys.argv:
        from prepare_suite.cli import main
        sys.exit(main(sys.argv[sys.argv.index('--cli')+1:]))
    if '--version' in sys.argv:
        from prepare_suite import __version__
        print(__version__);sys.exit(0)
    if len(sys.argv)>1:
        from prepare_suite.cli import main
        sys.exit(main(sys.argv[1:]))
    from prepare_suite.gui import main
    main()
