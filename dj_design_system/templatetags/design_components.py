from django import template
from django.templatetags.static import static
from django.utils.html import format_html_join

from dj_design_system import component_registry
from dj_design_system.services.media import (
    build_link_tags,
    build_script_tags,
    get_bundle_urls,
)
from dj_design_system.settings import dds_settings


register = template.Library()

component_registry.register_templatetags(register)


@register.simple_tag
def component_stylesheets() -> str:
    """Render ``<link>`` tags for every CSS file required by registered components.

    Merges the CSS paths from all discovered components, deduplicating across
    components, and returns safe HTML ready to embed in ``<head>``.
    """
    return build_link_tags(component_registry.get_merged_media().css)


@register.simple_tag
def component_scripts() -> str:
    """Render ``<script>`` tags for every JS file required by registered components.

    Merges the JS paths from all discovered components, deduplicating across
    components, and returns safe HTML ready to embed before ``</body>``.
    """
    return build_script_tags(component_registry.get_merged_media().js)


@register.simple_tag
def global_stylesheets() -> str:
    """Render ``<link>`` tags for global CSS bundles and static paths.

    Sources (in order):

    1. Webpack bundles listed in ``GLOBAL_CSS_BUNDLES`` - each entry is a
       tuple of args for ``webpack_loader.utils.get_files``, e.g.
       ``("main",)`` or ``("main", "MY_CONFIG")``.  Skipped when
       ``webpack_loader`` is not installed.
    2. Static file paths listed in ``GLOBAL_CSS`` - each resolved via
       Django's ``{% static %}`` tag.

    Returns an empty string when both lists are empty.
    """
    all_hrefs = [
        (url,) for url in get_bundle_urls(dds_settings.GLOBAL_CSS_BUNDLES, "css")
    ] + [(static(path),) for path in dds_settings.GLOBAL_CSS]
    if not all_hrefs:
        return ""
    return format_html_join("\n", '<link rel="stylesheet" href="{}">', all_hrefs)


@register.simple_tag
def global_scripts() -> str:
    """Render ``<script>`` tags for global JS bundles and static paths.

    Sources (in order):

    1. Webpack bundles listed in ``GLOBAL_JS_BUNDLES`` - each entry is a
       tuple of args for ``webpack_loader.utils.get_files``, e.g.
       ``("main",)`` or ``("main", "MY_CONFIG")``.  Skipped when
       ``webpack_loader`` is not installed.
    2. Static file paths listed in ``GLOBAL_JS`` - each resolved via
       Django's ``{% static %}`` tag.

    Returns an empty string when both lists are empty.
    """
    all_srcs = [
        (url,) for url in get_bundle_urls(dds_settings.GLOBAL_JS_BUNDLES, "js")
    ] + [(static(path),) for path in dds_settings.GLOBAL_JS]
    if not all_srcs:
        return ""
    return format_html_join("\n", '<script src="{}"></script>', all_srcs)
