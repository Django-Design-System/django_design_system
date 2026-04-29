from functools import wraps
from pathlib import Path

import markdown as markdown_lib
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.clickjacking import xframe_options_sameorigin

from dj_design_system.data import CanvasSpec
from dj_design_system.forms import build_component_form
from dj_design_system.services.canvas import (
    build_canvas_url,
    get_component_media,
    render_component,
    resolve_from_get_params,
)
from dj_design_system.services.markdown_canvas import CanvasExtension
from dj_design_system.services.media import (
    build_link_tags,
    build_script_tags,
)
from dj_design_system.services.navigation import (
    build_breadcrumbs,
    build_navigation,
    build_search_index,
    find_node,
    to_display_label,
)
from dj_design_system.services.registry import component_registry
from dj_design_system.services.tag_signature import (
    generate_current_tag_signature,
    generate_tag_signature,
)
from dj_design_system.settings import (
    dds_settings,
    get_backgrounds,
    get_default_background,
)
from dj_design_system.types import CanvasMode

GALLERY_PERMISSION = "dj_design_system.can_view_gallery"


def gallery_access_required(view_func):
    """Allow access if the gallery is public, otherwise require the permission."""

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if dds_settings.GALLERY_IS_PUBLIC:
            return view_func(request, *args, **kwargs)

        if not request.user.is_authenticated:
            url = f"{settings.LOGIN_URL}?next={request.path}"
            if not url_has_allowed_host_and_scheme(url, allowed_hosts=None):
                url = "/"
            return redirect(url)

        if not request.user.has_perm(GALLERY_PERMISSION):
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper


def get_base_context(
    active_app: str = "",
    active_path: str = "",
) -> dict:
    """Return context shared by all gallery views."""
    nav_tree = build_navigation()
    return {
        "nav_tree": nav_tree,
        "search_index": build_search_index(nav_tree),
        "design_system_name": dds_settings.DESIGN_SYSTEM_NAME,
        "active_app": active_app,
        "active_path": active_path,
    }


def _render_markdown(file_path: Path) -> str:
    """Render a markdown file to HTML.

    Fenced ``canvas`` blocks are replaced with live preview widgets.
    Standard fenced code blocks receive Pygments syntax highlighting.
    """
    content = file_path.read_text(encoding="utf-8")
    canvas_base_url = reverse("gallery-canvas-iframe")

    extensions: list = [
        CanvasExtension(
            canvas_base_url=canvas_base_url,
            debug=settings.DEBUG,
        ),
        "fenced_code",
        "tables",
        "toc",
    ]
    extension_configs: dict = {}
    style = dds_settings.GALLERY_CODEHILITE_STYLE
    if style:
        extensions.append("codehilite")
        extension_configs["codehilite"] = {
            "css_class": "gallery-highlight",
            "noclasses": False,
            "pygments_style": style,
        }
    return markdown_lib.markdown(
        content,
        extensions=extensions,
        extension_configs=extension_configs,
    )


# ---------------------------------------------------------------------------
# Rendering helpers (one per node type)
# ---------------------------------------------------------------------------


def _render_folder(request, context, node, app_label, path_parts):
    """Render a folder node — index.md if present, otherwise a listing."""
    context["node"] = node
    context["breadcrumbs"] = build_breadcrumbs(
        app_label, path_parts[:-1] if path_parts else [], node.label
    )

    if node.has_index_doc:
        context["doc_html"] = _render_markdown(node.index_doc_path)
        return render(
            request,
            "dj_design_system/gallery/documentation.html",
            context,
        )

    context["folder_label"] = node.label
    context["children"] = node.children
    context["is_debug"] = settings.DEBUG
    return render(
        request, "dj_design_system/gallery/folder.html", context
    )


