"""Package an already verified Ubuntu 24.04 x64 frozen runtime; never refreeze."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import tempfile

VERSION = json.loads((Path(__file__).resolve().parents[2] / 'product.json').read_text())['version']
DEB_VERSION = VERSION.replace('-beta.', '~beta.') + '-1'
DEPENDS = 'libc6 (>= 2.39), libgcc-s1, libstdc++6, zlib1g, libfontconfig1, libfreetype6, libx11-6, libxext6, libxrender1, libxft2, libxss1, libxcb1'
ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def validate_bundle(bundle):
    exe = bundle / 'Filecraft-Desktop'
    if not exe.is_file() or not (bundle / '_internal').is_dir():
        raise ValueError('Expected extracted Filecraft-Desktop onedir bundle')
    with exe.open('rb') as stream:
        header = stream.read(20)
    if header[:6] != b'\x7fELF\x02\x01' or header[18:20] != b'\x3e\x00':
        raise ValueError('Expected Linux x86-64 ELF executable')
    for name in ('FILECRAFT-LICENSE', 'FILECRAFT-NOTICE', 'DEPENDENCIES.json', 'OPENSSL-PROVENANCE.json'):
        if not (bundle / 'licenses' / name).is_file():
            raise ValueError('Missing exact bundled notice: ' + name)
    for path in bundle.rglob('*'):
        if path.is_symlink():
            if os.path.isabs(os.readlink(path)) or not path.resolve().is_relative_to(bundle.resolve()) or not path.exists():
                raise ValueError('Unsafe or dangling bundle symlink: ' + str(path))
        elif not (path.is_file() or path.is_dir()):
            raise ValueError('Special file in bundle: ' + str(path))
    return exe


def build(bundle, output):
    exe = validate_bundle(bundle)
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('Build requires native Ubuntu 24.04 x64')
    release = platform.freedesktop_os_release()
    if release.get('ID') != 'ubuntu' or release.get('VERSION_ID') != '24.04':
        raise RuntimeError('Only Ubuntu 24.04 is qualified')
    if output.is_relative_to(bundle):
        raise ValueError('Output must not be inside input bundle')
    # ZIP extraction may lose POSIX mode bits. Do not modify the verified input.
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / f'filecraft_{DEB_VERSION}_ubuntu24.04_amd64.deb'
    if artifact.exists():
        raise FileExistsError(artifact)
    with tempfile.TemporaryDirectory(prefix='filecraft-deb-') as td:
        stage = Path(td) / 'root'
        app = stage / 'opt/filecraft'
        shutil.copytree(bundle, app, symlinks=True)
        for path in stage.rglob('*'):
            if path.is_symlink():
                continue
            mode = 0o755 if path.is_dir() else 0o644
            if path.is_file():
                with path.open('rb') as stream:
                    if stream.read(4) == b'\x7fELF' or path.stat().st_mode & stat.S_IXUSR:
                        mode = 0o755
            path.chmod(mode)
        runtime = app / exe.name
        version = subprocess.check_output([str(runtime), '--version'], text=True, timeout=60).strip()
        if VERSION not in version.split():
            raise ValueError('Unexpected frozen runtime version: ' + version)
        subprocess.run([str(runtime), '--check-runtime'], check=True, timeout=60)
        wrapper = stage / 'usr/bin/filecraft'
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text('#!/bin/sh\nexec /opt/filecraft/Filecraft-Desktop "$@"\n', encoding='utf-8')
        wrapper.chmod(0o755)
        desktop = stage / 'usr/share/applications/io.filecraft.Filecraft.desktop'
        desktop.parent.mkdir(parents=True)
        shutil.copyfile(Path(__file__).with_name(desktop.name), desktop)
        icon = stage / 'usr/share/pixmaps/filecraft.png'
        icon.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / 'docs/assets/filecraft-avatar.png', icon)
        control = stage / 'DEBIAN/control'
        control.parent.mkdir()
        size = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
        control.write_text(f'Package: filecraft\nVersion: {DEB_VERSION}\nSection: utils\nPriority: optional\nArchitecture: amd64\nMaintainer: Filecraft contributors <noreply@github.com>\nHomepage: https://github.com/Filecraft/Filecraft\nDepends: {DEPENDS}\nInstalled-Size: {(size + 1023) // 1024}\nDescription: Local-first file preparation desktop (Ubuntu 24.04 x64 beta)\n Frozen Filecraft runtime; no services, updater or automatic downloads.\n Unsigned standalone package. Third-party notices in /opt/filecraft/licenses.\n', encoding='utf-8')
        for path in stage.rglob('*'):
            if path.is_dir() and not path.is_symlink():
                path.chmod(0o755)
        control.chmod(0o644)
        subprocess.run(['dpkg-deb', '--root-owner-group', '-Zxz', '--build', str(stage), str(artifact)], check=True)
    digest = sha256(artifact)
    artifact.with_name(artifact.name + '.sha256').write_text(digest + '  ' + artifact.name + '\n', encoding='utf-8')
    metadata = {'artifact': artifact.name, 'version': VERSION, 'package_version': DEB_VERSION, 'platform': 'ubuntu-24.04', 'architecture': 'amd64', 'signed': False, 'bytes': artifact.stat().st_size, 'sha256': digest, 'runtime_rebuilt': True, 'qualification': 'native install/GUI tests required before publication', 'bundle_files': {p.relative_to(bundle).as_posix(): sha256(p) for p in sorted(bundle.rglob('*')) if p.is_file()}, 'bundle_symlinks': {p.relative_to(bundle).as_posix(): os.readlink(p) for p in sorted(bundle.rglob('*')) if p.is_symlink()}}
    artifact.with_name(artifact.name + '.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in metadata.items() if not k.startswith('bundle_')}))
    return artifact


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    build(args.bundle.resolve(), args.output.resolve())
