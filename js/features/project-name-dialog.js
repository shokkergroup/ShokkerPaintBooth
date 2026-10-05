/* SPB-93 2026-09-08: Electron does not support window.prompt().
 * Keep project naming inside the app, with native modal focus and Escape. */
(function () {
    'use strict';
    var active = null;

    window.SPBProjectNameDialog = {
        open: function (defaultName) {
            if (active) return Promise.resolve(null);
            return new Promise(function (resolve) {
                var opener = document.activeElement;
                var dialog = document.createElement('dialog');
                active = dialog;
                dialog.id = 'spbProjectNameDialog';
                dialog.setAttribute('aria-labelledby', 'spbProjectNameTitle');
                dialog.style.cssText = 'position:fixed;inset:0;margin:auto;height:fit-content;max-height:90vh;overflow:auto;width:min(390px,90vw);box-sizing:border-box;padding:22px;border:1px solid #ff9e40;border-radius:12px;background:#0d1420;color:#eef2f8;box-shadow:0 20px 80px #0009;';
                dialog.innerHTML = '<form style="display:grid;gap:14px">' +
                    '<h2 id="spbProjectNameTitle" style="margin:0;font-size:19px">Save project</h2>' +
                    '<label for="spbProjectNameInput">Project name</label>' +
                    '<input id="spbProjectNameInput" name="projectName" required maxlength="80" autocomplete="off" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #64748b;border-radius:6px;background:#182334;color:#fff;font:inherit">' +
                    '<div style="display:flex;justify-content:flex-end;gap:8px">' +
                    '<button type="button" class="btn" data-cancel>Cancel</button>' +
                    '<button type="submit" class="btn" style="background:#ff9e40;color:#151515;font-weight:700">Save</button></div></form>';
                var input = dialog.querySelector('input');
                input.value = String(defaultName || 'My Project').slice(0, 80);
                input.addEventListener('input', function () { input.setCustomValidity(''); });
                dialog.querySelector('form').addEventListener('submit', function (event) {
                    event.preventDefault();
                    if (!input.value.trim()) {
                        input.setCustomValidity('Enter a project name.');
                        input.reportValidity();
                        return;
                    }
                    dialog.close('save');
                });
                dialog.querySelector('[data-cancel]').addEventListener('click', function () { dialog.close('cancel'); });
                dialog.addEventListener('close', function () {
                    var name = dialog.returnValue === 'save' ? input.value.trim() : null;
                    dialog.remove();
                    active = null;
                    if (opener && opener.isConnected) opener.focus({ preventScroll: true });
                    resolve(name);
                }, { once: true });
                document.body.appendChild(dialog);
                dialog.showModal();
                input.focus();
                input.select();
            });
        }
    };
}());
