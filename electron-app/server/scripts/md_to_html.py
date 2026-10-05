# -*- coding: utf-8 -*-
"""Convert Markdown -> a clean, dark, Chrome-friendly standalone HTML file.

Handles headings, **bold**, `inline code`, fenced ``` code blocks, bullet/numbered
lists, > blockquotes, --- rules, [links](url), and GitHub-style | tables |. Self-contained
(inline CSS), so the output opens straight from disk.

Usage:
  python -B scripts/md_to_html.py                 # converts the overnight audit MDs
  python -B scripts/md_to_html.py path\to\file.md [more.md ...]
"""
import os, sys, re, html

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"

CSS = """
:root{--bg:#0e0f13;--panel:#171922;--ink:#e6e8ee;--mut:#8a90a2;--line:#262a36;--acc:#22c55e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.65 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:40px 28px 80px}
h1{font-size:28px;border-bottom:2px solid var(--acc);padding-bottom:10px}
h2{font-size:22px;margin-top:34px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:18px;margin-top:26px}h4{font-size:15px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
a{color:#7ab8ff}code{background:#0a0b0f;padding:2px 6px;border-radius:5px;color:#9fe0b0;font:13px ui-monospace,Consolas,monospace}
pre{background:#0a0b0f;border:1px solid var(--line);border-radius:8px;padding:14px;overflow:auto}
pre code{background:none;padding:0;color:#cfe0ff}
ul,ol{padding-left:22px}li{margin:4px 0}
blockquote{border-left:3px solid var(--acc);margin:14px 0;padding:2px 16px;color:var(--mut);background:var(--panel)}
hr{border:0;border-top:1px solid var(--line);margin:28px 0}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px}
th,td{border:1px solid var(--line);padding:8px 11px;text-align:left}th{background:var(--panel);color:var(--mut)}
strong{color:#fff}
"""


def _inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def convert(md):
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)
    list_stack = []  # ('ul'|'ol')

    def close_lists():
        while list_stack:
            out.append("</%s>" % list_stack.pop())

    while i < n:
        line = lines[i]
        if line.strip().startswith("```"):
            close_lists()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(html.escape(lines[i])); i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % "\n".join(buf))
            continue
        if not line.strip():
            close_lists(); i += 1; continue
        # table: header row + separator row of ---|---
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|", lines[i + 1]) and "---" in lines[i + 1]:
            close_lists()
            def cells(r):
                return [c.strip() for c in r.strip().strip("|").split("|")]
            hdr = cells(line); i += 2
            out.append("<table><thead><tr>%s</tr></thead><tbody>" %
                       "".join("<th>%s</th>" % _inline(c) for c in hdr))
            while i < n and "|" in lines[i] and lines[i].strip():
                out.append("<tr>%s</tr>" % "".join("<td>%s</td>" % _inline(c) for c in cells(lines[i]))); i += 1
            out.append("</tbody></table>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            close_lists()
            lvl = min(len(m.group(1)), 6)
            out.append("<h%d>%s</h%d>" % (lvl, _inline(m.group(2)), lvl)); i += 1; continue
        if re.match(r"^\s*>\s?", line):
            close_lists()
            out.append("<blockquote>%s</blockquote>" % _inline(re.sub(r"^\s*>\s?", "", line))); i += 1; continue
        if re.match(r"^\s*(---+|\*\*\*+)\s*$", line):
            close_lists(); out.append("<hr>"); i += 1; continue
        mu = re.match(r"^(\s*)([-*])\s+(.*)", line)
        mo = re.match(r"^(\s*)(\d+)\.\s+(.*)", line)
        if mu or mo:
            tag = "ul" if mu else "ol"
            if not list_stack or list_stack[-1] != tag:
                close_lists(); out.append("<%s>" % tag); list_stack.append(tag)
            out.append("<li>%s</li>" % _inline((mu or mo).group(3))); i += 1; continue
        close_lists()
        out.append("<p>%s</p>" % _inline(line)); i += 1
    close_lists()
    return "\n".join(out)


def main(paths):
    for p in paths:
        if not os.path.exists(p):
            print("skip (missing):", p); continue
        md = open(p, encoding="utf-8", errors="replace").read()
        title = os.path.splitext(os.path.basename(p))[0]
        doc = ("<!doctype html><html><head><meta charset='utf-8'><title>%s</title><style>%s</style></head>"
               "<body><div class='wrap'>%s</div></body></html>" % (html.escape(title), CSS, convert(md)))
        outp = os.path.splitext(p)[0] + ".html"
        open(outp, "w", encoding="utf-8").write(doc)
        print("wrote", outp)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        oa = os.path.join(ROOT, "_overnight_audit")
        args = [os.path.join(oa, "MORNING_REPORT.md"), os.path.join(oa, "FINDINGS.md")]
    main(args)
