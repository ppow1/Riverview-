# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/markdown.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.1
# Purpose: Render approved component documentation as safe readable HTML
# Execution Model: Request-time pure rendering of repository-controlled Markdown
# Observability: Invalid or unsupported links remain inert text
# Dependencies: Python standard library
# Authority: No raw HTML; links are limited to HTTPS, anchors, and approved docs
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Preserve final character of validated local documentation links
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: tests/test_status_dashboard.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Small safe renderer for repository-controlled operational documentation."""

from __future__ import annotations

from html import escape
from pathlib import PurePosixPath
import posixpath
import re
from urllib.parse import urlsplit


_INLINE = re.compile(r"(\[[^\]]+\]\([^)]+\)|\*\*.+?\*\*|`[^`]+`|\*[^*]+\*)")
_TABLE_RULE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$|^\|?\s*:?-{3,}:?\s*\|?$")
_LANGUAGE = re.compile(r"^[A-Za-z0-9_+-]{0,24}$")


def _doc_href(raw: str, document: str) -> str | None:
    """Resolve only safe external links and links inside the component-doc set."""
    if raw.startswith("#") and re.fullmatch(r"#[A-Za-z0-9_.:-]*", raw):
        return raw
    parsed = urlsplit(raw)
    if parsed.scheme in {"http", "https"} and parsed.netloc and not parsed.username:
        return raw
    if parsed.scheme or parsed.netloc or parsed.query:
        return None
    path = parsed.path
    if path.startswith("docs/"):
        target = posixpath.normpath(path)
    elif path.startswith("/"):
        target = posixpath.normpath(path.lstrip("/"))
    else:
        target = posixpath.normpath(posixpath.join(PurePosixPath(document).parent.as_posix(), path))
    if (target.startswith("docs/components/") and target.endswith(".md") and
            ".." not in PurePosixPath(target).parts):
        return "/" + target
    return None


def _inline(text: str, document: str) -> str:
    pieces = []
    cursor = 0
    for match in _INLINE.finditer(text):
        pieces.append(escape(text[cursor:match.start()]))
        token = match.group(0)
        if token.startswith("["):
            label, raw_href = token[1:-1].split("](", 1)
            raw_href = raw_href.strip()
            href = _doc_href(raw_href, document)
            label_html = escape(label)
            if href:
                ext = ' target="_blank" rel="noopener noreferrer"' if href.startswith("https:") else ""
                pieces.append(f'<a href="{escape(href, quote=True)}"{ext}>{label_html}</a>')
            else:
                pieces.append(label_html)
        elif token.startswith("**"):
            pieces.append("<strong>" + escape(token[2:-2]) + "</strong>")
        elif token.startswith("`"):
            pieces.append("<code>" + escape(token[1:-1]) + "</code>")
        elif token.startswith("*"):
            pieces.append("<em>" + escape(token[1:-1]) + "</em>")
        cursor = match.end()
    pieces.append(escape(text[cursor:]))
    return "".join(pieces)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render_markdown(source: str, *, document: str, title: str) -> bytes:
    """Render headings, paragraphs, lists, tables and fenced code without raw HTML."""
    lines = source.splitlines()
    visible = []
    in_comment = False
    for line in lines:
        stripped = line.strip()
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            in_comment = "-->" not in stripped
            continue
        visible.append(line)
    if visible and visible[0].strip() == "---":
        end = next((i for i, line in enumerate(visible[1:], 1) if line.strip() == "---"), None)
        if end is not None:
            visible = visible[end + 1:]

    out = ['<article class="readable-doc">']
    i = 0
    heading_counts: dict[str, int] = {}
    while i < len(visible):
        line = visible[i]
        text = line.strip()
        if not text:
            i += 1
            continue
        if text.startswith("```"):
            language = text[3:].strip().split(maxsplit=1)[0] if text[3:].strip() else ""
            language = language if _LANGUAGE.fullmatch(language) else ""
            block = []
            i += 1
            while i < len(visible) and not visible[i].strip().startswith("```"):
                block.append(visible[i])
                i += 1
            i += i < len(visible)
            cls = f' class="language-{language}"' if language else ""
            out.append(f"<pre><code{cls}>{escape(chr(10).join(block))}</code></pre>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", text)
        if heading:
            level, label = len(heading.group(1)), heading.group(2)
            slug_base = re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-") or "section"
            count = heading_counts.get(slug_base, 0) + 1
            heading_counts[slug_base] = count
            slug = slug_base if count == 1 else f"{slug_base}-{count}"
            out.append(f'<h{level} id="{slug}">{_inline(label, document)}</h{level}>')
            i += 1
            continue
        if (i + 1 < len(visible) and "|" in text and
                _TABLE_RULE.fullmatch(visible[i + 1].strip())):
            headers = _cells(text)
            out.append('<div class="doc-table-wrap"><table><thead><tr>')
            out.extend(f"<th>{_inline(cell, document)}</th>" for cell in headers)
            out.append("</tr></thead><tbody>")
            i += 2
            while i < len(visible) and visible[i].strip() and "|" in visible[i]:
                cells = _cells(visible[i])
                out.append("<tr>")
                for index in range(len(headers)):
                    out.append("<td>" + _inline(cells[index] if index < len(cells) else "", document) + "</td>")
                out.append("</tr>")
                i += 1
            out.append("</tbody></table></div>")
            continue
        list_match = re.match(r"^\s*([-*+] |\d+[.)] )(.*)$", line)
        if list_match:
            ordered = bool(re.match(r"^\s*\d", line))
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>")
            while i < len(visible):
                item = re.match(r"^\s*([-*+] |\d+[.)] )(.*)$", visible[i])
                if not item or bool(re.match(r"^\s*\d", visible[i])) != ordered:
                    break
                out.append("<li>" + _inline(item.group(2), document) + "</li>")
                i += 1
            out.append(f"</{tag}>")
            continue
        if re.fullmatch(r"([-*_]\s*){3,}", text):
            out.append("<hr>")
            i += 1
            continue
        para = [text]
        i += 1
        while i < len(visible):
            nxt = visible[i].strip()
            if (not nxt or nxt.startswith(("```", "# ", "## ", "### ", "#### ", "- ", "* ", "+ ")) or
                    (i + 1 < len(visible) and "|" in nxt and _TABLE_RULE.fullmatch(visible[i + 1].strip()))):
                break
            para.append(nxt)
            i += 1
        out.append("<p>" + _inline(" ".join(para), document) + "</p>")
    out.append("</article>")
    page = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{escape(title)}</title><link rel=\"stylesheet\" href=\"/assets/app.css\"></head>"
            f"<body class=\"doc-page\"><header class=\"doc-topbar\"><a href=\"/#activity\">← Riverview dashboard</a>"
            f"<span>{escape(title)}</span></header><main>{''.join(out)}</main></body></html>")
    return page.encode("utf-8")
