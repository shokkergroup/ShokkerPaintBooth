@echo off
title SPB - gate the FRACTURED MOTION fleet
cd /d "%~dp0"
echo Rendering and gating every MOTION finish. No AI involved - deterministic.
echo.
py -3 "_motion_lab\gate_all.py" %*
echo.
echo Full report: _motion_lab\GATE_REPORT.txt
pause
