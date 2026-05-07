@echo off
setlocal
wsl -d Ubuntu-24.04 -u ricky -- bash -lc "cd '/mnt/e/Koda/Shokker Paint Booth Gold to Platinum' && python3 tools/hermes_recon/hermes_recon.py --once"
