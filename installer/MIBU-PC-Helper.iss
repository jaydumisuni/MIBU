#define MyAppName "MIBU PC Helper"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "THETECHGUY TOOL"
#define MyAppURL "https://github.com/jaydumisuni/MIBU"
#define MyAppExeName "MIBU-PC-Helper.exe"

[Setup]
AppId={{23AA67F7-A0F0-4E33-98C8-E7E0CDE3AA03}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases/latest
DefaultDirName={autopf}\THETECHGUY TOOL\MIBU PC Helper
DefaultGroupName=MIBU PC Helper
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=MIBU-PC-Helper-Setup-{#MyAppVersion}
SetupIconFile=..\resources\live_ui\mibu_app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\pc-helper\release\MIBU-PC-Helper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MIBU PC Helper"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\MIBU PC Helper"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Uninstall MIBU PC Helper"; Filename: "{uninstallexe}"

[Run]
Filename: "{cmd}"; Parameters: "/c winget install -e --id Google.Chrome --silent --accept-source-agreements --accept-package-agreements"; StatusMsg: "Installing Chrome if required..."; Flags: runhidden waituntilterminated; Check: not ChromeInstalled
Filename: "{cmd}"; Parameters: "/c winget install -e --id Mozilla.Firefox --silent --accept-source-agreements --accept-package-agreements"; StatusMsg: "Installing Firefox if required..."; Flags: runhidden waituntilterminated; Check: not FirefoxInstalled
Filename: "{app}\{#MyAppExeName}"; Description: "Launch MIBU PC Helper"; Flags: nowait postinstall skipifsilent

[Code]
function ChromeInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe')) or
            FileExists(ExpandConstant('{pf}\Google\Chrome\Application\chrome.exe')) or
            FileExists(ExpandConstant('{pf32}\Google\Chrome\Application\chrome.exe'));
end;

function FirefoxInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{pf}\Mozilla Firefox\firefox.exe')) or
            FileExists(ExpandConstant('{pf32}\Mozilla Firefox\firefox.exe')) or
            FileExists(ExpandConstant('{localappdata}\Mozilla Firefox\firefox.exe'));
end;
