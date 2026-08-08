#define MyAppName "Nika CRM"
#define MyAppVersion "1.0.6"
#define MyAppPublisher "Alexander Smelkov, Service Center Nika"
#define MyAppURL "https://github.com/nika-sc/Nika-Service-CRM"
#define MyAppEmail "smelkov2008@yandex.ru"
#define MyDemoURL "https://demo.nika-sc.ru/"
#define MyGuideURL "https://github.com/nika-sc/Nika-Service-CRM/blob/main/docs/USER_GUIDE.md"
#define SourceRoot "..\.."

[Setup]
AppId={{D606AA35-BA7B-46F0-96E4-72EB1CCCE693}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/nika-sc/Nika-Service-CRM/issues
AppUpdatesURL={#MyAppURL}
AppContact={#MyAppEmail}
AppComments=Free open-source CRM for service centers. MIT License.
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
VersionInfoVersion=1.0.6.0
VersionInfoCompany=Service Center Nika
VersionInfoDescription=Nika CRM Offline Installer for Windows
VersionInfoCopyright=Copyright (c) 2026 Alexander Smelkov
VersionInfoProductName=Nika CRM
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Dirs]
Name: "{commonappdata}\NikaCRM"; Permissions: admins-full system-full
Name: "{commonappdata}\NikaCRM\logs"; Permissions: admins-full system-full users-readexec

[Files]
Source: "{#SourceRoot}\app\*"; DestDir: "{app}\app\app"; Excludes: "database\service_center.db,database\*.db,database\*.db-*,database\*.sqlite,database\*.sqlite3,*\__pycache__\*,*\*.pyc"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\database\bootstrap\nikacrm_public_sanitized.sql"; DestDir: "{app}\app\database\bootstrap"; Flags: ignoreversion
Source: "{#SourceRoot}\database\bootstrap\README.md"; DestDir: "{app}\app\database\bootstrap"; Flags: ignoreversion
Source: "{#SourceRoot}\docs\*"; DestDir: "{app}\app\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\static\*"; DestDir: "{app}\app\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\templates\*"; DestDir: "{app}\app\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\scripts\run_migrations.py"; DestDir: "{app}\app\scripts"; Flags: ignoreversion
Source: "{#SourceRoot}\scripts\Grant-LocalPostgresAppPrivileges.ps1"; DestDir: "{app}\app\scripts"; Flags: ignoreversion
Source: "{#SourceRoot}\packaging\windows\*.ps1"; DestDir: "{app}\app\packaging\windows"; Flags: ignoreversion
Source: "{#SourceRoot}\packaging\windows\requirements-windows.txt"; DestDir: "{app}\app\packaging\windows"; Flags: ignoreversion
Source: "{#SourceRoot}\packaging\windows\service_entry.py"; DestDir: "{app}\app"; DestName: "nikacrm_service.py"; Flags: ignoreversion
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
Name: "{commondesktop}\Nika CRM — Открыть"; Filename: "http://127.0.0.1:5000"; Comment: "Открыть Nika CRM в браузере (локально). Из локальной сети: http://<IP-этого-ПК>:5000"
Name: "{commondesktop}\Nika CRM — Перезапустить сервис"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\restart-service.ps1"""; WorkingDir: "{app}\app"; Comment: "Перезапустить локальный сервер Nika CRM"
Name: "{group}\Nika CRM — Открыть"; Filename: "http://127.0.0.1:5000"
Name: "{group}\Nika CRM — Перезапустить сервис"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\restart-service.ps1"""; WorkingDir: "{app}\app"
Name: "{group}\Nika CRM — Доступ по сети (LAN)"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\enable-lan-access.ps1"""; WorkingDir: "{app}\app"; Comment: "Включить/починить доступ к CRM из локальной сети"
Name: "{group}\Nika CRM — Пароль базы данных"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\show-db-credentials.ps1"""; WorkingDir: "{app}\app"; Comment: "Показать пароли PostgreSQL для pgAdmin (нужны права администратора)"
Name: "{group}\Nika CRM — Журналы"; Filename: "{sys}\explorer.exe"; Parameters: """{commonappdata}\NikaCRM\logs"""
Name: "{group}\Nika CRM — Руководство пользователя"; Filename: "{#MyGuideURL}"
Name: "{group}\Nika CRM — Онлайн-демо"; Filename: "{#MyDemoURL}"

[Run]
Filename: "http://127.0.0.1:5000"; Description: "Открыть Nika CRM"; Flags: shellexec postinstall skipifsilent nowait
Filename: "{#MyGuideURL}"; Description: "Открыть руководство пользователя"; Flags: shellexec postinstall skipifsilent nowait

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\app\packaging\windows\uninstall-cleanup.ps1"" -AppDir ""{app}"""; Flags: runhidden waituntilterminated; RunOnceId: "NikaCRMCleanup"

[UninstallDelete]
Type: files; Name: "{commondesktop}\Nika CRM - *.lnk"

[Code]
var
  ProductPage: TWizardPage;
  ProductImage: TBitmapImage;
  LegalConfirmationPage: TInputOptionWizardPage;
  DocumentationPage: TWizardPage;

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
    'Демо: https://demo.nika-sc.ru/' + #13#10 +
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
    MsgBox(
      'Для продолжения отметьте оба пункта.',
      mbInformation,
      MB_OK
    );
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  PowerShell: String;
  Bootstrap: String;
  Params: String;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Настройка Python, PostgreSQL, базы данных и службы Nika CRM...';
    PowerShell := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
    Bootstrap := ExpandConstant('{app}\app\packaging\windows\bootstrap.ps1');
    Params :=
      '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + Bootstrap + '"' +
      ' -AppDir "' + ExpandConstant('{app}') + '"' +
      ' -DataDir "' + ExpandConstant('{commonappdata}\NikaCRM') + '"' +
      ' -AssetsDir "' + ExpandConstant('{tmp}\NikaCRM-offline') + '"';
    if not Exec(PowerShell, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Не удалось запустить автоматическую настройку Nika CRM.')
    else if ResultCode <> 0 then
      RaiseException(
        'Автоматическая настройка завершилась с ошибкой ' + IntToStr(ResultCode) +
        '. Журнал: ' + ExpandConstant('{commonappdata}\NikaCRM\logs\setup.log')
      );
  end;
end;
