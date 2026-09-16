; Script do Inno Setup (Sprint 12) para o instalador Windows do
; Detector de Duplicidade de Materiais.
;
; Pre-requisito: rodar "pyinstaller packaging/app.spec" antes (Sprint 11),
; gerando dist/DetectorDuplicidadeMateriais/ com o executavel e os
; arquivos de config/ empacotados.
;
; Uso: abrir este arquivo no Inno Setup Compiler (ou "iscc packaging/installer.iss")
; em uma maquina Windows. Gera um instalador .exe unico em build/output/.

#define MyAppName "Detector de Duplicidade de Materiais"
#define MyAppVersion "0.1.0"
#define MyAppExeName "DetectorDuplicidadeMateriais.exe"

[Setup]
AppId={{6C6F9D2B-6B7E-4D2C-9C7B-DUPMATERIAIS}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=DetectorDuplicidadeMateriais-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
; Instalador simples: sem privilegios de administrador, sem passos
; extras para o usuario final alem de "Seguinte/Instalar".
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos adicionais:"

[Files]
Source: "..\dist\DetectorDuplicidadeMateriais\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
