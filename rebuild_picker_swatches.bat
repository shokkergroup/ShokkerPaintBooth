@echo off
cd /d "%~dp0"
echo Default: incremental bake (changed finishes only).
echo For full Alpha library use: rebuild_picker_swatches_alpha.bat
echo.
python rebuild_picker_swatches.py %*
echo.
pause
