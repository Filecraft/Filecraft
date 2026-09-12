# Windows and Linux distribution decisions

Scope: consumer installers for the version in product.json. The first packaging spike used hash-locked beta.1 runtimes. Qualification exposed an initial-window layout bug, so beta.2 rebuilds desktop runtimes with that narrowly scoped fix. Historical beta.1 archives are unchanged. No network installation, updater, associations, services or document-processing changes. Builders verify shape, architecture, version, runtime diagnostics and required notice presence; native CI records the source commit. SHA-256 is not a signature.

## Windows: unsigned per-user Inno Setup

Selected Inno Setup 6 (use 6.3+ for `x64os` syntax), not MSIX. `PrivilegesRequired=lowest` does not request elevation and uses non-administrative install mode.[1] Fixed `AppId=Filecraft.Desktop` preserves reinstall/uninstall identity across package versions.[2] No directory migration from historical Prepare products is attempted. Installs to `{localappdata}\Programs\Filecraft`; creates a per-user Start menu entry and registered uninstaller. No broad uninstall-delete directives: user documents/preferences outside the application tree are not touched. Same-version reinstall is tested; cross-version upgrade/downgrade and stale-file cleanup are not yet qualified.

MSIX is deferred because a deployable package must be signed and trusted on the target device.[3] No owner signing credentials exist in this task. Self-signed certificates and instructions to disable security controls are deliberately not a public distribution substitute. Installer, launcher and frozen runtime remain **unsigned**; SmartScreen/reputation warnings and organizational blocking remain possible. Nothing here claims Store approval.

The tiny `/SUBSYSTEM:WINDOWS` C launcher starts the unchanged console frozen executable with `CREATE_NO_WINDOW`, which runs console applications without a console window.[6] This preserves the existing frozen runtime's worker/CLI entrypoints and stdout protocol. The launcher deliberately accepts no CLI arguments: CLI, `--worker`, and test tools must call `Filecraft-Desktop.exe` directly. The launcher waits for GUI exit. It neither launches a browser nor performs network access. Compile only the launcher, never rebuild PyInstaller just to change subsystem flags.

### Windows native CI contract (repository root)

Prerequisites: Windows x64 runner with an **interactive desktop session**, Python 3.11+ (3.13 preferred), x64 MSVC developer environment exposing `cl.exe`, Inno Setup 6.3+ exposing `ISCC.exe`. Test interpreter requires Pillow, pypdf, reportlab for the existing independent checker. Tool provisioning is a CI responsibility, not an installer action. Use an ordinary non-elevated Windows account to qualify the no-admin promise.

```powershell
python distribution/windows/build.py --bundle C:\verified\Filecraft-Desktop --output C:\artifacts --iscc 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
pwsh -File distribution/windows/test-install.ps1 -Installer C:\artifacts\Filecraft-0.10.0-beta.2-windows-x64-setup.exe -AllowDisposableRunner
```

Test refuses pre-existing installations; verifies installer digest, every input payload byte (including exact notices), per-user registration and shortcut, actual installed frozen exports with `desktop/check_frozen.py`, MainWindowHandle, normal close/relaunch, reinstall and uninstall. A GUI-less/service runner must fail rather than report a worker test as GUI evidence. The gate now invokes OS-input-driven installed GUI import/export and relaunch. This must execute on the native runner before GUI qualification can be claimed; console-flash observation remains a visual check. No UI credentials or elevated bypass are used.

## Linux: Ubuntu 24.04 x64 `.deb`, not universal Linux

Selected a distro-qualified standalone DEB with `Architecture: amd64`, Debian version `0.10.0~beta.2-1`, and conservative `libc6 (>= 2.39)` floor. Only Ubuntu 24.04 x86-64 build hosts are accepted. This is not an AppImage, Flatpak, universal archive, ARM build, Ubuntu 22.04 claim or repository-signed APT channel. Package architecture/dependencies cannot enforce the distro identity at install time: other distributions are **unsupported**, even if dpkg accepts them.

