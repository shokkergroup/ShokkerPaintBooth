@echo off
title Shokker Paint Booth - Incremental Thumbnail Rebuild
cd /d "%~dp0"
echo ============================================================
echo   INCREMENTAL THUMBNAIL REBUILD
echo   Only builds missing thumbnails - skips existing ones
echo ============================================================
echo.
python rebuild_thumbnails.py --incremental %*
echo.
echo Done! Restart the app or hit Ctrl+Shift+R to see new thumbnails.
pause
