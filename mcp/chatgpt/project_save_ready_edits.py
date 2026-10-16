"""Refuse project capture during the existing PSD import transaction."""


def edits(relative):
    if relative != 'js/features/spb-projects.js':
        return []
    return [(
        '    function buildProjectPayload(name) {\n',
        '''    function buildProjectPayload(name) {
        // CX4: a pending import can expose an empty/previous layer list.
        // Check here after the asynchronous name dialog as well as at entry.
        if (window._spbPsdImportInFlight === true) {
            _toast('Project was not saved: paint layers are still loading. Wait for PSD ready, then save again.', true);
            return null;
        }
''', 1), (
        "    async function saveSpbProject() {\n        var defaultName = '';",
        """    async function saveSpbProject() {
        if (window._spbPsdImportInFlight === true) {
            _toast('Project was not saved: paint layers are still loading. Wait for PSD ready, then save again.', true);
            return false;
        }
        var defaultName = '';""", 1)]
