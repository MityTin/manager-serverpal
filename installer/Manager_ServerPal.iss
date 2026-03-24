; Manager ServerPal Installer Script
; Build with Inno Setup 6 (ISCC.exe)

#define MyAppName "Manager ServerPal"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "MityTinDev"
#define MyAppExeName "Manager_ServerPal.exe"
#define MyServerPalExeName "Manager_ServerPal_App.exe"
#define MyAppId "{{C4D8A8F4-7C3D-4F16-BBC0-9F0A1A7C4E10}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoDescription={#MyAppName} Installer
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=Manager_ServerPal_Setup_v1.0.2
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesAssociations=no
CloseApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Táº¡o biá»ƒu tÆ°á»£ng ngoÃ i Desktop"; GroupDescription: "TÃ¹y chá»n:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\{#MyServerPalExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\HUONG_DAN.txt"; DestDir: "{app}"; Flags: ignoreversion
; ÄÃ³ng gÃ³i trá»n bá»™ dá»± Ã¡n Ä‘á»ƒ app cháº¡y Ä‘á»™c láº­p (khÃ´ng cáº§n Python/Node cÃ i sáºµn).
Source: "..\*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\_ui_assets\*"; DestDir: "{app}\_ui_assets"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"
Source: "..\_datadb\*"; DestDir: "{app}\_datadb"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"
Source: "..\_map_assets\*"; DestDir: "{app}\_map_assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Excludes: "__pycache__\*,*.pyc"
Source: "..\palserver-online-map-main\*"; DestDir: "{app}\palserver-online-map-main"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Excludes: "node_modules\*.cache\*,*.log,*.tmp,__pycache__\*,*.pyc"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\HÆ°á»›ng dáº«n ({#MyAppName})"; Filename: "{app}\HUONG_DAN.txt"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Cháº¡y {#MyAppName}"; Flags: nowait postinstall skipifsilent


