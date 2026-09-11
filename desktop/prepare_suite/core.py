"""Local format registry and exclusive-output conversion. No network services."""
import hashlib
import gzip
import zipfile
import os
from pathlib import Path
import stat
import tempfile
import warnings
from PIL import Image, ImageOps
from . import documents, media

MAX_BYTES = 100 * 1024 * 1024
MAX_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
warnings.simplefilter('error', Image.DecompressionBombWarning)
IMAGE_INPUTS = {'.png','.jpg','.jpeg','.webp','.gif','.tif','.tiff','.bmp','.ico','.ppm','.pgm','.pbm','.pnm','.pcx','.tga','.dds','.icns','.jp2','.j2k','.avif'}
IMAGE_OUTPUTS = ['png','jpg','webp','tiff','bmp','gif','ico','ppm','pdf']

def regular(path):
    path = Path(path).absolute()
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Choose a regular local file, not a link or device.')
    if info.st_size < 1 or info.st_size > MAX_BYTES:
        raise ValueError('Input must contain 1 byte to 100 MiB.')
    return path

def capabilities(source):
    path = regular(source)
    ext = path.suffix.lower()
    targets = list(IMAGE_OUTPUTS) if ext in IMAGE_INPUTS else list(documents.TARGETS) if ext in documents.TEXT_INPUTS | documents.OFFICE_INPUTS else []
    if ext=='.pdf':
        targets=['pdf','png','jpg','txt']
        import shutil
        if shutil.which('tesseract'):targets+=['ocr-pdf','ocr-txt']
    targets += media.targets(ext) + ['zip','gz']
    return {'extension':ext, 'targets':targets, 'warnings':['Conversion can change colors, metadata and size; review the new copy.']}

def image_convert(source, output, target, options):
    quality = int(options.get('quality',85))
    if not 1 <= quality <= 95: raise ValueError('Quality must be 1–95.')
    with Image.open(source) as original:
        if original.width * original.height > MAX_PIXELS: raise ValueError('Image exceeds 20 million pixels.')
        if getattr(original,'n_frames',1)>1 and 'page' not in options:
            raise ValueError('Animated or multipage images require an explicit frame selection.')
        frame=int(options.get('page',0))
        if frame<0 or frame>=getattr(original,'n_frames',1):raise ValueError('Image frame is out of range.')
        original.seek(frame)
        image = ImageOps.exif_transpose(original)
        if target in ('jpg','pdf','ppm'):
            base=Image.new('RGB',image.size,'white')
            if 'A' in image.getbands(): base.paste(image,mask=image.getchannel('A'))
            else: base.paste(image.convert('RGB'))
            image=base
        fmt={'jpg':'JPEG','tiff':'TIFF','pdf':'PDF'}.get(target,target.upper())
        image.save(output,format=fmt,quality=quality)
    if target != 'pdf':
        with Image.open(output) as checked: checked.verify()
    return {'warnings':['One selected frame only; animation is not preserved. Metadata and color profiles may be removed. JPEG and WebP quality can be lossy.']}

def execute(request):
    source=regular(request['source'])
    destination=Path(request['output']).absolute()
    target=request['target']
    options=request.get('options',{})
    from .requirements import validate_profile, output_facts, receipt
    from . import __version__
    profile=validate_profile(request['profile']) if 'profile' in request else None
    extension={'ocr-pdf':'pdf','ocr-txt':'txt'}.get(target,target)
    aliases={'jpg':{'jpg','jpeg'},'tiff':{'tiff','tif'}}
    if destination.suffix.lower().lstrip('.') not in aliases.get(extension,{extension}):
        raise ValueError('Output extension must match the selected format.')
    if destination.exists() or destination.is_symlink(): raise FileExistsError('Choose a new output filename; existing files are never replaced.')
    if target not in capabilities(source)['targets']: raise ValueError('Unsupported conversion for this input.')
    # Snapshot inputs into a private directory; codecs never receive a caller path.
    with tempfile.TemporaryDirectory(prefix='.prepare-',dir=destination.parent) as directory:
        snapshot=Path(directory)/('source'+source.suffix.lower())
        flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
        fd=os.open(source,flags)
        with os.fdopen(fd,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): raise ValueError('Input changed to a non-regular file.')
            data=stream.read(MAX_BYTES+1)
        if not data or len(data)>MAX_BYTES: raise ValueError('Input size changed or exceeds 100 MiB.')
        snapshot.write_bytes(data)
        digest=hashlib.sha256(data).hexdigest()
        staged=Path(directory)/('output.'+target)
        if target == 'zip':
            with zipfile.ZipFile(staged,'x',compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot,arcname=source.name)
            with zipfile.ZipFile(staged) as archive:
                if archive.read(source.name)!=data: raise ValueError('Archive verification failed.')
            metadata={'warnings':['Lossless archive; already compressed files may grow.']}
        elif target == 'gz':
            staged.write_bytes(gzip.compress(data,mtime=0))
            if gzip.decompress(staged.read_bytes())!=data: raise ValueError('Archive verification failed.')
            metadata={'warnings':['Lossless gzip stream; original filename is not stored.']}
        elif snapshot.suffix=='.pdf':
            from . import pdf_ops
            staged.touch(mode=0o600)
            metadata=pdf_ops.convert(str(snapshot),str(staged),target,options)
        elif snapshot.suffix in media.FORMATS:
            metadata=media.convert(str(snapshot),str(staged),target,options)
        elif snapshot.suffix in documents.TEXT_INPUTS | documents.OFFICE_INPUTS:
            metadata=documents.convert(str(snapshot),str(staged),target,options)
        else:
            metadata=image_convert(str(snapshot),str(staged),target,options)
        size=staged.stat().st_size
        if not 0<size<=MAX_BYTES: raise ValueError('Output exceeds 100 MiB or is empty.')
        if target in ('pdf','ocr-pdf'):
            from pypdf import PdfReader
            with staged.open('rb') as check_stream:
                checked=PdfReader(check_stream)
                if checked.is_encrypted and not checked.decrypt(options.get('output_password','')):
                    raise ValueError('Output password verification failed.')
                if not 1<=len(checked.pages)<=100:raise ValueError('Output page count failed validation.')
        output_digest=hashlib.sha256(staged.read_bytes()).hexdigest()
        facts=output_facts(staged,target,options.get('output_password',''),destination.name)
        evidence=receipt(digest,len(data),output_digest,facts,profile,__version__)
        if evidence['readiness']['status']=='NOT_READY':
            raise ValueError('Output fails your requirements; no copy was published. Adjust the transformation or requirements.')
        # Hardlink publication is atomic and refuses a destination created meanwhile.
        # A local filesystem supporting hard links is required; never use overwrite.
        os.link(staged,destination)
    return {**metadata,'receipt':evidence,'output':str(destination),'bytes':size,'input_bytes':len(data),'input_sha256':digest,'sha256':output_digest}