`/opt/filecraft` holds the unchanged runtime and all its notices. `/usr/bin/filecraft` uses `exec` with quoted argument forwarding; desktop entry has no MIME associations and launches the GUI without a terminal. Icon bytes come directly from `docs/assets/filecraft-avatar.png`. No maintainer scripts, triggers, system services or network calls are packaged. `dpkg-deb --root-owner-group` writes root-owned archive entries without requiring a root build; installation/removal use dpkg under sudo in disposable CI.[4]

The frozen bundle already carries Tcl/Tk. Declare its X/font runtime dependencies (`libx11-6`, `libxft2`, `libxss1`, `libfontconfig1`) rather than assuming a headless base image contains them; Ubuntu's Tk package documents these library relationships.[5] Also declare libc/libgcc/libstdc++/zlib, FreeType, Xext, Xrender and XCB. CI must validate the real payload on a clean Ubuntu 24.04 environment; a dependency list is not proof all native extensions load. No full system Python/Tk, browser, office suite, OCR or media engine is dragged into package dependencies. X11 or an XWayland-compatible desktop is required for the GUI.

### Linux native CI contract (repository root)

Prerequisites: Ubuntu 24.04 x64, Python 3.11+, dpkg-deb, `xz`, declared package dependencies provisioned **before** the offline install gate. Test Python requires Pillow, pypdf, reportlab. sudo must work non-interactively; runner must be disposable and have no Filecraft installation. Input and output must be separate paths. Packaging uses temporary disk space for one copied runtime plus the resulting archive.

```sh
python3 distribution/linux/build.py --bundle /verified/Filecraft-Desktop --output /artifacts
python3 distribution/linux/test-install.py --artifact '/artifacts/filecraft_0.10.0~beta.2-1_ubuntu24.04_amd64.deb' --allow-disposable-runner
```

The gate streams actual `dpkg-deb` data/control tar archives, checks ownership/paths/no scripts, installs and reinstalls with `dpkg --install` (never downloads missing dependencies), checks every runtime byte/symlink and actual installed frozen exports, removes the package, and checks an external synthetic user-data sentinel survives. The gate now invokes installed GUI import/export via X11 input under Xvfb with Openbox; evidence is explicitly Xvfb-only, not a Wayland desktop certification. Package removal does not erase user data.

## Output and evidence contracts

Both builders accept required `--bundle` and `--output` paths, reject an existing final artifact and emit:

* Native `.exe` or `.deb` artifact.
* `<artifact>.sha256` using standard `digest  filename` syntax.
* `<artifact>.metadata.json`: filename, bytes, digest, version, target, explicit unsigned status, `runtime_rebuilt: true`, exact input-file digests; Linux also records symlink targets.
* Compact JSON summary on stdout after tool output. Native compiler/package-tool output is intentionally retained as evidence.

All licenses are copied byte-for-byte from the verified input bundle; no notices are regenerated, fetched, pruned or paraphrased. Metadata is an integrity inventory, not independent qualification or authentication. Builders run version and `--check-runtime` on the real native payload, but final publication still requires the separate native install gate and human GUI export evidence.

Portable regression command: `python3 -m unittest discover -s distribution/tests -p test_platform_packaging.py -v`. Tests use clearly synthetic headers solely for validation/path-safety checks; they never stand in for a frozen runtime or installer. Development performed on macOS: native Windows compiler/installer and Linux dpkg installation are **not executed locally**. Windows headers are absent locally, so native launcher compilation is explicitly pending. No release artifact, compatibility result or publication is claimed by static tests. AI assistance was used for these bounded packaging changes; local-first runtime behavior and the existing worker protocol were not edited.

## Sources

[1] https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm
[2] https://jrsoftware.org/ishelp/topic_setup_appid.htm
[3] https://learn.microsoft.com/en-us/windows/msix/package/signing-package-overview
[4] https://manpages.ubuntu.com/manpages/noble/en/man1/dpkg-deb.1.html
[5] https://packages.ubuntu.com/noble/libtk8.6
[6] https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags
