from django.conf import settings

from dj_design_system.services.media import coerce_path_list
from dj_design_system.types import NodeType

# Built-in canvas backgrounds keyed by slug.  Each entry is a dict with
# ``label`` and ``color`` (a CSS <background> value).  Projects can replace
# this entirely via ``GALLERY_CANVAS_BACKGROUNDS`` or merge extra entries
# via ``GALLERY_CANVAS_EXTRA_BACKGROUNDS``.
BUILTIN_CANVAS_BACKGROUNDS: dict[str, dict] = {
    "white": {"label": "White", "color": "#ffffff"},
    "light-grey": {"label": "Light Grey", "color": "#f0f0f0"},
    "dark-grey": {"label": "Dark Grey", "color": "#404040"},
    "black": {"label": "Black", "color": "#000000"},
    "checkerboard": {
        "label": "Checkerboard",
        "color": (
            "repeating-conic-gradient(#e0e0e0 0% 25%, transparent 0% 50%) "
            "0 0 / 20px 20px #ffffff"
        ),
    },
}


DEFAULTS: dict = {
    "DESIGN_SYSTEM_NAME": "Django Design System",
    "ENABLE_GALLERY": True,
    "GALLERY_IS_PUBLIC": True,
    "GALLERY_NAV_ORDER": [NodeType.FOLDER, NodeType.COMPONENT, NodeType.DOCUMENT],
    "GLOBAL_CSS": [],
    "GLOBAL_JS": [],
    # Each entry is a tuple of positional args passed to webpack_loader's
    # ``get_files(bundle_name, extension, config)``:
    #   ("main",)              → get_files("main", extension=..., config="DEFAULT")
    #   ("main", "MY_CONFIG") → get_files("main", extension=..., config="MY_CONFIG")
    # Ignored when webpack_loader is not installed.
    "GLOBAL_CSS_BUNDLES": [],
    "GLOBAL_JS_BUNDLES": [],
    "GALLERY_CANVAS_BACKGROUNDS": BUILTIN_CANVAS_BACKGROUNDS,
    "GALLERY_CANVAS_EXTRA_BACKGROUNDS": {},
    "GALLERY_CANVAS_DEFAULT_BACKGROUND": "light-grey",
    # Extra HTML attributes for the canvas iframe's <html> and <body> tags.
    # Example: {"html": {"class": "govuk-template"}, "body": {"class": "govuk-template__body"}}
    "GALLERY_CANVAS_HTML_ATTRS": {},
    # Pygments style used for syntax highlighting in markdown fenced code
    # blocks and canvas code previews. Set to "" to disable highlighting.
    "GALLERY_CODEHILITE_STYLE": "monokai",
}

# Settings whose values are normalised to a list of strings.
_PATH_LIST_SETTINGS = {"GLOBAL_CSS", "GLOBAL_JS"}


class DjangoDesignSystemSettings:
    DESIGN_SYSTEM_NAME: str
    ENABLE_GALLERY: bool
    GALLERY_IS_PUBLIC: bool
    GALLERY_NAV_ORDER: list[NodeType] | str
    GLOBAL_CSS: list[str]
    GLOBAL_JS: list[str]
    GLOBAL_CSS_BUNDLES: list[tuple[str, ...]]
    GLOBAL_JS_BUNDLES: list[tuple[str, ...]]
    GALLERY_CANVAS_DEFAULT_BACKGROUND: str
    GALLERY_CANVAS_BACKGROUNDS: dict[str, dict]
    GALLERY_CANVAS_EXTRA_BACKGROUNDS: dict[str, dict]
    GALLERY_CANVAS_HTML_ATTRS: dict
    GALLERY_CODEHILITE_STYLE: str

    def __getattr__(self, attr: str):
        django_settings = getattr(settings, "dj_design_system", {})

        if attr in django_settings:
            value = django_settings[attr]
        else:
            # Check if present in defaults
            if attr not in DEFAULTS:
                raise AttributeError(
                    f"No value set for dj_design_system['{attr}']"
                )
            value = DEFAULTS[attr]

        if attr in _PATH_LIST_SETTINGS:
            return coerce_path_list(value)
        return value


dds_settings = DjangoDesignSystemSettings()


def get_backgrounds() -> list[dict]:
    """Return the merged list of canvas backgrounds.

    ``GALLERY_CANVAS_EXTRA_BACKGROUNDS`` entries are merged into (and can
    override) ``GALLERY_CANVAS_BACKGROUNDS``.  Each returned dict has
    ``value``, ``label``, and ``color`` keys.
    """
    merged = {
        **dds_settings.GALLERY_CANVAS_BACKGROUNDS,
        **dds_settings.GALLERY_CANVAS_EXTRA_BACKGROUNDS,
    }
    return [{"value": key, **entry} for key, entry in merged.items()]


def get_default_background() -> dict:
    """Return the default background as a ``{"value", "label", "color"}`` dict."""
    value = dds_settings.GALLERY_CANVAS_DEFAULT_BACKGROUND
    backgrounds = get_backgrounds()
    for bg in backgrounds:
        if bg["value"] == value:
            return bg
    # Fallback to first configured background, then hard-coded light grey.
    if backgrounds:
        return backgrounds[0]
    return {"value": "light-grey", "label": "Light Grey", "color": "#f0f0f0"}
