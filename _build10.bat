@echo off
cd /d "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine"
C:\Python313\python.exe -m PyInstaller --onefile --name shokker-server --distpath "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\electron-app\server" --workpath "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\_pybuild_work" --specpath "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\_pybuild_work" --add-data "shokker_engine_v2.py;." --hidden-import flask --hidden-import flask_cors --hidden-import numpy --hidden-import PIL --hidden-import PIL.Image --hidden-import PIL.ImageFilter --clean --noconfirm server.py
echo EXIT CODE: %errorlevel%
