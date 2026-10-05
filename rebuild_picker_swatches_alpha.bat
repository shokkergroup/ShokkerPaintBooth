@echo off
cd /d "%~dp0"
echo Full Alpha picker library bake (~20 MB). Run once before packaging a release.
python rebuild_picker_swatches.py --package-alpha %*
echo.
pause
