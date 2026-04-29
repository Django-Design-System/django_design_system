from typing import Type

from django.templatetags.static import static
from django.utils.html import format_html_join

from dj_design_system.data import ComponentMedia

try:
    from webpack_loader.utils import get_files as _webpack_get_files

    _WEBPACK_AVAILABLE = True
except ImportError:
    _webpack_get_files = None
    _WEBPACK_AVAILABLE = False


def coerce_path_list(value: str | list[str]) -> list[str]:
    """Normalise a CSS/JS path value to a list of strings.

    Accepts either a single string or a list of strings, returning a list
    in both cases.  This mirrors the convention used by Django's form widget
    ``Media`` inner class, where single strings are also accepted.
    """
    if isinstance(value, str):
        return [value]
    return list(value)


def get_own_media(cls: Type) -> ComponentMedia | None:
    """Return a ``ComponentMedia`` built from *cls*'s own ``Media`` inner class.

    Returns ``None`` if *cls* has no ``Media`` defined directly on it (i.e.
    not inherited).  Accepts a single string or a list for each of ``css``
    and ``js``.
    """
    media_cls = cls.__dict__.get("Media")
    if media_cls is None:
        return None

    css_raw = coerce_path_list(getattr(media_cls, "css", []))
    js_raw = coerce_path_list(getattr(media_cls, "js", []))

    return ComponentMedia(css=css_raw, js=js_raw)


def get_bundle_urls(bundles: list[tuple], extension: str) -> list[str]:
    """Return chunk URLs from webpack bundles, or an empty list.

    Each entry in *bundles* is a tuple whose first element is the bundle name
    and whose optional second element is the webpack_loader config name
    (defaults to ``"DEFAULT"``).  Returns an empty list when
    ``webpack_loader`` is not installed or *bundles* is empty.
    """
    if not _WEBPACK_AVAILABLE or not bundles:
        return []
    urls: list[str] = []
    for bundle_args in bundles:
        bundle_name = bundle_args[0]
        config = bundle_args[1] if len(bundle_args) > 1 else "DEFAULT"
        for chunk in _webpack_get_files(
            bundle_name, extension=extension, config=config
        ):
            urls.append(chunk["url"])
    return urls


def build_static_url(app_label: str, relative_path: str, name: str, ext: str) -> str:
    """Build the Django static URL for a co-located component asset.

    Given a component with ``app_label="myapp"``, ``relative_path="cards"``,
    ``name="hero"`` and ``ext=".css"``, returns
    ``"myapp/components/cards/hero.css"``.
    """
    parts = [app_label, "components"]
    if relative_path:
        parts.extend(relative_path.split("."))
    parts.append(f"{name}{ext}")
    return "/".join(parts)


def build_link_tags(css_paths: list[str]) -> str:
    """Build ``<link>`` tags for a list of static CSS paths."""
    if not css_paths:
        return ""
    return format_html_join(
        "\n",
        '<link rel="stylesheet" href="{}">',
        ((static(path),) for path in css_paths),
    )


def build_script_tags(js_paths: list[str]) -> str:
    """Build ``<script>`` tags for a list of static JS paths."""
    if not js_paths:
        return ""
    return format_html_join(
        "\n",
        '<script src="{}"></script>',
        ((static(path),) for path in js_paths),
    )
