"""Destructive native gate: run only on a disposable Ubuntu 24.04 x64 CI runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def inspect_archive(deb, flag):
    # Stream the real dpkg-deb archive, avoiding a full in-memory runtime copy.
    process = subprocess.Popen(['dpkg-deb', flag, str(deb)], stdout=subprocess.PIPE)
    entries = []
    with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts:
                raise AssertionError('Unsafe archive path')
            if member.uid != 0 or member.gid != 0:
                raise AssertionError('Non-root package ownership: ' + member.name)
            if member.mode & 0o6000:
                raise AssertionError('Set-ID package entry')
            entries.append(member.name.removeprefix('./').rstrip('/'))
    if process.wait() != 0:
        raise AssertionError('dpkg-deb archive read failed')
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--allow-disposable-runner', action='store_true')
    args = parser.parse_args()
    if not args.allow_disposable_runner:
        parser.error('Requires --allow-disposable-runner; installs/removes package via sudo')
    deb = args.artifact.resolve()
    repo = Path(__file__).resolve().parents[2]
    if Path('/opt/filecraft').exists() or subprocess.run(['dpkg-query', '-W', 'filecraft'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        raise RuntimeError('Refusing to replace an existing Filecraft installation')
    metadata = json.loads(deb.with_name(deb.name + '.metadata.json').read_text())
    assert digest(deb) == metadata['sha256']
    assert subprocess.check_output(['dpkg-deb', '--field', str(deb), 'Architecture'], text=True).strip() == 'amd64'
    control = inspect_archive(deb, '--ctrl-tarfile')
    assert set(control) <= {'', '.', 'control'}, control
    files = inspect_archive(deb, '--fsys-tarfile')
    for required in ('opt/filecraft/Filecraft-Desktop', 'usr/bin/filecraft', 'usr/share/applications/io.filecraft.Filecraft.desktop', 'opt/filecraft/licenses/FILECRAFT-NOTICE'):
        assert required in files, required
    assert not any('/systemd/' in p or '/init.d/' in p or p.startswith(('home/', 'root/', 'etc/')) for p in files)
    with tempfile.TemporaryDirectory(prefix='filecraft-user-data-') as td:
        sentinel = Path(td) / 'user-data.txt'
        sentinel.write_text('synthetic data outside installation')
        installed = False
        try:
            for _ in range(2):
                installed = True # A failed dpkg configure can still unpack payload files.
                subprocess.run(['sudo', '-n', 'dpkg', '--install', str(deb)], check=True)
                for name, expected in metadata['bundle_files'].items():
                    assert digest(Path('/opt/filecraft') / name) == expected, name
                for name, target in metadata.get('bundle_symlinks', {}).items():
                    assert os.readlink(Path('/opt/filecraft') / name) == target
                subprocess.run([sys.executable, str(repo / 'desktop/check_frozen.py'), '/opt/filecraft/Filecraft-Desktop'], check=True, timeout=600)
                subprocess.run(['/usr/bin/filecraft', '--version'], check=True, timeout=60)
                subprocess.run([sys.executable, str(repo / 'distribution/test_installed_gui.py'), '--executable', '/usr/bin/filecraft', '--evidence', str(repo / 'build/distribution-evidence')], check=True, timeout=180)
            subprocess.run(['sudo', '-n', 'dpkg', '--remove', 'filecraft'], check=True)
            installed = False
            assert not Path('/opt/filecraft/Filecraft-Desktop').exists()
            assert not Path('/usr/bin/filecraft').exists()
            assert not Path('/usr/share/applications/io.filecraft.Filecraft.desktop').exists()
            assert sentinel.read_text() == 'synthetic data outside installation'
        finally:
            if installed:
                subprocess.run(['sudo', '-n', 'dpkg', '--remove', 'filecraft'], check=False)
    print('PASS real dpkg contents/root ownership/install/reinstall/uninstall and frozen export checks; OS-input GUI export tested')


if __name__ == '__main__':
    main()
