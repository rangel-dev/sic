; SIC - Inno Setup Script
#define AppName "SIC"
#define AppPublisher "RangelDev"
#define AppURL "https://github.com/rangel-dev/sic"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define AppExeName "SIC.exe"

[Setup]
AppId={{8C3A7B1E-7D4F-4E9A-B2C1-6E5D4F3A2B1C}
AppName={#AppName}
AppVersion={#MyAppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=SIC_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\icons\app.ico
; Permite que o instalador feche o app se estiver aberto
CloseApplications=yes
; Força o fechamento se necessário
CloseApplicationsFilter=SIC.exe
; Garante que o atalho na área de trabalho seja opcional mas padrão
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\SIC\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
