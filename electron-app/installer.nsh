; Shokker Paint Booth — custom NSIS include (upgrade-hang hardening, 2026-06-07)
;
; Why this exists: buyers upgrading from an older build kept hitting "Shokker Paint
; Booth V6 is running" and a hung 7z install, because the old app (and its bundled
; Python server child process) held file locks while the one-click installer tried to
; overwrite them. This force-closes EVERY Shokker process before the installer touches
; any files, so the install can never hang on a running app or locked files — no matter
; how many old copies are on the machine.
;
; customInit runs in .onInit, BEFORE the install section extracts files (the critical
; spot). customInstall runs again inside the install section as belt-and-suspenders in
; case the old app auto-relaunched in the gap. Both swallow errors (a process that
; isn't running just returns non-zero, which we ignore).

!macro killShokker
  ; [10.0.0 RENAME 2026-08-09] The exe name comes from package.json build.productName,
  ; which became "Shokker Paint Booth V10". V10 MUST be listed first: without it, any
  ; future 10.x -> 10.y upgrade (or a re-install over a running 10.0.0) would hit the
  ; exact locked-file hang this whole file exists to prevent. The older names stay so
  ; upgrades FROM V8/V7/V6 keep working.
  nsExec::Exec 'taskkill /F /T /IM "Shokker Paint Booth V10.exe"'
  nsExec::Exec 'taskkill /F /T /IM "Shokker Paint Booth V8.exe"'
  nsExec::Exec 'taskkill /F /T /IM "Shokker Paint Booth V7.exe"'
  nsExec::Exec 'taskkill /F /T /IM "Shokker Paint Booth V6.exe"'
  nsExec::Exec 'taskkill /F /T /IM "shokker-server.exe"'
  nsExec::Exec 'taskkill /F /T /IM "shokker-paint-booth-v5.exe"'
  nsExec::Exec 'taskkill /F /T /IM "shokker-paint-booth-ag.exe"'
!macroend

!macro customInit
  ; SPB 2026-07-23 install-UX overhaul (owner: "could definitely look like it's hanging"):
  ; the payload now ships with compression: "store", so the post-download extraction that used
  ; to sit frozen for 2-3 minutes is a near-instant file copy — the DOWNLOAD progress bar now
  ; covers essentially the whole install. The old scary "may look FROZEN" MessageBox is retired;
  ; a short heads-up about the one-download size remains.
  ; IfSilent guard: auto-update runs the installer with /S — a MessageBox there would HANG the
  ; silent auto-update, so skip the prompt when silent.
  IfSilent +2
  MessageBox MB_OK|MB_ICONINFORMATION "Shokker Paint Booth installs EVERYTHING — every finish included — in ONE download (a few GB).$\r$\n$\r$\nThe progress bar tracks the whole install. On most connections this takes a few minutes — grab a coffee and it'll be ready to paint."
  DetailPrint "Closing any running Shokker Paint Booth before installing..."
  !insertmacro killShokker
  Sleep 1500
!macroend

!macro customInstall
  SetDetailsPrint both
  DetailPrint "Finalizing install..."
  !insertmacro killShokker
  Sleep 600
!macroend