def _render_component(request, context, node, app_label, path_parts):
    """Render a component node — Documentation pane + Sandbox pane.

    When the request contains GET parameters matching any of the component's
    parameter names, the form is bound and used to build the rendering kwargs.
    Valid cleaned data (excluding empty strings and None) overrides defaults.
    If the form is invalid the component falls back to defaults and errors are
    surfaced in the template via the bound form.
    """
    info = node.component
    component_class = info.component_class
    params = component_class.get_params()

    # Generate tag signature usage examples (includes CanvasSpecs).
    # Use the qualified name in CanvasSpecs so the canvas view can resolve
    # components unambiguously when multiple apps share the same short name.
    tag_signature = generate_tag_signature(
        component_class, canvas_component_name=info.qualified_name
    )

    # Build and optionally bind the parameter form.
    form_class = build_component_form(component_class)
    has_param_in_get = any(key in request.GET for key in form_class.base_fields)
    form = form_class(data=request.GET) if has_param_in_get else form_class()

    # Determine the active kwargs: from a valid form or fall back to maximal spec.
    if form.is_bound and form.is_valid():
        form_kwargs = {
            name: value
            for name, value in form.cleaned_data.items()
            if value is not None and value != ""
        }
        # Build a CanvasSpec from form values to drive the sandbox iframe.
        positional_args = component_class.get_positional_args()
        positional_values = tuple(
            form_kwargs.pop(name) for name in positional_args if name in form_kwargs
        )
        sandbox_spec = CanvasSpec(
            component_name=tag_signature.maximal_spec.component_name,
            params=form_kwargs,
            positional_args=positional_values,
        )
    else:
        form_kwargs = {}
        sandbox_spec = tag_signature.maximal_spec

    canvas_base_url = reverse("gallery-canvas-iframe")
    canvas_iframe_url = build_canvas_url(sandbox_spec, canvas_base_url)
    minimal_preview_url = (
        build_canvas_url(tag_signature.minimal_spec, canvas_base_url) + "&mode=basic"
    )
    maximal_preview_url = (
        build_canvas_url(tag_signature.maximal_spec, canvas_base_url) + "&mode=basic"
    )

    # Annotate params with type_name for the template.
    for spec_param in params.values():
        spec_param.type_name = getattr(spec_param, "type", type(spec_param)).__name__

    # Build param_rows: one dict per param with the bound form field included.
    param_rows = [
        {"name": name, "spec": spec_param, "field": form[name]}
        for name, spec_param in params.items()
    ]

    # BlockComponent subclasses expose a content field — prepend it to the rows
    # with a synthetic spec so the template can render it uniformly.
    from types import SimpleNamespace

    from dj_design_system.components import BlockComponent

    if issubclass(component_class, BlockComponent):
        content_spec = SimpleNamespace(
            description="Inner block content.",
            type_name="str",
            required=False,
            default=None,
            choices=[],
        )
        param_rows.insert(
            0, {"name": "content", "spec": content_spec, "field": form["content"]}
        )

    # Generate current-parameters usage example.
    # Keep non-default parameter values, and also pass block content so
    # the current-usage snippet reflects textarea edits.
    non_default_kwargs = {
        name: value
        for name, value in form_kwargs.items()
        if name != "content"
        and (params.get(name) is None or params[name].default != value)
    }
    signature_kwargs = dict(non_default_kwargs)
    if "content" in form_kwargs:
        signature_kwargs["content"] = form_kwargs["content"]

    current_signature = (
        generate_current_tag_signature(
            component_class, signature_kwargs, canvas_component_name=info.qualified_name
        )
        if form.is_bound and form.is_valid() and signature_kwargs
        else None
    )

    context["component_info"] = info
    context["component_description"] = markdown_lib.markdown(
        (component_class.__doc__ or "").strip(),
        extensions=["fenced_code", "tables"],
    )
    context["tag_signature"] = tag_signature
    context["current_signature"] = current_signature
    context["params"] = params
    context["param_rows"] = param_rows
    context["form"] = form
    context["canvas_iframe_url"] = canvas_iframe_url
    context["minimal_preview_url"] = minimal_preview_url
    context["maximal_preview_url"] = maximal_preview_url
    context["canvas_backgrounds"] = get_backgrounds()
    context["breadcrumbs"] = build_breadcrumbs(
        app_label,
        path_parts[:-1] if path_parts else [],
        to_display_label(info.name, component=info),
    )

    if node.has_index_doc:
        context["doc_html"] = _render_markdown(node.index_doc_path)

    if request.headers.get("HX-Request"):
        return render(
            request,
            "dj_design_system/gallery/sandbox_fragment.html",
            context,
        )

    return render(
        request, "dj_design_system/gallery/component.html", context
    )


def _render_document(request, context, node, app_label, path_parts):
    """Render a standalone markdown document."""
    context["doc_html"] = _render_markdown(node.doc_path)
    context["doc_label"] = node.label
    context["breadcrumbs"] = build_breadcrumbs(
        app_label, path_parts[:-1] if path_parts else [], node.label
    )
    return render(
        request, "dj_design_system/gallery/documentation.html", context
    )


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


