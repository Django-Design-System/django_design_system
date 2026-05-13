#!/usr/bin/env python3
"""
Fetch canvas iframe pages from the running dev server, save them as clean
static HTML files, and patch the gallery snapshot HTML to reference them.

Why this script exists
----------------------
The gallery's component detail pages embed live canvas pages in iframes using
URLs like ``/_canvas/?component=demo_components__button&mode=basic``.  These
cannot be saved by wget because the ``?`` character is illegal in artifact
upload paths.  The canvas pages also contain absolute ``/static/…`` paths that
break when the snapshot is deployed inside a sub-directory (``/demo/``) on
GitHub Pages.

Additionally, because wget is told to exclude ``/_canvas/`` from its crawl,
any static assets that are *only* referenced from canvas pages (e.g.
``canvas.css``, per-component CSS/JS) would never be downloaded.  This script
fetches those too.

This script:
1. Scans all downloaded HTML files for canvas iframe ``src`` attributes.
2. Fetches every unique canvas URL from the still-running local server.
3. Collects all ``/static/…`` references from each canvas page and fetches
   any that aren't already present in the snapshot's ``static/`` directory.
4. Rewrites ``/static/`` → ``../static/`` inside each fetched canvas page.
5. Saves each page as ``_canvas/<component>__<params>.html``.
6. Patches every gallery HTML file to replace the absolute ``/_canvas/?…``
   src with a relative path to the newly saved clean file.

Usage
-----
    python3 save_canvas_pages.py <snapshot_dir> <base_url>

    snapshot_dir  – root of the wget mirror, e.g. gallery-snapshot/localhost:8000
    base_url      – running server root, e.g. http://localhost:8000
"""

import html as html_module
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


# Matches:  src="/_canvas/?component=…"
#       or  src="http://localhost:8000/_canvas/?component=…"
CANVAS_SRC_RE = re.compile(r'src="((?:http://[^/]+)?/_canvas/\?([^"]+))"')

# Matches any href/src pointing to /static/ (absolute)
STATIC_REF_RE = re.compile(r'(?:href|src)="(/static/[^"]+)"')


def make_clean_name(decoded_qs: str) -> str:
    """Convert a canvas query string into a safe, readable filename."""
    params = dict(urllib.parse.parse_qsl(decoded_qs, keep_blank_values=True))
    component = params.pop("component", "unknown")
    # Sort remaining params so the name is deterministic
    suffix_parts = [f"{k}_{v}" for k, v in sorted(params.items()) if v]
    suffix = "__".join(suffix_parts)
    return component + (f"__{suffix}" if suffix else "") + ".html"


def fix_static_paths(html_content: str) -> str:
    """Rewrite absolute /static/ paths to relative ../static/ ones.

    Canvas files live one level deep inside ``_canvas/``, so ``../static/``
    is the correct relative path back to the snapshot's ``static/`` directory.
    """
    # Simple string replace avoids the backreference double-slash trap
    # (r"../\1" with \1=/static/ would produce ..//static/).
    return html_content.replace('="/static/', '="../static/')


def collect_canvas_urls(snapshot: Path, canvas_out: Path) -> dict[str, str]:
    """Return a mapping of decoded_query_string -> clean_filename."""
    canvas_map: dict[str, str] = {}
    for html_file in sorted(snapshot.rglob("*.html")):
        if html_file.is_relative_to(canvas_out):
            continue
        text = html_file.read_text(encoding="utf-8", errors="replace")
        for m in CANVAS_SRC_RE.finditer(text):
            # m.group(2) is the raw HTML-attribute query string (may contain &amp;)
            decoded_qs = html_module.unescape(m.group(2))
            if decoded_qs not in canvas_map:
                canvas_map[decoded_qs] = make_clean_name(decoded_qs)
    return canvas_map


def fetch_canvas_static_assets(
    canvas_html: str,
    snapshot: Path,
    base_url: str,
) -> None:
    """Fetch any /static/ assets referenced in a canvas page that are not
    already present in the snapshot's static/ directory."""
    for m in STATIC_REF_RE.finditer(canvas_html):
        static_path = m.group(1)  # e.g. /static/dj_design_system/canvas.css
        dest = snapshot / static_path.lstrip("/")
        if dest.exists():
            continue
        url = base_url + static_path
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=15) as resp:
                dest.write_bytes(resp.read())
            print(f"  static {static_path}")
        except Exception as exc:
            print(f"  ERR static {url}: {exc}", file=sys.stderr)


def fetch_and_save(
    canvas_map: dict[str, str],
    canvas_out: Path,
    snapshot: Path,
    base_url: str,
) -> int:
    """Fetch each canvas URL, save static deps, and save as a clean file.
    Returns error count."""
    errors = 0
    for qs, clean_name in canvas_map.items():
        url = f"{base_url}/_canvas/?{qs}"
        out_path = canvas_out / clean_name
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            # Fetch any static assets this canvas page needs that wget missed
            fetch_canvas_static_assets(content, snapshot, base_url)
            content = fix_static_paths(content)
            out_path.write_text(content, encoding="utf-8")
            print(f"  OK   {clean_name}")
        except Exception as exc:
            print(f"  ERR  {url}: {exc}", file=sys.stderr)
            errors += 1
    return errors


def patch_gallery_html(
    snapshot: Path,
    canvas_out: Path,
    canvas_map: dict[str, str],
) -> int:
    """Replace absolute canvas src attrs with relative paths. Returns patched count."""
    patched = 0
    for html_file in sorted(snapshot.rglob("*.html")):
        if html_file.is_relative_to(canvas_out):
            continue
        text = html_file.read_text(encoding="utf-8", errors="replace")

        def replace_src(m: re.Match) -> str:
            decoded_qs = html_module.unescape(m.group(2))
            clean_name = canvas_map.get(decoded_qs)
            if not clean_name:
                return m.group(0)
            canvas_file = canvas_out / clean_name
            rel = os.path.relpath(canvas_file, html_file.parent)
            return f'src="{rel}"'

        new_text = CANVAS_SRC_RE.sub(replace_src, text)
        if new_text != text:
            html_file.write_text(new_text, encoding="utf-8")
            patched += 1
    return patched


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <snapshot_dir> <base_url>", file=sys.stderr)
        sys.exit(1)

    snapshot = Path(sys.argv[1])
    base_url = sys.argv[2].rstrip("/")
    canvas_out = snapshot / "_canvas"
    canvas_out.mkdir(exist_ok=True)

    canvas_map = collect_canvas_urls(snapshot, canvas_out)
    print(f"Found {len(canvas_map)} unique canvas URLs.")

    errors = fetch_and_save(canvas_map, canvas_out, snapshot, base_url)
    patched = patch_gallery_html(snapshot, canvas_out, canvas_map)

    print(f"Patched {patched} gallery HTML files.")
    if errors:
        print(f"WARNING: {errors} canvas page(s) failed to fetch.", file=sys.stderr)
        # Non-fatal: the gallery is still usable; broken previews are better than no gallery.


if __name__ == "__main__":
    main()
