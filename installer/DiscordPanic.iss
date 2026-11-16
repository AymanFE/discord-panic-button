; Discord Panic Button - Inno Setup script
; Build: ISCC.exe installer\DiscordPanic.iss   (after PyInstaller has produced dist\DiscordPanic.exe)

#define AppName "Discord Panic Button"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppExe "DiscordPanic.exe"

[Setup]
AppId={{6B3D2B8E-6E0B-4C1F-9C55-0D1E5A9C7F21}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=AymanFE
AppPublisherURL=https://github.com/AymanFE/discord-panic-button
DefaultDirName={autopf}\DiscordPanic
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=DiscordPanicSetup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE

[Tasks]
Name: "autostart"; Description: "Start automatically when I sign in to Windows"; GroupDescription: "Startup:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\DiscordPanic\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Edit hotkey settings"; Filename: "{app}\{#AppExe}"; Parameters: "--config"
Name: "{group}\Restart (apply settings)"; Filename: "{app}\{#AppExe}"; Parameters: "--restart"
Name: "{group}\Stop {#AppName}"; Filename: "{app}\{#AppExe}"; Parameters: "--stop"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DiscordPanicButton"; ValueData: """{app}\{#AppExe}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName} now"; Flags: nowait postinstall

[UninstallRun]
Filename: "{app}\{#AppExe}"; Parameters: "--stop"; Flags: runhidden; RunOnceId: "StopApp"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{userappdata}\DiscordPanic"

[Code]
var
  HotkeyPage: TInputQueryWizardPage;
  TogglePage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  HotkeyPage := CreateInputQueryPage(wpSelectTasks,
    'Hotkey', 'Choose the key combination that minimizes Discord',
    'Join keys with +. Examples:' + #13#10 +
    '  num1+num3+num5   (hold numpad 1 and 3, then press 5)' + #13#10 +
    '  ctrl+alt+d' + #13#10 +
    '  ctrl+shift+f12' + #13#10 + #13#10 +
    'Modifiers: ctrl, alt, shift, win.  Numpad digits: num0-num9.' + #13#10 +
    'You can change this later from Start menu > Edit hotkey settings.');
  HotkeyPage.Add('Hotkey:', False);
  HotkeyPage.Values[0] := 'num1+num3+num5';

  TogglePage := CreateInputOptionPage(HotkeyPage.ID,
    'Behaviour', 'What should pressing the hotkey again do?', '', True, False);
  TogglePage.Add('Bring Discord back (toggle minimize / restore)');
  TogglePage.Add('Nothing - only ever minimize');
  TogglePage.SelectedValueIndex := 0;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = HotkeyPage.ID) and (Trim(HotkeyPage.Values[0]) = '') then
  begin
    MsgBox('Please enter a hotkey.', mbError, MB_OK);
    Result := False;
  end;
end;

function JsonBool(B: Boolean): String;
begin
  if B then Result := 'true' else Result := 'false';
end;

procedure StopRunning;
var
  RC: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, RC);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopRunning;
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Dir, Json, HK: String;
begin
  if CurStep = ssPostInstall then
  begin
    Dir := ExpandConstant('{userappdata}\DiscordPanic');
    ForceDirectories(Dir);
    HK := Lowercase(Trim(HotkeyPage.Values[0]));
    StringChangeEx(HK, '\', '\\', True);
    StringChangeEx(HK, '"', '\"', True);
    Json :=
      '{' + #13#10 +
      '  "hotkey": "' + HK + '",' + #13#10 +
      '  "toggle_restore": ' + JsonBool(TogglePage.SelectedValueIndex = 0) + ',' + #13#10 +
      '  "swallow_trigger_key": true,' + #13#10 +
      '  "process_names": ["discord.exe", "discordptb.exe", "discordcanary.exe"]' + #13#10 +
      '}' + #13#10;
    SaveStringToFile(Dir + '\config.json', Json, False);
  end;
end;

function InitializeUninstall: Boolean;
begin
  StopRunning;
  Result := True;
end;
