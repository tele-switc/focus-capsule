#ifndef MyAppVersion
#define MyAppVersion "2.0.0"
#endif

#define MyAppName "Focus Capsule"
#define MyAppExeName "Focus Capsule.exe"
#define MyAppPublisher "Focus Capsule Project"
#ifndef MyAppSource
  #define MyAppSource "..\dist\Focus Capsule"
#endif
#ifndef MyOutputDir
  #define MyOutputDir "..\dist\installer"
#endif

[Setup]
AppId={{A8DAE576-88A8-49F8-A005-E1C7000AB862}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoDescription={#MyAppName} installer
DefaultDirName={localappdata}\Programs\Focus Capsule
DefaultGroupName=Focus Capsule
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#MyOutputDir}
OutputBaseFilename=Focus-Capsule-{#MyAppVersion}-Windows-x64-Setup
SetupIconFile=..\assets\focus-capsule.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyAppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Focus Capsule"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Focus Capsule"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,Focus Capsule}"; Flags: nowait postinstall skipifsilent
