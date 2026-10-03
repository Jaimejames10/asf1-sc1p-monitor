#define MyAppName "ASFI Monitor"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Comarapa RL"
#define MyAppExeName "ASFI_Monitor_GUI.exe"
#define MyAgentExeName "ASFI_Monitor_Agent.exe"

[Setup]
AppId={{6E8D7E6D-0F53-4D5A-9D8A-4C2B1F49A2F1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\ASFI Monitor
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer-output
OutputBaseFilename=ASFI-Monitor-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\gui\{#MyAppExeName}
; Al actualizar sobre una instalación previa, cierra agente/GUI en uso
; para poder reemplazar los archivos.
CloseApplications=force
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "autostart"; Description: "Iniciar ASFI Monitor automáticamente al iniciar sesión"; GroupDescription: "Inicio automático:"

[Files]
Source: "dist\ASFI_Monitor_GUI\*"; DestDir: "{app}\gui"; Excludes: "ms-playwright\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\ASFI_Monitor_Agent\*"; DestDir: "{app}\agent"; Excludes: "ms-playwright\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\ASFI_Monitor_CLI\*"; DestDir: "{app}\cli"; Excludes: "ms-playwright\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\ASFI_Monitor_Agent\ms-playwright\*"; DestDir: "{app}\ms-playwright"; Flags: ignoreversion recursesubdirs createallsubdirs

; La primera versión del instalador duplicó carpetas ms-playwright vacías
; dentro de gui, agent y cli; se eliminan para dejar una sola carpeta
; compartida y evitar que la resolución de Chromium las elija primero.
[InstallDelete]
Type: filesandordirs; Name: "{app}\gui\ms-playwright"
Type: filesandordirs; Name: "{app}\agent\ms-playwright"
Type: filesandordirs; Name: "{app}\cli\ms-playwright"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\gui\{#MyAppExeName}"; WorkingDir: "{app}\gui"; AppUserModelID: "ASFI.Monitor"
Name: "{userstartup}\ASFI Monitor Agent"; Filename: "{app}\agent\{#MyAgentExeName}"; WorkingDir: "{app}\agent"; Tasks: autostart

[Dirs]
Name: "{localappdata}\ASFI Monitor\logs"
Name: "{localappdata}\ASFI Monitor\exports"
Name: "{localappdata}\ASFI Monitor\backups"

[Run]
Filename: "{app}\gui\{#MyAppExeName}"; Description: "Abrir ASFI Monitor"; Flags: nowait postinstall skipifsilent
Filename: "{app}\agent\{#MyAgentExeName}"; Description: "Iniciar el agente de fondo"; Flags: nowait postinstall skipifsilent; Tasks: autostart

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
