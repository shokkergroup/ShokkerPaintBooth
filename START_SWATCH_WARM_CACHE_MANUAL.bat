@echo off
setlocal
title SPB Manual Swatch Warm Cache
cd /d "%~dp0"

echo ============================================================
echo   SPB MANUAL SWATCH WARM CACHE
echo   This is intentionally heavy. Run it when you want to
echo   refresh picker thumbnails, not during active painting.
echo ============================================================
echo.

if exist "C:\Python313\python.exe" (
    C:\Python313\python.exe rebuild_picker_swatches.py --warm-cache
) else (
    python rebuild_picker_swatches.py --warm-cache
)

echo.
echo Done. You can close this window.
pause
endlocal
