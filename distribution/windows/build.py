"""Unsigned per-user Inno Setup packaging of a verified frozen Windows runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile

VERSION = json.loads((Path(__file__).resolve().parents[2] / 'product.json').read_text())['version']
HERE = Path(__file__).resolve().parent


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def validate_bundle(bundle):
    exe = bundle / 'Filecraft-Desktop.exe'
    if not exe.is_file() or not (bundle / '_internal').is_dir():
        raise ValueError('Expected extracted Filecraft-Desktop onedir bundle')
    with exe.open('rb') as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b'MZ':
            raise ValueError('Expected Windows PE executable')
        stream.seek(struct.unpack_from('<I', header, 60)[0])
        if stream.read(6) != b'PE\0\0\x64\x86':
            raise ValueError('Expected Windows x64 executable')
    for name in ('FILECRAFT-LICENSE', 'FILECRAFT-NOTICE', 'DEPENDENCIES.json', 'OPENSSL-PROVENANCE.json'):
        if not (bundle / 'licenses' / name).is_file():
            raise ValueError('Missing exact bundled notice: ' + name)
    for path in bundle.rglob('*'):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('Windows bundle must not contain links/reparse junctions')
        if not (path.is_file() or path.is_dir()):
            raise ValueError('Special bundle file')
    if (bundle / 'Filecraft.exe').exists():
        raise ValueError('Bundle conflicts with GUI launcher')
    return exe


def build(bundle, output, iscc):
    exe = validate_bundle(bundle)
    if platform.system() != 'Windows' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('Build requires native Windows x64 with MSVC cl.exe and Inno Setup 6')
    if output.is_relative_to(bundle):
        raise ValueError('Output must not be inside input bundle')
    version = subprocess.check_output([str(exe), '--version'], text=True, timeout=60).strip()
    if VERSION not in version.split():
        raise ValueError('Unexpected frozen runtime version: ' + version)
    subprocess.run([str(exe), '--check-runtime'], check=True, timeout=60)
    compiler = shutil.which(iscc)
    if not compiler:
        raise RuntimeError('Inno Setup compiler not found; pass --iscc full path')
    output.mkdir(parents=True, exist_ok=True)
    name = f'Filecraft-{VERSION}-windows-x64-setup'
    artifact = output / (name + '.exe')
    if artifact.exists():
        raise FileExistsError(artifact)
    with tempfile.TemporaryDirectory(prefix='filecraft-inno-') as td:
        launcher = Path(td) / 'Filecraft.exe'
        subprocess.run(['cl.exe', '/nologo', '/O2', '/MT', '/W4', '/WX', '/DUNICODE', '/D_UNICODE', str(HERE / 'launcher.c'), '/Fe:' + str(launcher), '/Fo:' + str(Path(td) / 'launcher.obj'), '/link', '/SUBSYSTEM:WINDOWS', '/MACHINE:X64', 'user32.lib'], cwd=td, check=True)
        subprocess.run([compiler, '/DProductVersion=' + VERSION, '/DBundle=' + str(bundle), '/DLauncher=' + str(launcher), '/DOutputDir=' + str(output), '/DOutputName=' + name, str(HERE / 'filecraft.iss')], check=True)
    if not artifact.is_file():
        raise RuntimeError('Inno Setup produced no installer')
    digest = sha256(artifact)
    artifact.with_name(artifact.name + '.sha256').write_text(digest + '  ' + artifact.name + '\n', encoding='utf-8')
    metadata = {'artifact': artifact.name, 'version': VERSION, 'platform': 'windows', 'architecture': 'x64', 'signed': False, 'bytes': artifact.stat().st_size, 'sha256': digest, 'runtime_rebuilt': True, 'app_id': 'Filecraft.Desktop', 'install_scope': 'per-user', 'qualification': 'native install/GUI tests required before publication', 'bundle_files': {p.relative_to(bundle).as_posix(): sha256(p) for p in sorted(bundle.rglob('*')) if p.is_file()}}
    artifact.with_name(artifact.name + '.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in metadata.items() if k != 'bundle_files'}))
    return artifact


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--iscc', default='ISCC.exe')
    args = parser.parse_args()
    build(args.bundle.resolve(), args.output.resolve(), args.iscc)
