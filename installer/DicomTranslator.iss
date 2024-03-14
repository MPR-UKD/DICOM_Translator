[Setup]
AppId={{3F12B359-E222-4242-42B0-427B28D4242A}}
AppName=DicomTranslator
AppVersion=1.1
;AppVerName=Dicom Translator 1.1
AppPublisher=Karl Ludger Radke
DefaultDirName={pf}\DicomTranslator
DefaultGroupName=DicomTranslator
OutputBaseFilename=DicomTranslatorSetup
Compression=lzma
LicenseFile=LICENSE
SolidCompression=yes
SetupIconFile=assets/icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\DicomTranslator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\DicomTranslator"; Filename: "{app}\DicomTranslator.exe"
Name: "{commondesktop}\DicomTranslator"; Filename: "{app}\DicomTranslator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DicomTranslator.exe"; Description: "{cm:LaunchProgram,Dicom Translator}"; Flags: nowait postinstall skipifsilent
