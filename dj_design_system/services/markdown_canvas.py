"""Markdown extension for embedding live canvas previews.

Provides a ``CanvasExtension`` that registers a ``Preprocessor`` to find
fenced ``canvas`` blocks and replace them with an HTML widget containing
a live preview iframe and a syntax-highlighted code block.

Syntax
------
In markdown files::

    ```canvas
    {% icon "check" size="large" %}
    ```

Block components::

    ```canvas
    {% callout type="warning" %}Warning content{% endcallout %}
    ```

The preprocessor parses the Django template tag syntax, builds a
``CanvasSpec``, and outputs an iframe (``src`` URL pointing to ``_canvas/``)
plus a highlighted code block with a toggle.
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from markdown import Extension
from markdown.preprocessors import Preprocessor

from dj_design_system.data import CanvasSpec
from dj_design_system.services.canvas import build_canvas_url
from dj_design_system.services.tag_signature import highlight_code


if TYPE_CHECKING:
    from markdown import Markdown


# ---------------------------------------------------------------------------
# Tag syntax parser
# ---------------------------------------------------------------------------

# Matches: {% tag_name ... %} with optional content and {% endtag_name %}
_TAG_RE = re.compile(
    r"\{%[-\s]*(\w+)"  # opening tag name
    r"(.*?)"  # everything between tag name and %}
    r"\s*%\}"  # closing %}
)

# Matches: keyword="value", keyword='value', or keyword=value.
# Unquoted values support booleans and other bare tokens in template syntax.
_KWARG_RE = re.compile(r"""(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s%}]+))""")

# Matches: "value" or 'value' (positional argument)
_POS_ARG_RE = re.compile(r"""(?:"([^"]*)"|'([^']*)')""")


def parse_tag_syntax(source: str) -> CanvasSpec:
    """Parse Django template tag syntax into a ``CanvasSpec``.

    Handles both inline tags (``{% icon "check" %}``) and block tags
    (``{% callout type="warning" %}Content{% endcallout %}``).

    Raises ``ValueError`` if the syntax cannot be parsed.
    """
    source = source.strip()
    if not source:
        raise ValueError("Empty canvas block.")

    match = _TAG_RE.match(source)
    if not match:
        raise ValueError(f"Cannot parse template tag: {source!r}")

    tag_name = match.group(1)
    args_str = match.group(2).strip()

    # Extract keyword arguments
    kwargs: dict[str, str] = {}
    for m in _KWARG_RE.finditer(args_str):
        kwargs[m.group(1)] = next(
            group for group in (m.group(2), m.group(3), m.group(4)) if group is not None
        )

    # Extract positional arguments (quoted strings not part of a kwarg)
    # Remove kwargs from args_str first, then find remaining quoted strings
    remaining = _KWARG_RE.sub("", args_str).strip()
    positional: list[str] = []
    for m in _POS_ARG_RE.finditer(remaining):
        positional.append(m.group(1) if m.group(1) is not None else m.group(2))

    # Check for block content: text between %} and {% endtag_name %}
    after_opening = source[match.end() :]
    closing_pattern = re.compile(
        r"\{%[-\s]*end" + re.escape(tag_name) + r"\s*%\}", re.IGNORECASE
    )
    closing_match = closing_pattern.search(after_opening)
    if closing_match:
        content = after_opening[: closing_match.start()].strip()
        if content:
            kwargs["content"] = content

    return CanvasSpec(
        component_name=tag_name,
        params=kwargs,
        positional_args=tuple(positional),
    )


# ---------------------------------------------------------------------------
# Widget HTML builder
# ---------------------------------------------------------------------------


def _build_widget_html(
    source: str,
    canvas_url: str,
    unique_id: str,
) -> str:
    """Build the HTML widget with preview iframe, code block, and toggle.

    Radio inputs are placed as direct children of the wrapper so CSS
    ``:checked ~ .target`` selectors can show/hide preview and code.
    Labels are positioned absolutely in the bottom right via CSS.
    """
    highlighted = highlight_code(source)
    escaped_source = html.escape(source)

    # If highlight failed, fall back to plain text
    code_inner = highlighted if highlighted else escaped_source

    return (
        f'<div class="gallery-md-canvas">'
        # Radio inputs at root level for CSS sibling targeting
        f'<input type="radio" name="mc-toggle-{unique_id}" '
        f'id="mc-both-{unique_id}" class="gallery-md-canvas__input '
        f'gallery-md-canvas__input--both" checked>'
        f'<input type="radio" name="mc-toggle-{unique_id}" '
        f'id="mc-preview-{unique_id}" class="gallery-md-canvas__input '
        f'gallery-md-canvas__input--preview">'
        f'<input type="radio" name="mc-toggle-{unique_id}" '
        f'id="mc-code-{unique_id}" class="gallery-md-canvas__input '
        f'gallery-md-canvas__input--code">'
        # Toggle labels (positioned via CSS)
        f'<div class="gallery-md-canvas__toggles">'
        f'<label for="mc-both-{unique_id}" class="gallery-md-canvas__label" '
        f'title="Preview and code">'
        # Split icon (horizontal line dividing a box)
        f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2"><rect x="3" y="3" '
        f'width="18" height="18" rx="2"/><line x1="3" y1="12" x2="21" '
        f'y2="12"/></svg>'
        f"</label>"
        f'<label for="mc-preview-{unique_id}" class="gallery-md-canvas__label" '
        f'title="Preview only">'
        # Eye icon
        f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 '
        f'8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'
        f"</label>"
        f'<label for="mc-code-{unique_id}" class="gallery-md-canvas__label" '
        f'title="Code only">'
        # Code brackets icon
        f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/>'
        f'<polyline points="8 6 2 12 8 18"/></svg>'
        f"</label>"
        f"</div>"
        # Preview iframe
        f'<div class="gallery-md-canvas__preview">'
        f'<iframe class="gallery-canvas gallery-md-canvas__iframe" '
        f'src="{html.escape(canvas_url)}" '
        f'loading="lazy" '
        f'title="Component preview"></iframe>'
        f"</div>"
        # Code block
        f'<div class="gallery-md-canvas__code">'
        f'<pre class="gallery-usage__pre"><code class="gallery-usage__code">'
        f"{code_inner}</code></pre>"
        f"</div>"
        f"</div>"
    )


