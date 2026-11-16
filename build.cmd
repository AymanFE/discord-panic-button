@echo off
rem Build DiscordPanic.exe (PyInstaller) and the setup wizard (Inno Setup 6).
setlocal
cd /d "%~dp0"
if "%VERSION%"=="" set VERSION=1.0.0

python -m PyInstaller --noconfirm --clean --onedir --noconsole ^
  --name DiscordPanic --icon assets\icon.ico ^
  --distpath dist --workpath build src\discord_panic.py || exit /b 1

set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
"%ISCC%" /DAppVersion=%VERSION% installer\DiscordPanic.iss || exit /b 1

echo.
echo Done: dist\DiscordPanicSetup-%VERSION%.exe
