; Filecraft.Desktop is permanent: do not include a version in AppId.
[Setup]
AppId=Filecraft.Desktop
AppName=Filecraft
AppVersion={#ProductVersion}
AppPublisher=Filecraft contributors
DefaultDirName={localappdata}\Programs\Filecraft
DefaultGroupName=Filecraft
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
DisableDirPage=yes
UsePreviousAppDir=no
DisableProgramGroupPage=yes
Uninstallable=yes
UninstallDisplayIcon={app}\Filecraft.exe
SignedUninstaller=no
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
LicenseFile={#Bundle}\licenses\FILECRAFT-LICENSE
AppComments=Unsigned beta. Local processing; no updater or automatic downloads.

[Files]
Source: "{#Bundle}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Launcher}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Filecraft"; Filename: "{app}\Filecraft.exe"; WorkingDir: "{app}"
Name: "{userprograms}\Uninstall Filecraft"; Filename: "{uninstallexe}"

[Messages]
WelcomeLabel2=This installs Filecraft for your Windows account only.%n%nThis beta is UNSIGNED. Follow your organization's security policy; do not disable Windows security controls.%n%nFiles are processed locally. No updater, services, file associations or automatic downloads are installed.