def _build_error_html(message: str, source: str = "", debug: bool = False) -> str:
    """Build error HTML for invalid canvas blocks."""
    error = f'<p style="color:red;">Canvas error: {html.escape(message)}</p>'
    if debug and source:
        escaped = html.escape(source)
        error += f"<pre><code>{escaped}</code></pre>"
    return error


# ---------------------------------------------------------------------------
# Markdown Preprocessor
# ---------------------------------------------------------------------------

# Matches a fenced canvas block: ```canvas ... ```
_FENCE_RE = re.compile(
    r"^```canvas\s*$\n"  # opening fence
    r"(.*?)\n"  # content (non-greedy)
    r"^```\s*$",  # closing fence
    re.MULTILINE | re.DOTALL,
)

# Matches fenced blocks with no language or generic languages (py, python)
# that contain Django template syntax, and re-tags them as html+django.
_UNLABELLED_FENCE_RE = re.compile(
    r"^```(py|python)?\s*$\n"  # opening: no lang or py/python
    r"(.*?)\n"  # content
    r"^```\s*$",  # closing
    re.MULTILINE | re.DOTALL,
)

_DJANGO_SYNTAX_RE = re.compile(r"\{[%{]")


class DjangoLangPreprocessor(Preprocessor):
    """Re-tag fenced blocks containing Django syntax as ``html+django``.

    Runs before the canvas preprocessor and fenced_code. Blocks with no
    language tag (or ``py``/``python``) that contain ``{%`` or ``{{`` are
    relabelled so codehilite uses the Django/Jinja template lexer.
    """

    def run(self, lines: list[str]) -> list[str]:
        text = "\n".join(lines)
        text = _UNLABELLED_FENCE_RE.sub(self._maybe_retag, text)
        return text.split("\n")

    @staticmethod
    def _maybe_retag(match: re.Match) -> str:
        content = match.group(2)
        if _DJANGO_SYNTAX_RE.search(content):
            return f"```html+django\n{content}\n```"
        return match.group(0)


class CanvasPreprocessor(Preprocessor):
    """Replace fenced ``canvas`` blocks with live preview widgets."""

    def __init__(self, md: Markdown, canvas_base_url: str, debug: bool = False):
        super().__init__(md)
        self.canvas_base_url = canvas_base_url
        self.debug = debug
        self._counter = 0

    def run(self, lines: list[str]) -> list[str]:
        """Process all lines, replacing canvas blocks with HTML widgets."""
        text = "\n".join(lines)
        text = _FENCE_RE.sub(self._replace_match, text)
        return text.split("\n")

    def _replace_match(self, match: re.Match) -> str:
        """Replace a single canvas fence match with widget HTML."""
        source = match.group(1).strip()
        self._counter += 1
        unique_id = str(self._counter)

        try:
            spec = parse_tag_syntax(source)
            canvas_url = build_canvas_url(spec, self.canvas_base_url) + "&mode=basic"
            return _build_widget_html(source, canvas_url, unique_id)
        except ValueError as exc:
            return _build_error_html(str(exc), source, self.debug)


# ---------------------------------------------------------------------------
# Markdown Extension
# ---------------------------------------------------------------------------


class CanvasExtension(Extension):
    """Markdown extension that processes fenced ``canvas`` blocks.

    Requires ``canvas_base_url`` config (the ``_canvas/`` endpoint URL).
    """

    def __init__(self, **kwargs):
        self.config = {
            "canvas_base_url": ["", "Base URL for the canvas iframe endpoint"],
            "debug": [False, "Show source on errors"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        """Register preprocessors.

        CanvasPreprocessor (priority 32) replaces canvas blocks with widgets
        before any generic fence retagging runs. DjangoLangPreprocessor
        (priority 30) then re-tags remaining fenced blocks containing Django
        syntax. Both run before fenced_code (priority 25).
        """
        preprocessor = CanvasPreprocessor(
            md,
            canvas_base_url=self.getConfig("canvas_base_url"),
            debug=self.getConfig("debug"),
        )
        md.preprocessors.register(preprocessor, "canvas", 32)
        md.preprocessors.register(DjangoLangPreprocessor(md), "django-lang", 30)
