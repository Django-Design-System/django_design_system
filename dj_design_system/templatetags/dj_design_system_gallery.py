"""Template tags and filters for the gallery UI."""

from __future__ import annotations

import html

from django import template
from django.templatetags.static import static

from dj_design_system.services.media import get_bundle_urls
from dj_design_system.settings import (
    dds_settings,
    get_backgrounds,
    get_default_background,
)


register = template.Library()

BASE_INDENT_PX = 0
INDENT_PER_LEVEL_PX = 16


@register.filter
def add_indent(depth: int) -> int:
    """Convert a tree depth to a left-padding value in pixels.

    depth=1 → 16px, depth=2 → 32px, etc.
    """
    try:
        depth = int(depth)
    except (TypeError, ValueError):
        depth = 0
    return BASE_INDENT_PX + (depth * INDENT_PER_LEVEL_PX)


# ---------------------------------------------------------------------------
# Canvas block tag — renders a component inside an isolated iframe
# ---------------------------------------------------------------------------


class CanvasNode(template.Node):
    """Render children inside an ``<iframe srcdoc="...">``.

    The inner nodelist is evaluated normally (so real component template tags
    execute), and the resulting HTML is wrapped in a full HTML document with
    the correct CSS cascade: global → canvas → component.

    Used exclusively by the gallery UI and documentation renderers.
    """

    def __init__(self, nodelist: template.NodeList):
        self.nodelist = nodelist

    def render(self, context: template.Context) -> str:
        rendered_component = self.nodelist.render(context)

        # Build the full iframe HTML document
        global_css = self._global_css_tags()
        canvas_css_tag = (
            f'<link rel="stylesheet" href="{static("dj_design_system/canvas.css")}">'
        )

        # Collect component media from context if available
        component_css = context.get("_canvas_component_css", "")
        component_js = context.get("_canvas_component_js", "")

        bg_class = context.get(
            "_canvas_bg_class",
            f"canvas-bg-{get_default_background()['value']}",
        )
        mode_class = context.get("_canvas_mode_class", "canvas-wrapper--basic")

        bg_styles = (
            "<style>"
            + "".join(
                f".canvas-bg-{bg['value']}{{background:{bg['color']};}}"
                for bg in get_backgrounds()
            )
            + "</style>"
        )

        resize_script = (
            "<script>"
            "(function(){"
            'var w=document.querySelector(".canvas-wrapper");'
            "if(!w||!window.parent||window.parent===window)return;"
            "new ResizeObserver(function(){"
            "window.parent.postMessage("
            '{type:"canvas-resize",height:document.documentElement.scrollHeight},"*");'
            "}).observe(w);"
            "})();"
            "</script>"
        )

        iframe_doc = (
            "<!DOCTYPE html>"
            f'<html lang="en"{self._html_attrs()}>'
            "<head>"
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"{global_css}"
            f"{canvas_css_tag}"
            f"{component_css}"
            f"{bg_styles}"
            "</head>"
            f"<body{self._body_attrs()}>"
            f'<div class="canvas-wrapper {mode_class} {bg_class}">'
            f"{rendered_component}"
            "</div>"
            f"{component_js}"
            f"{resize_script}"
            "</body>"
            "</html>"
        )

        escaped_doc = html.escape(iframe_doc)
        return (
            f'<iframe class="gallery-canvas" srcdoc="{escaped_doc}" '
            f'title="Component preview"></iframe>'
        )

    def _global_css_tags(self) -> str:
        """Build ``<link>`` tags for global CSS (webpack bundles + static)."""
        all_hrefs = [
            url for url in get_bundle_urls(dds_settings.GLOBAL_CSS_BUNDLES, "css")
        ] + [static(path) for path in dds_settings.GLOBAL_CSS]
        return "".join(f'<link rel="stylesheet" href="{href}">' for href in all_hrefs)

    @staticmethod
    def _flatten_attrs(attrs: dict[str, str]) -> str:
        """Convert a dict to an HTML attribute string with leading space."""
        if not attrs:
            return ""
        return " " + " ".join(f'{k}="{html.escape(v)}"' for k, v in attrs.items())

    def _html_attrs(self) -> str:
        raw = dds_settings.GALLERY_CANVAS_HTML_ATTRS
        return self._flatten_attrs(raw.get("html", {}))

    def _body_attrs(self) -> str:
        raw = dds_settings.GALLERY_CANVAS_HTML_ATTRS
        return self._flatten_attrs(raw.get("body", {}))


@register.tag("canvas")
def do_canvas(parser: template.Parser, token: template.Token) -> CanvasNode:
    """Render the enclosed component tag(s) inside an isolated iframe.

    Usage::

        {% canvas %}{% icon "check" size="large" %}{% endcanvas %}
        {% canvas %}{% callout type="warning" %}Content{% endcallout %}{% endcanvas %}

    The canvas tag captures the rendered output of its children and wraps it
    in a self-contained HTML document inside an ``<iframe srcdoc="...">``.
    """
    nodelist = parser.parse(("endcanvas",))
    parser.delete_first_token()
    return CanvasNode(nodelist)
