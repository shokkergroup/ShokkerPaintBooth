"""Clickable source links in the common answer formatter; shared source untouched."""

BEFORE = r"""    function fmt(s) { return esc(s).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/^- /gm, '\u2022 ').replace(/\n{2,}/g, '<br>').replace(/\n/g, '<br>'); }"""
AFTER = r"""    function fmtPlain(s) { return esc(s).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/^- /gm, '\u2022 ').replace(/\n{2,}/g, '<br>').replace(/\n/g, '<br>'); }
    // Source links are navigation only: never fetch, download or dispatch paint.
    function fmt(s) {
        s = String(s == null ? '' : s);
        if (window.SPB_ANSWER_LINKS_OFF) return fmtPlain(s);
        var prefix = 'SPB_SOURCE_LINK_TOKEN_'; while (s.indexOf(prefix) >= 0) prefix += '_';
        var links = [], pattern = /\[([^\]\r\n]{1,160})\]\((https:\/\/[^\s<>"'\\()\x00-\x1f`*]{1,2048})\)|(https:\/\/[^\s<>"'\\\x00-\x1f`*]{1,2048})/gi;
        var marked = s.replace(pattern, function (whole, label, markdownUrl, bareUrl, offset, original) {
            if (links.length >= 12) return whole;
            if (bareUrl && original.charAt(offset + whole.length) === '\\') return whole;
            var url = markdownUrl || bareUrl, suffix = '';
            if (bareUrl) {
                var prior;
                do {
                    prior = url;
                    if (/[.,;:!?\]}]$/.test(url) || (/\)$/.test(url) && (url.match(/\)/g) || []).length > (url.match(/\(/g) || []).length)) { suffix = url.slice(-1) + suffix; url = url.slice(0, -1); }
                } while (url !== prior);
            }
            var parsed; try { parsed = new URL(url); } catch (eLink) { return whole; }
            if (parsed.protocol !== 'https:' || !parsed.hostname || parsed.username || parsed.password || (parsed.port && parsed.port !== '443')) return whole;
            var marker = prefix + links.length + '_END';
            links.push({ marker: marker, html: '<a class="spb-pai-source-link" style="color:inherit;text-decoration:underline;overflow-wrap:anywhere" href="' + esc(url) + '" title="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(label || url) + '</a>' });
            return marker + suffix;
        });
        var html = fmtPlain(marked);
        links.forEach(function (link) { html = html.split(link.marker).join(link.html); });
        return html;
    }"""

def edits(relative):
    return [(BEFORE, AFTER, 1)] if relative == 'js/spb-pro-ai.js' else []
