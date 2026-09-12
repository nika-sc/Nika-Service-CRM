#define MyAppName "Nika CRM"
#define VersionFileHandle FileOpen(AddBackslash(SourcePath) + "..\..\VERSION")
#define MyAppVersion Trim(FileRead(VersionFileHandle))
#expr FileClose(VersionFileHandle)
#define MyAppVersionDate "2026-09-11"
#define MyAppPublisher "Alexander Smelkov, Service Center Nika"
#define MyAppURL "https://github.com/nika-sc/Nika-Service-CRM"
#define MyAppEmail "smelkov2008@yandex.ru"
#define MyDemoURL "https://service.nika-crm.ru/"
#define MyGuideURL "https://github.com/nika-sc/Nika-Service-CRM/blob/main/docs/USER_GUIDE.md"
#define SourceRoot "..\.."

[Setup]
AppId={{D606AA35-BA7B-46F0-96E4-72EB1CCCE693}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion} ({#MyAppVersionDate})
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/nika-sc/Nika-Service-CRM/issues
AppUpdatesURL={#MyAppURL}
AppContact={#MyAppEmail}
AppComments=Free open-source CRM for service centers. MIT License. Build {#MyAppVersionDate}.
DefaultDirName={autopf}\NikaCRM
DefaultGroupName=Nika CRM
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=NikaCRM-Offline-Setup-{#MyAppVersion}-x64
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
SetupLogging=yes
InfoBeforeFile=installer-license.ru.txt
WizardImageFile=wizard-large.bmp
WizardSmallImageFile=wizard-small.bmp
UninstallDisplayName=Nika CRM
Uninstallable=yes
CloseApplications=yes
RestartApplications=no
MinVersion=10.0.17763
DiskSpanning=no
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany=Service Center Nika
VersionInfoDescription=Nika CRM Offline Installer for Windows ({#MyAppVersionDate})
VersionInfoCopyright=Copyright (c) 2026 Alexander Smelkov
VersionInfoProductName=Nika CRM
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
russian.InstallingLabel=Копирование файлов Nika CRM…%nДальше пойдёт настройка Python и базы — обычно 5–10 минут. Не нажимайте «Отмена» и не закрывайте окно: установка не зависла.
english.InstallingLabel=Copying Nika CRM files…%nPython and the database are set up next (usually 5–10 minutes). Do not click Cancel or close this window.

[Dirs]
Name: "{commonappdata}\NikaCRM"; Permissions: admins-full system-full
Name: "{commonappdata}\NikaCRM\logs"; Permissions: admins-full system-full

[Files]
Source: "{#SourceRoot}\app\*"; DestDir: "{app}\app\app"; Excludes: "database\service_center.db,database\*.db,database\*.db-*,database\*.sqlite,database\*.sqlite3,*\__pycache__\*,*\*.pyc"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\database\bootstrap\nikacrm_public_sanitized.sql"; DestDir: "{app}\app\database\bootstrap"; Flags: ignoreversion
Source: "{#SourceRoot}\database\bootstrap\README.md"; DestDir: "{app}\app\database\bootstrap"; Flags: ignoreversion
Source: "{#SourceRoot}\docs\*"; DestDir: "{app}\app\docs"; Excludes: "private,private\*,*\private\*,SERVICE_NIKA_CRM_HOST.md"; Flags: ignoreversion recursesubdirs
Source: "{#SourceRoot}\static\*"; DestDir: "{app}\app\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\templates\*"; DestDir: "{app}\app\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\scripts\run_migrations.py"; DestDir: "{app}\app\scripts"; Flags: ignoreversion
Source: "{#SourceRoot}\scripts\Grant-LocalPostgresAppPrivileges.ps1"; DestDir: "{app}\app\scripts"; Flags: ignoreversion
Source: "{#SourceRoot}\packaging\windows\*.ps1"; DestDir: "{app}\app\packaging\windows"; Flags: ignoreversion
Source: "{#SourceRoot}\packaging\windows\requirements-windows.txt"; DestDir: "{app}\app\packaging\windows"; Flags: ignoreversion
Source: "{#SourceRoot}\packaging\windows\service_entry.py"; DestDir: "{app}\app"; DestName: "nikacrm_service.py"; Flags: ignoreversion
Source: "{#SourceRoot}\VERSION"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "{#SourceRoot}\run.py"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "{#SourceRoot}\wsgi.py"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "{#SourceRoot}\requirements.txt"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "{#SourceRoot}\README.md"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "{#SourceRoot}\LICENSE"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "{#SourceRoot}\oh-oh-icq-sound.mp3"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "installer-hero.bmp"; Flags: dontcopy

Source: "assets\python-installer.exe"; DestDir: "{tmp}\NikaCRM-offline"; Flags: deleteafterinstall
Source: "assets\postgresql-installer.exe"; DestDir: "{tmp}\NikaCRM-offline"; Flags: deleteafterinstall
Source: "assets\nssm.exe"; DestDir: "{tmp}\NikaCRM-offline"; Flags: deleteafterinstall
Source: "assets\wheelhouse\*"; DestDir: "{tmp}\NikaCRM-offline\wheelhouse"; Flags: deleteafterinstall recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Nika CRM — Открыть"; Filename: "http://127.0.0.1:5000"
Name: "{group}\Nika CRM — Перезапустить сервис"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\restart-service.ps1"""; WorkingDir: "{app}\app"
Name: "{group}\Nika CRM — Доступ по сети (LAN)"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\enable-lan-access.ps1"""; WorkingDir: "{app}\app"; Comment: "Включить/починить доступ к CRM из локальной сети"
Name: "{group}\Nika CRM — Пароль базы данных"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\show-db-credentials.ps1"""; WorkingDir: "{app}\app"; Comment: "Показать пароли PostgreSQL для pgAdmin (нужны права администратора)"
Name: "{group}\Nika CRM — Резервная копия базы"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\backup-database.ps1"""; WorkingDir: "{app}\app"; Comment: "Сохранить базу в %ProgramData%\NikaCRM-backup (нужны права администратора)"
Name: "{group}\Nika CRM — Журналы"; Filename: "{sys}\explorer.exe"; Parameters: """{commonappdata}\NikaCRM\logs"""
Name: "{group}\Nika CRM — Руководство пользователя"; Filename: "{#MyGuideURL}"
Name: "{group}\Nika CRM — Онлайн-демо"; Filename: "{#MyDemoURL}"
Name: "{group}\Nika CRM — Удалить"; Filename: "{uninstallexe}"; Comment: "Удалить Nika CRM: службы, файлы и (по вопросу) база с настройками"

[Run]
Filename: "http://127.0.0.1:5000"; Description: "Открыть Nika CRM"; Flags: shellexec postinstall skipifsilent nowait
Filename: "{#MyGuideURL}"; Description: "Открыть руководство пользователя"; Flags: shellexec postinstall skipifsilent nowait

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\uninstall-cleanup.ps1"" -AppDir ""{app}"""; Flags: runhidden waituntilterminated; RunOnceId: "NikaCRMCleanup"

[UninstallDelete]
Type: files; Name: "{commondesktop}\Nika CRM*"

[Code]
type
  TMsg = record
    hwnd: HWND;
    message: UINT;
    wParam: Longint;
    lParam: Longint;
    time: DWORD;
    pt: TPoint;
  end;

function PeekMessage(var lpMsg: TMsg; hWnd: HWND; wMsgFilterMin, wMsgFilterMax, wRemoveMsg: UINT): BOOL;
  external 'PeekMessageW@user32.dll stdcall';
function TranslateMessage(const lpMsg: TMsg): BOOL;
  external 'TranslateMessage@user32.dll stdcall';
function DispatchMessage(const lpMsg: TMsg): Longint;
  external 'DispatchMessageW@user32.dll stdcall';
function OpenProcess(dwDesiredAccess: Cardinal; bInheritHandle: BOOL; dwProcessId: Cardinal): THandle;
  external 'OpenProcess@kernel32.dll stdcall';
function CloseHandle(hObject: THandle): BOOL;
  external 'CloseHandle@kernel32.dll stdcall';
function GetExitCodeProcess(hProcess: THandle; var lpExitCode: Cardinal): BOOL;
  external 'GetExitCodeProcess@kernel32.dll stdcall';
function WaitForSingleObject(hHandle: THandle; dwMilliseconds: DWORD): DWORD;
  external 'WaitForSingleObject@kernel32.dll stdcall';

var
  ProductPage: TWizardPage;
  ProductImage: TBitmapImage;
  LegalConfirmationPage: TInputOptionWizardPage;
  DocumentationPage: TWizardPage;
  KeepDataDir: Boolean;

procedure OpenInstallerLink(Sender: TObject);
var
  ErrorCode: Integer;
  Link: TNewStaticText;
begin
  Link := TNewStaticText(Sender);
  ShellExec('open', Link.Hint, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

function AddInstallerLink(
  Page: TWizardPage;
  Caption: String;
  URL: String;
  ALeft: Integer;
  ATop: Integer;
  AWidth: Integer
): TNewStaticText;
begin
  Result := TNewStaticText.Create(Page);
  Result.Parent := Page.Surface;
  Result.Caption := Caption;
  Result.Hint := URL;
  Result.ShowHint := True;
  Result.Left := ALeft;
  Result.Top := ATop;
  Result.Width := AWidth;
  Result.Height := ScaleY(18);
  Result.AutoSize := False;
  Result.Font.Color := clBlue;
  Result.Font.Style := [fsUnderline];
  Result.Cursor := crHand;
  Result.OnClick := @OpenInstallerLink;
end;

procedure InitializeWizard;
var
  FeatureText: TNewStaticText;
  DemoAccessText: TNewStaticText;
  DocsIntro: TNewStaticText;
  ColumnWidth: Integer;
begin
  WizardForm.WelcomeLabel1.Caption := 'Nika CRM — бесплатная CRM для сервисных центров';
  WizardForm.WelcomeLabel2.Caption :=
    'Открытая CRM для заявок, клиентов, устройств, склада и финансов.' + #13#10 + #13#10 +
    'Установщик автоматически развернёт Python 3.12, PostgreSQL 18, демонстрационную базу и службы автозапуска.' + #13#10 + #13#10 +
    'Автор: Александр Смелков, сервисный центр «Ника», Сочи.' + #13#10 +
    'Проект: https://github.com/nika-sc/Nika-Service-CRM' + #13#10 +
    'Демо: https://service.nika-crm.ru/' + #13#10 +
    'Email: smelkov2008@yandex.ru';

  ExtractTemporaryFile('installer-hero.bmp');
  ProductPage := CreateCustomPage(
    wpWelcome,
    'Возможности Nika CRM',
    'Всё необходимое сервисному центру в одной системе'
  );
  ProductImage := TBitmapImage.Create(ProductPage);
  ProductImage.Parent := ProductPage.Surface;
  ProductImage.Left := 0;
  ProductImage.Top := 0;
  ProductImage.Width := ProductPage.SurfaceWidth;
  ProductImage.Height := ScaleY(112);
  ProductImage.AutoSize := False;
  ProductImage.Stretch := True;
  ProductImage.Bitmap.LoadFromFile(ExpandConstant('{tmp}\installer-hero.bmp'));

  FeatureText := TNewStaticText.Create(ProductPage);
  FeatureText.Parent := ProductPage.Surface;
  FeatureText.Left := 0;
  FeatureText.Top := ScaleY(120);
  FeatureText.Width := ProductPage.SurfaceWidth;
  FeatureText.Height := ScaleY(58);
  FeatureText.AutoSize := False;
  FeatureText.Caption :=
    '✓ Заявки, клиенты и история устройств     ✓ Склад, закупки и продажи' + #13#10 +
    '✓ Финансы, зарплата и аналитика           ✓ Клиентский портал и уведомления' + #13#10 +
    '✓ PostgreSQL, локальная работа и открытый исходный код';

  DemoAccessText := TNewStaticText.Create(ProductPage);
  DemoAccessText.Parent := ProductPage.Surface;
  DemoAccessText.Left := 0;
  DemoAccessText.Top := ScaleY(176);
  DemoAccessText.Width := ProductPage.SurfaceWidth;
  DemoAccessText.Height := ScaleY(20);
  DemoAccessText.AutoSize := False;
  DemoAccessText.Font.Style := [fsBold];
  DemoAccessText.Caption :=
    'Демо: admin, manager, master, viewer — пароль для всех 111111';

  AddInstallerLink(ProductPage, 'Онлайн-демо', '{#MyDemoURL}', 0, ScaleY(202), ScaleX(100));
  AddInstallerLink(ProductPage, 'Сайт Ника-Сервис', 'https://nika-sc.ru/', ScaleX(110), ScaleY(202), ScaleX(130));
  AddInstallerLink(ProductPage, 'Проект на GitHub', '{#MyAppURL}', ScaleX(250), ScaleY(202), ScaleX(135));
  AddInstallerLink(ProductPage, 'Email разработчика', 'mailto:{#MyAppEmail}', 0, ScaleY(226), ScaleX(130));
  AddInstallerLink(ProductPage, 'Telegram-канал', 'https://t.me/nikaserviceadler', ScaleX(145), ScaleY(226), ScaleX(125));
  AddInstallerLink(ProductPage, 'Руководство', '{#MyGuideURL}', ScaleX(285), ScaleY(226), ScaleX(105));

  LegalConfirmationPage := CreateInputOptionPage(
    wpInfoBefore,
    'Подтверждение условий',
    'Перед установкой подтвердите оба условия',
    'Отметьте оба пункта, чтобы продолжить установку Nika CRM.',
    False,
    False
  );
  LegalConfirmationPage.Add(
    'Я прочитал(а) и принимаю условия свободной лицензии MIT.'
  );
  LegalConfirmationPage.Add(
    'Я принимаю отказ от гарантий и ответственности и самостоятельно отвечаю за резервное копирование и сохранность данных.'
  );
  LegalConfirmationPage.Values[0] := False;
  LegalConfirmationPage.Values[1] := False;
  if WizardSilent then
  begin
    LegalConfirmationPage.Values[0] := True;
    LegalConfirmationPage.Values[1] := True;
  end;

  DocumentationPage := CreateCustomPage(
    LegalConfirmationPage.ID,
    'Документация Nika CRM',
    'Полезные ссылки откроются в браузере'
  );
  DocsIntro := TNewStaticText.Create(DocumentationPage);
  DocsIntro.Parent := DocumentationPage.Surface;
  DocsIntro.Left := 0;
  DocsIntro.Top := 0;
  DocsIntro.Width := DocumentationPage.SurfaceWidth;
  DocsIntro.Height := ScaleY(32);
  DocsIntro.AutoSize := False;
  DocsIntro.Caption := 'Документация проекта и описание основных модулей:';

  ColumnWidth := (DocumentationPage.SurfaceWidth div 2) - ScaleX(8);
  AddInstallerLink(DocumentationPage, 'Руководство пользователя', '{#MyGuideURL}', 0, ScaleY(38), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'API документация', '{#MyAppURL}/blob/main/docs/API.md', 0, ScaleY(62), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Обзор системы', '{#MyAppURL}/blob/main/docs/SYSTEM_OVERVIEW.md', 0, ScaleY(86), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Политика данных OSS', '{#MyAppURL}/blob/main/docs/OSS_DATA_POLICY.md', 0, ScaleY(110), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Workflow OSS-релизов', '{#MyAppURL}/blob/main/docs/OSS_RELEASE_WORKFLOW.md', 0, ScaleY(134), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Деплой', '{#MyAppURL}/blob/main/docs/DEPLOY.md', 0, ScaleY(158), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Сервисы', '{#MyAppURL}/blob/main/app/services/README.md', 0, ScaleY(182), ColumnWidth);

  AddInstallerLink(DocumentationPage, 'Модели', '{#MyAppURL}/blob/main/app/models/README.md', ColumnWidth + ScaleX(16), ScaleY(38), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Query-классы', '{#MyAppURL}/blob/main/app/database/queries/README.md', ColumnWidth + ScaleX(16), ScaleY(62), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Маршруты', '{#MyAppURL}/blob/main/app/routes/README.md', ColumnWidth + ScaleX(16), ScaleY(86), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Утилиты', '{#MyAppURL}/blob/main/app/utils/README.md', ColumnWidth + ScaleX(16), ScaleY(110), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Middleware', '{#MyAppURL}/blob/main/app/middleware/README.md', ColumnWidth + ScaleX(16), ScaleY(134), ColumnWidth);
  AddInstallerLink(DocumentationPage, 'Шаблоны', '{#MyAppURL}/blob/main/templates/README.md', ColumnWidth + ScaleX(16), ScaleY(158), ColumnWidth);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = LegalConfirmationPage.ID) and
     ((not LegalConfirmationPage.Values[0]) or
      (not LegalConfirmationPage.Values[1])) then
  begin
    if WizardSilent then
    begin
      LegalConfirmationPage.Values[0] := True;
      LegalConfirmationPage.Values[1] := True;
    end
    else
    begin
      MsgBox(
        'Для продолжения отметьте оба пункта.',
        mbInformation,
        MB_OK
      );
      Result := False;
    end;
  end;
end;

procedure StopNikaService(const ServiceName: String);
var
  ResultCode: Integer;
begin
  // net stop waits until the service really stops; sc stop returns immediately.
  // A live service keeps files and the database busy during an upgrade.
  Exec(ExpandConstant('{sys}\net.exe'), 'stop ' + ServiceName + ' /y', '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
end;

function ReadFirstLine(const Path: String): String;
var
  Content: AnsiString;
  S: String;
  P: Integer;
begin
  Result := '';
  if not LoadStringFromFile(Path, Content) then
    Exit;
  S := Trim(String(Content));
  StringChangeEx(S, #13#10, #10, True);
  StringChangeEx(S, #13, #10, True);
  P := Pos(#10, S);
  if P > 0 then
    S := Copy(S, 1, P - 1);
  Result := Trim(S);
end;

function SanitizeFolderToken(const Value: String): String;
var
  I: Integer;
  Ch: Char;
begin
  Result := '';
  for I := 1 to Length(Value) do
  begin
    Ch := Value[I];
    if ((Ch >= '0') and (Ch <= '9')) or (Ch = '.') or ((Ch >= 'a') and (Ch <= 'z')) or ((Ch >= 'A') and (Ch <= 'Z')) then
      Result := Result + Ch;
  end;
  if Result = '' then
    Result := 'previous';
end;

procedure SnapshotAppForRollback;
var
  Src, Dest, RollbackRoot, InstalledVer, Params: String;
  ResultCode: Integer;
begin
  Src := ExpandConstant('{app}\app');
  if not DirExists(Src) then
    Exit;

  RollbackRoot := ExpandConstant('{commonappdata}\NikaCRM\rollback');
  ForceDirectories(RollbackRoot);
  InstalledVer := SanitizeFolderToken(ReadFirstLine(ExpandConstant('{app}\app\VERSION')));
  Dest := RollbackRoot + '\' + InstalledVer + '-' + GetDateTimeString('yyyymmdd-hhnnss', '-', ':');
  WizardForm.StatusLabel.Caption := 'Сохраняю снимок текущих файлов для отката...';
  WizardForm.Update;
  Exec(
    ExpandConstant('{sys}\robocopy.exe'),
    '"' + Src + '" "' + Dest + '" /E /NFL /NDL /NJH /NJS /NC /NS /NP /XD __pycache__',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // robocopy uses 0–7 as success.
  Params :=
    '-NoLogo -NoProfile -Command "Get-ChildItem -LiteralPath ''' + RollbackRoot +
    ''' -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 2 | Remove-Item -Recurse -Force"';
  Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  NeedsRestart := False;
  WizardForm.StatusLabel.Caption := 'Останавливаю службы Nika CRM перед обновлением...';
  WizardForm.Update;
  StopNikaService('NikaCRM-Web');
  StopNikaService('NikaCRM-PostgreSQL');
  SnapshotAppForRollback;
  Sleep(1000);
end;

procedure PersistSetupLogs;
var
  Src, Dest, InnoLog: String;
  ResultCode: Integer;
begin
  Src := ExpandConstant('{win}\Temp\NikaCRM-setup');
  Dest := ExpandConstant('{commondesktop}\NikaCRM-setup-log');
  ForceDirectories(Src);
  ForceDirectories(Dest);
  Exec(
    ExpandConstant('{sys}\xcopy.exe'),
    '"' + Src + '\*" "' + Dest + '\" /E /I /Y /Q',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  InnoLog := ExpandConstant('{log}');
  if (InnoLog <> '') and FileExists(InnoLog) then
    FileCopy(InnoLog, Dest + '\inno-setup.log', False);
end;

function ReadSetupErrorHint: String;
var
  ErrorFile, LogFile: String;
  Content: AnsiString;
  S: String;
begin
  Result := '';
  ErrorFile := ExpandConstant('{win}\Temp\NikaCRM-setup\setup-error.txt');
  LogFile := ExpandConstant('{win}\Temp\NikaCRM-setup\setup.log');
  if LoadStringFromFile(ErrorFile, Content) then
  begin
    S := Trim(String(Content));
    if Length(S) > 1200 then
      S := Copy(S, Length(S) - 1199, 1200);
    Result := S;
    Exit;
  end;
  if not FileExists(LogFile) then
    Result := 'Файл setup.log не создан — скрипт настройки не стартовал. Нужен setup-error.txt из папки журнала.';
end;

procedure FailBootstrap(const Msg: String);
var
  Hint, Full: String;
begin
  PersistSetupLogs;
  WizardForm.CancelButton.Enabled := True;
  Hint := ReadSetupErrorHint;
  Full := Msg;
  if Hint <> '' then
    Full := Full + #13#10#13#10 + Hint;
  RaiseException(
    Full + #13#10#13#10 +
    'Журнал скопирован на рабочий стол:' + #13#10 +
    ExpandConstant('{commondesktop}\NikaCRM-setup-log') + #13#10 +
    'Также: ' + ExpandConstant('{win}\Temp\NikaCRM-setup') + #13#10 +
    'Пришлите setup-error.txt и setup.log из этой папки.'
  );
end;

procedure AppProcessMessage;
var
  Msg: TMsg;
begin
  while PeekMessage(Msg, 0, 0, 0, 1) do
  begin
    TranslateMessage(Msg);
    DispatchMessage(Msg);
  end;
end;

procedure UpdateBootstrapProgressFromFile(const ProgressDir: String);
var
  Content: AnsiString;
  S, PercentLine, Title, Hint: String;
  P, Percent: Integer;
begin
  if not LoadStringFromFile(ProgressDir + '\setup-progress.txt', Content) then
    Exit;
  S := String(Content);
  StringChangeEx(S, #13#10, #10, True);
  StringChangeEx(S, #13, #10, True);
  P := Pos(#10, S);
  if P = 0 then
    Exit;
  PercentLine := Trim(Copy(S, 1, P - 1));
  Delete(S, 1, P);
  P := Pos(#10, S);
  if P > 0 then
  begin
    Title := Trim(Copy(S, 1, P - 1));
    Hint := Trim(Copy(S, P + 1, Length(S)));
  end
  else
    Title := Trim(S);
  Percent := StrToIntDef(PercentLine, -1);
  if (Percent >= 0) and (Percent <= 100) then
    WizardForm.ProgressGauge.Position := Percent;
  if Title <> '' then
    WizardForm.StatusLabel.Caption := PercentLine + '%  ' + Title;
  if Hint <> '' then
    WizardForm.FilenameLabel.Caption := Hint;
end;

procedure RunBootstrapWithProgress;
var
  ResultCode: Integer;
  PowerShell, Bootstrap, Params, ProgressDir, PidFile: String;
  Pid, Elapsed: Integer;
  ProcessHandle: THandle;
  ExitCode: Cardinal;
begin
  // ewWaitUntilTerminated freezes the wizard (cannot drag/minimize) and hides
  // live progress. Start PowerShell without waiting, then wait on its PID
  // with a message pump. Fail fast if the PID file never appears.
  ProgressDir := ExpandConstant('{win}\Temp\NikaCRM-setup');
  PidFile := ProgressDir + '\setup-progress.pid';
  ForceDirectories(ProgressDir);
  DeleteFile(PidFile);
  DeleteFile(ProgressDir + '\setup-progress.done');
  SaveStringToFile(ProgressDir + '\installer-launch.log', 'preparing' + #13#10, False);

  WizardForm.ProgressGauge.Min := 0;
  WizardForm.ProgressGauge.Max := 100;
  WizardForm.ProgressGauge.Position := 5;
  WizardForm.StatusLabel.Caption := 'Настройка Python, PostgreSQL, базы данных и службы Nika CRM...';
  WizardForm.FilenameLabel.Caption :=
    'Файлы уже скопированы. Этот шаг обычно занимает 5–10 минут. Не закрывайте окно.';
  WizardForm.CancelButton.Enabled := False;
  WizardForm.BackButton.Enabled := False;
  WizardForm.Update;

  PowerShell := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Bootstrap := ExpandConstant('{app}\app\packaging\windows\bootstrap.ps1');
  if not FileExists(PowerShell) then
    FailBootstrap('Не найден PowerShell: ' + PowerShell);
  if not FileExists(Bootstrap) then
    FailBootstrap('Не найден скрипт настройки: ' + Bootstrap);

  Params :=
    '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + Bootstrap + '"' +
    ' -AppDir "' + ExpandConstant('{app}') + '"' +
    ' -DataDir "' + ExpandConstant('{commonappdata}\NikaCRM') + '"' +
    ' -AssetsDir "' + ExpandConstant('{tmp}\NikaCRM-offline') + '"' +
    ' -ProgressDir "' + ProgressDir + '"';
  SaveStringToFile(
    ProgressDir + '\installer-launch.log',
    PowerShell + #13#10 + Params + #13#10 +
    'BootstrapExists=' + Bootstrap + #13#10 +
    'Wait=OpenProcess+PeekMessage' + #13#10,
    False);
  if not Exec(PowerShell, Params, '', SW_HIDE, ewNoWait, ResultCode) then
    FailBootstrap('Не удалось запустить автоматическую настройку Nika CRM.');

  Elapsed := 0;
  while not FileExists(PidFile) do
  begin
    AppProcessMessage;
    WizardForm.Refresh;
    Sleep(200);
    Inc(Elapsed);
    if Elapsed > 150 then
      FailBootstrap('Скрипт настройки не стартовал (нет PID за 30 секунд).');
  end;

  Pid := StrToIntDef(Trim(ReadFirstLine(PidFile)), 0);
  if Pid <= 0 then
    FailBootstrap('Некорректный PID настройки.');
  ProcessHandle := OpenProcess($101000, False, Pid);
  ResultCode := 1;
  if ProcessHandle <> 0 then
  begin
    Elapsed := 0;
    while WaitForSingleObject(ProcessHandle, 200) = 258 do
    begin
      AppProcessMessage;
      UpdateBootstrapProgressFromFile(ProgressDir);
      Inc(Elapsed);
      if Elapsed > 6000 then
      begin
        CloseHandle(ProcessHandle);
        FailBootstrap('Настройка не отвечает больше 20 минут.');
      end;
    end;
    if GetExitCodeProcess(ProcessHandle, ExitCode) then
      ResultCode := Integer(ExitCode);
    CloseHandle(ProcessHandle);
  end
  else if FileExists(ProgressDir + '\setup-progress.done') then
    ResultCode := StrToIntDef(Trim(ReadFirstLine(ProgressDir + '\setup-progress.done')), 1);

  SaveStringToFile(
    ProgressDir + '\installer-launch.log',
    PowerShell + #13#10 + Params + #13#10 +
    'BootstrapExists=' + Bootstrap + #13#10 +
    'Wait=OpenProcess+PeekMessage' + #13#10 +
    'Pid=' + IntToStr(Pid) + #13#10 +
    'ResultCode=' + IntToStr(ResultCode) + #13#10,
    False);

  WizardForm.CancelButton.Enabled := True;
  if ResultCode <> 0 then
    FailBootstrap('Автоматическая настройка завершилась с ошибкой ' + IntToStr(ResultCode) + '.');
  WizardForm.ProgressGauge.Position := 100;
  WizardForm.StatusLabel.Caption := '100%  Установка завершена';
  WizardForm.FilenameLabel.Caption := 'Можно открывать Nika CRM.';
  WizardForm.Update;
  Exec(
    PowerShell,
    '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' +
    ExpandConstant('{app}\app\packaging\windows\create-desktop-icons.ps1') +
    '" -AppDir "' + ExpandConstant('{app}') + '"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunBootstrapWithProgress;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  // Silent/very silent installs cannot interact with the custom legal page.
  if WizardSilent and (PageID = LegalConfirmationPage.ID) then
    Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  KeepDataDir := False;
  if UninstallSilent then
    Exit;

  Result := MsgBox(
    'Удаление Nika CRM выполняется полностью: службы, программа, база данных и настройки.' + #13#10#13#10 +
    'Перед удалением база будет сохранена в резервную копию:' + #13#10 +
    ExpandConstant('{commonappdata}\NikaCRM-backup') + #13#10#13#10 +
    'Эта папка при удалении не стирается, и повторная установка подхватит данные из неё.' + #13#10#13#10 +
    'Продолжить удаление?',
    mbConfirmation,
    MB_YESNO
  ) = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  DataDir: String;
  BackupDir: String;
  Script: String;
begin
  DataDir := ExpandConstant('{commonappdata}\NikaCRM');
  BackupDir := ExpandConstant('{commonappdata}\NikaCRM-backup');

  if CurUninstallStep = usUninstall then
  begin
    // Runs before files are deleted and before uninstall-cleanup.ps1 stops the
    // services, so pg_dump still has a live PostgreSQL to talk to.
    Script := ExpandConstant('{app}\app\packaging\windows\backup-database.ps1');
    if DirExists(DataDir) and FileExists(Script) then
    begin
      if not Exec(
           ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
           '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + Script + '"' +
           ' -AppDir "' + ExpandConstant('{app}') + '"' +
           ' -DataDir "' + DataDir + '"' +
           ' -BackupDir "' + BackupDir + '" -Quiet',
           '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
      begin
        // No backup means no safe wipe: keep the database where it is.
        KeepDataDir := True;
        if not UninstallSilent then
          MsgBox(
            'Не удалось создать резервную копию базы данных.' + #13#10#13#10 +
            'Поэтому база и настройки останутся на диске:' + #13#10 + DataDir + #13#10#13#10 +
            'Программа и службы будут удалены. Папку с данными можно удалить вручную.',
            mbError,
            MB_OK
          );
      end;
    end;
    Exit;
  end;

  if CurUninstallStep <> usPostUninstall then
    Exit;

  if KeepDataDir or (not DirExists(DataDir)) then
    Exit;

  if not DelTree(DataDir, True, True, True) then
    MsgBox(
      'Не удалось удалить каталог полностью:' + #13#10 + DataDir + #13#10#13#10 +
      'Перезагрузите компьютер и удалите папку вручную. Резервная копия базы сохранена в' + #13#10 +
      BackupDir,
      mbInformation,
      MB_OK
    );
end;
