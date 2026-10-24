#define MyAppName "Nika CRM"
#define VersionFileHandle FileOpen(AddBackslash(SourcePath) + "..\..\VERSION")
#define MyAppVersion Trim(FileRead(VersionFileHandle))
#expr FileClose(VersionFileHandle)
#define MyAppVersionDate "2026-10-24"
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
AppComments=Free CRM for service centers. Use only; copying and modification are not allowed. Build {#MyAppVersionDate}.
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
WizardStyle=classic
SetupLogging=yes
; Russian is the product language: never ask, even on an English Windows.
LanguageDetectionMethod=none
ShowLanguageDialog=no
InfoBeforeFile=installer-license.ru.txt
WizardImageFile=wizard-large.bmp
WizardSmallImageFile=wizard-small.png
SetupIconFile=nika-service.ico
UninstallDisplayName=Nika CRM
UninstallDisplayIcon={app}\nika-service.ico
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

[InstallDelete]
; Older builds put every shortcut on the desktop; 1.0.11 keeps them in the
; Start menu only, so an in-place upgrade must clean the old icons up.
Type: files; Name: "{commondesktop}\Nika CRM*.url"
Type: files; Name: "{commondesktop}\Nika CRM*.lnk"
Type: files; Name: "{commondesktop}\Ника Сервис*.url"

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
Source: "nika-service.ico"; DestDir: "{app}"; Flags: ignoreversion

Source: "assets\python-3.12.10-embed-amd64.zip"; DestDir: "{tmp}\NikaCRM-offline"; Flags: deleteafterinstall
Source: "assets\postgresql-installer.exe"; DestDir: "{tmp}\NikaCRM-offline"; Flags: deleteafterinstall
Source: "assets\nssm.exe"; DestDir: "{tmp}\NikaCRM-offline"; Flags: deleteafterinstall
Source: "assets\wheelhouse\*"; DestDir: "{tmp}\NikaCRM-offline\wheelhouse"; Flags: deleteafterinstall recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Nika CRM — Открыть"; Filename: "http://127.0.0.1:5000"
Name: "{group}\Nika CRM — Перезапустить сервис"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\restart-service.ps1"""; WorkingDir: "{app}\app"
Name: "{group}\Nika CRM — Доступ по сети (LAN)"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\enable-lan-access.ps1"""; WorkingDir: "{app}\app"; Comment: "Включить/починить доступ к CRM из локальной сети"
Name: "{group}\Nika CRM — Пароль базы данных"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\show-db-credentials.ps1"""; WorkingDir: "{app}\app"; Comment: "Показать пароли PostgreSQL для pgAdmin (нужны права администратора)"
Name: "{group}\Nika CRM — Резервная копия базы"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\backup-database.ps1"""; WorkingDir: "{app}\app"; Comment: "Сохранить базу в %ProgramData%\NikaCRM-backup и показать путь к архиву (нужны права администратора)"
Name: "{group}\Nika CRM — Журналы"; Filename: "{sys}\explorer.exe"; Parameters: """{commonappdata}\NikaCRM\logs"""
Name: "{group}\Nika CRM — Руководство пользователя"; Filename: "{#MyGuideURL}"
Name: "{group}\Nika CRM — Онлайн-демо"; Filename: "{#MyDemoURL}"
Name: "{group}\Ника Сервис — Сайт"; Filename: "https://nika-sc.ru/"; Comment: "Сайт сервисного центра «Ника»"
Name: "{group}\Nika CRM — Удалить"; Filename: "{uninstallexe}"; Comment: "Удалить Nika CRM: службы, файлы и (по вопросу) база с настройками"

; Desktop: exactly three icons. Created natively by Setup (not by a script),
; so they exist even if PowerShell is locked down on the target machine.
Name: "{commondesktop}\Nika CRM — Открыть"; Filename: "http://127.0.0.1:5000"; IconFilename: "{app}\nika-service.ico"
Name: "{commondesktop}\Nika CRM — Перезапустить сервис"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\restart-service.ps1"""; WorkingDir: "{app}\app"; IconFilename: "{app}\nika-service.ico"; Comment: "Перезапустить сервис Nika CRM"
Name: "{commondesktop}\Ника Сервис — Сайт"; Filename: "https://nika-sc.ru/"; IconFilename: "{app}\nika-service.ico"; Comment: "Сайт сервисного центра «Ника»"

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

var
  ProductPage: TWizardPage;
  ProductImage: TBitmapImage;
  InstallingLogo: TBitmapImage;
  LegalConfirmationPage: TInputOptionWizardPage;
  DocumentationPage: TWizardPage;
  KeepDataDir: Boolean;
  UserWantsDataRemoved: Boolean;

{ WizardImageFile is drawn only on Welcome/Finished since Inno 6.6, so the
  progress page needs its own logo. The banner goes under every visible control
  (progress bar, status and path labels) using their real rectangles; the
  computed geometry is logged next to setup.log for support. }
procedure LayoutInstallingLogo;
var
  Page: TNewNotebookPage;
  GaugeTop, OccupiedBottom, Free, LabelTop, LogoHeight: Integer;
  Details: String;
begin
  if InstallingLogo = nil then
    Exit;
  Page := WizardForm.InstallingPage;
  GaugeTop := WizardForm.ProgressGauge.Top;
  OccupiedBottom := GaugeTop + WizardForm.ProgressGauge.Height;
  Free := Page.Height - OccupiedBottom - ScaleY(8);

  LabelTop := WizardForm.StatusLabel.Top;
  if WizardForm.FilenameLabel.Top < LabelTop then
    LabelTop := WizardForm.FilenameLabel.Top;

  InstallingLogo.Visible := False;
  if Free >= ScaleY(48) then
  begin
    LogoHeight := (Page.Width * 170) div 640;
    if LogoHeight > Free then
      LogoHeight := Free;
    InstallingLogo.Height := LogoHeight;
    InstallingLogo.Width := (LogoHeight * 640) div 170;
    InstallingLogo.Left := (Page.Width - InstallingLogo.Width) div 2;
    InstallingLogo.Top := OccupiedBottom + ScaleY(4);
    InstallingLogo.Visible := True;
  end
  else if (GaugeTop - LabelTop) >= ScaleY(48) then
  begin
    LogoHeight := (Page.Width * 170) div 640;
    if LogoHeight > (GaugeTop - LabelTop - ScaleY(8)) then
      LogoHeight := GaugeTop - LabelTop - ScaleY(8);
    InstallingLogo.Height := LogoHeight;
    InstallingLogo.Width := (LogoHeight * 640) div 170;
    InstallingLogo.Left := (Page.Width - InstallingLogo.Width) div 2;
    InstallingLogo.Top := GaugeTop - LogoHeight - ScaleY(4);
    InstallingLogo.Visible := True;
  end;

  Details :=
    'page=' + IntToStr(Page.Width) + 'x' + IntToStr(Page.Height) + #13#10 +
    'gauge=' + IntToStr(GaugeTop) + '+' + IntToStr(WizardForm.ProgressGauge.Height) + #13#10 +
    'status=' + IntToStr(WizardForm.StatusLabel.Top) + '+' + IntToStr(WizardForm.StatusLabel.Height) +
    ' visible=' + IntToStr(Ord(WizardForm.StatusLabel.Visible)) + #13#10 +
    'filename=' + IntToStr(WizardForm.FilenameLabel.Top) + '+' + IntToStr(WizardForm.FilenameLabel.Height) +
    ' visible=' + IntToStr(Ord(WizardForm.FilenameLabel.Visible)) + #13#10 +
    'occupiedBottom=' + IntToStr(OccupiedBottom) + ' free=' + IntToStr(Free) + #13#10 +
    'logo=' + IntToStr(InstallingLogo.Left) + ',' + IntToStr(InstallingLogo.Top) +
    ' ' + IntToStr(InstallingLogo.Width) + 'x' + IntToStr(InstallingLogo.Height) +
    ' visible=' + IntToStr(Ord(InstallingLogo.Visible));
  ForceDirectories(ExpandConstant('{win}\Temp\NikaCRM-setup'));
  SaveStringToFile(ExpandConstant('{win}\Temp\NikaCRM-setup\ui-layout.txt'), Details, False);
end;

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

  InstallingLogo := TBitmapImage.Create(WizardForm.InstallingPage);
  InstallingLogo.Parent := WizardForm.InstallingPage;
  InstallingLogo.Left := 0;
  InstallingLogo.Top := 0;
  InstallingLogo.AutoSize := False;
  InstallingLogo.Stretch := True;
  InstallingLogo.Visible := False;
  InstallingLogo.Bitmap.LoadFromFile(ExpandConstant('{tmp}\installer-hero.bmp'));

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

function ReadTextTail(const Path: String; MaxLen: Integer): String;
var
  Content: AnsiString;
  S: String;
begin
  Result := '';
  if not LoadStringFromFile(Path, Content) then
    Exit;
  S := Trim(String(Content));
  if (MaxLen > 0) and (Length(S) > MaxLen) then
    S := Copy(S, Length(S) - MaxLen + 1, MaxLen);
  Result := S;
end;

function ReadSetupErrorHint: String;
var
  Dir, Extra: String;
begin
  Dir := ExpandConstant('{win}\Temp\NikaCRM-setup');
  Result := ReadTextTail(Dir + '\setup-error.txt', 1200);
  if Result <> '' then
    Exit;
  Result := ReadTextTail(Dir + '\console.txt', 1200);
  Extra := ReadTextTail(Dir + '\cmd-start.txt', 400);
  if Extra <> '' then
  begin
    if Result <> '' then
      Result := Result + #13#10;
    Result := Result + Extra;
  end;
  if Result <> '' then
    Exit;
  if not FileExists(Dir + '\setup.log') then
    Result := 'Скрипт настройки не записал setup.log. Пришлите console.txt и cmd-start.txt из папки журнала.';
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
    'Пришлите setup-error.txt, setup.log и console.txt из этой папки.'
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

procedure WriteBootstrapLauncher(const ProgressDir, PowerShell, Bootstrap: String);
var
  Cmd: String;
begin
  { ASCII, CRLF. cmd stays alive for the whole script and keeps its stdout. }
  Cmd :=
    '@echo off' + #13#10 +
    '(echo cmd-start %DATE% %TIME%)>"' + ProgressDir + '\cmd-start.txt"' + #13#10 +
    '"' + PowerShell + '" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + Bootstrap + '"' +
    ' -AppDir "' + ExpandConstant('{app}') + '"' +
    ' -DataDir "' + ExpandConstant('{commonappdata}\NikaCRM') + '"' +
    ' -AssetsDir "' + ExpandConstant('{tmp}\NikaCRM-offline') + '"' +
    ' -ProgressDir "' + ProgressDir + '"' +
    ' >"' + ProgressDir + '\console.txt" 2>&1' + #13#10 +
    'set EC=%ERRORLEVEL%' + #13#10 +
    '(echo EXIT=%EC%)>>"' + ProgressDir + '\cmd-start.txt"' + #13#10 +
    'if exist "' + ProgressDir + '\setup-error.txt" type "' + ProgressDir + '\setup-error.txt" >>"' + ProgressDir + '\console.txt"' + #13#10 +
    'if exist "' + ProgressDir + '\setup.log" type "' + ProgressDir + '\setup.log" >>"' + ProgressDir + '\console.txt"' + #13#10 +
    'exit /b %EC%' + #13#10;
  SaveStringToFile(ProgressDir + '\launch-bootstrap.cmd', Cmd, False);
end;

procedure RunBootstrapWithProgress;
var
  ResultCode: Integer;
  PowerShell, Bootstrap, Params, ProgressDir: String;
  Pid, Elapsed: Integer;
begin
  { cmd.exe in Windows Sandbox exits with code 1 while PowerShell is still
    running. Waiting on that PID aborts the wizard and rolls the files back,
    so the site opens and then disappears. The script's setup-progress.done
    file is the only completion signal. }
  ProgressDir := ExpandConstant('{win}\Temp\NikaCRM-setup');
  ForceDirectories(ProgressDir);
  DeleteFile(ProgressDir + '\setup-progress.pid');
  DeleteFile(ProgressDir + '\setup-progress.done');
  DeleteFile(ProgressDir + '\setup-progress.txt');
  DeleteFile(ProgressDir + '\setup-error.txt');
  DeleteFile(ProgressDir + '\setup.log');
  DeleteFile(ProgressDir + '\console.txt');
  DeleteFile(ProgressDir + '\cmd-start.txt');
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

  WriteBootstrapLauncher(ProgressDir, PowerShell, Bootstrap);
  Params := '/d /c "' + ProgressDir + '\launch-bootstrap.cmd"';
  SaveStringToFile(
    ProgressDir + '\installer-launch.log',
    ExpandConstant('{cmd}') + #13#10 + Params + #13#10 +
    'PowerShell=' + PowerShell + #13#10 +
    'Bootstrap=' + Bootstrap + #13#10 +
    'Wait=setup-progress.done' + #13#10,
    False);
  if not Exec(ExpandConstant('{cmd}'), Params, ProgressDir, SW_HIDE, ewNoWait, ResultCode) then
    FailBootstrap('Не удалось запустить автоматическую настройку Nika CRM.');

  Pid := ResultCode;
  Elapsed := 0;
  while not FileExists(ProgressDir + '\setup-progress.done') do
  begin
    AppProcessMessage;
    UpdateBootstrapProgressFromFile(ProgressDir);
    WizardForm.Refresh;
    Sleep(200);
    Inc(Elapsed);
    if (Elapsed > 300) and (not FileExists(ProgressDir + '\setup-progress.pid')) then
      FailBootstrap('Скрипт настройки не стартовал.');
    if Elapsed > 6000 then
      FailBootstrap('Настройка не отвечает больше 20 минут.');
  end;
  ResultCode := StrToIntDef(Trim(ReadFirstLine(ProgressDir + '\setup-progress.done')), 1);

  SaveStringToFile(
    ProgressDir + '\installer-launch.log',
    ExpandConstant('{cmd}') + #13#10 + Params + #13#10 +
    'PowerShell=' + PowerShell + #13#10 +
    'Bootstrap=' + Bootstrap + #13#10 +
    'Wait=setup-progress.done' + #13#10 +
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
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpInstalling then
    LayoutInstallingLogo;
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
  UserWantsDataRemoved := True;
  if UninstallSilent then
    Exit;

  Result := MsgBox(
    'Удаление Nika CRM: службы, программа и регистрация её собственного Python и PostgreSQL.' + #13#10 +
    'Отдельно установленные Python и PostgreSQL на этом компьютере не удаляются.' + #13#10#13#10 +
    'Перед удалением база будет сохранена в резервную копию:' + #13#10 +
    ExpandConstant('{commonappdata}\NikaCRM-backup') + #13#10#13#10 +
    'Эта папка при удалении не стирается.' + #13#10#13#10 +
    'Продолжить удаление?',
    mbConfirmation,
    MB_YESNO
  ) = IDYES;
  if not Result then
    Exit;

  UserWantsDataRemoved := MsgBox(
    'Удалить базу данных и настройки Nika CRM?' + #13#10#13#10 +
    'Да — удалить данные. Копия останется в:' + #13#10 +
    ExpandConstant('{commonappdata}\NikaCRM-backup') + #13#10#13#10 +
    'Нет — оставить данные в:' + #13#10 +
    ExpandConstant('{commonappdata}\NikaCRM') + #13#10 +
    'Повторная установка подхватит их.',
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

  if not UserWantsDataRemoved then
  begin
    if (not UninstallSilent) and DirExists(DataDir) then
      MsgBox(
        'База данных и настройки оставлены:' + #13#10 + DataDir + #13#10#13#10 +
        'Резервная копия:' + #13#10 + BackupDir,
        mbInformation,
        MB_OK
      );
    Exit;
  end;

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
