@echo off
echo Building Monster & MonsterSetBase Editor...
echo.

rem Navigate to the correct directory if needed
cd /d "%~dp0"

rem Install PyInstaller if not already installed
pip install pyinstaller

rem Run PyInstaller with correct paths
pyinstaller --onefile --windowed --icon=icon.ico --name="MonsterSpawnEditor" src\monster_spawn_editor.py

echo.
if %ERRORLEVEL% EQU 0 (
  echo Build completed successfully! 
  echo The executable is located in the 'dist' folder.
) else (
  echo Build failed with error code %ERRORLEVEL%
)

pause 