@xframe_options_sameorigin
@gallery_access_required
def canvas_iframe_view(request: HttpRequest) -> HttpResponse:
    """Render a single component inside a full HTML document for iframe embedding.

    Loads global CSS, canvas-specific CSS, and the component's own CSS/JS in
    the correct cascade order.  Accepts component name and parameters via GET
    query parameters (parsed by ``resolve_from_get_params``).
    """
    context = {
        "rendered_html": "",
        "component_css": "",
        "component_js": "",
        "canvas_bg_class": _canvas_bg_class(request),
        "canvas_bg_styles": _canvas_bg_styles(),
        "canvas_mode_class": _canvas_mode_class(request),
        "html_attrs": "",
        "body_attrs": "",
    }
    try:
        spec = resolve_from_get_params(request.GET, component_registry)
    except ValueError as exc:
        html_attrs, body_attrs = _canvas_html_attrs()
        context["rendered_html"] = format_html(
            '<p style="color:red;">Canvas error: {}</p>', str(exc)
        )
        context["html_attrs"] = html_attrs
        context["body_attrs"] = body_attrs
        return render(
            request,
            "dj_design_system/canvas/iframe.html",
            context,
        )

    media = get_component_media(spec, component_registry)
    context["rendered_html"] = render_component(spec, component_registry)
    context["component_css"] = build_link_tags(media.css)
    context["component_js"] = build_script_tags(media.js)
    context["html_attrs"], context["body_attrs"] = _canvas_html_attrs()

    return render(
        request,
        "dj_design_system/canvas/iframe.html",
        context,
    )


def _canvas_bg_class(request: HttpRequest) -> str:
    """Return the CSS class for the canvas background from GET params or settings."""
    default = get_default_background()
    bg_param = request.GET.get("bg")
    if bg_param:
        for bg in get_backgrounds():
            if bg["value"] == bg_param:
                return f"canvas-bg-{bg['value']}"
    return f"canvas-bg-{default['value']}"


def _canvas_bg_styles() -> str:
    """Generate ``<style>`` CSS rules for all configured canvas backgrounds."""
    rules = []
    for bg in get_backgrounds():
        rules.append(f".canvas-bg-{bg['value']} {{ background: {bg['color']}; }}")
    return "<style>" + "\n".join(rules) + "</style>"


def _canvas_mode_class(request: HttpRequest) -> str:
    """Return the CSS class for the canvas mode from GET params."""
    mode_param = request.GET.get("mode")
    if mode_param:
        try:
            mode = CanvasMode(mode_param)
        except ValueError:
            mode = CanvasMode.EXTENDED
    else:
        mode = CanvasMode.EXTENDED
    return f"canvas-wrapper--{mode.value}"


def _flatten_attrs(attrs: dict[str, str]) -> str:
    """Convert a dict of HTML attributes to a safe attribute string.

    Returns a string with a leading space (e.g. ``' class="govuk-template"'``)
    or an empty string if *attrs* is empty.
    """
    if not attrs:
        return ""
    parts = format_html_join(" ", '{}="{}"', attrs.items())
    return format_html(" {}", parts)


def _canvas_html_attrs() -> tuple[str, str]:
    """Return ``(html_attrs, body_attrs)`` strings from settings."""
    raw = dds_settings.GALLERY_CANVAS_HTML_ATTRS
    return _flatten_attrs(raw.get("html", {})), _flatten_attrs(raw.get("body", {}))


@gallery_access_required
def gallery_index(request: HttpRequest) -> HttpResponse:
    """Gallery home — lists all registered components in the sidebar."""
    context = get_base_context()
    context["total_components"] = len(component_registry.list_all())
    return render(request, "dj_design_system/gallery/index.html", context)


@gallery_access_required
def gallery_node(
    request: HttpRequest,
    app_label: str,
    path: str = "",
) -> HttpResponse:
    """Unified view that dispatches to the correct renderer based on node type.

    The URL structure is simply::

        /                          → gallery index
        /<app_label>/              → app root (folder)
        /<app_label>/<path>/       → folder, component, or document

    The node type is determined by looking up the path in the navigation
    tree. This avoids the need for separate URL prefixes like ``/c/`` or
    ``/d/``.
    """
    path_parts = [p for p in path.split("/") if p]
    context = get_base_context(active_app=app_label)

    node = find_node(context["nav_tree"], app_label, path_parts)
    if node is None:
        raise Http404

    context["active_path"] = node.active_path

    if node.is_component:
        return _render_component(request, context, node, app_label, path_parts)

    if node.is_document:
        return _render_document(request, context, node, app_label, path_parts)

    # Default: folder (including APP nodes)
    return _render_folder(request, context, node, app_label, path_parts)
