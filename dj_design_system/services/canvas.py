"""Canvas rendering service — resolves component specifications and renders them.

All functions are stateless and operate on a ``ComponentRegistry`` passed as an
argument (defaulting to the global singleton).  The module follows the same
pure-function pattern used by ``services/component.py`` and ``services/media.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.utils.html import format_html

from dj_design_system.components import BlockComponent
from dj_design_system.data import (
    BLOCK_CONTENT_PLACEHOLDER,
    CanvasSpec,
    ComponentMedia,
)
from dj_design_system.services.registry import (
    ComponentDoesNotExist,
    MultipleComponentsFound,
)


if TYPE_CHECKING:
    from django.http import QueryDict

    from dj_design_system.services.registry import ComponentRegistry


def resolve_from_get_params(
    query_dict: QueryDict,
    registry: ComponentRegistry,
) -> CanvasSpec:
    """Build a ``CanvasSpec`` from an HTTP request's GET parameters.

    Expects a ``component`` key identifying the component by name. All other
    query parameters are treated as keyword arguments for the component.
    Type coercion is applied based on the component's parameter specs:
    string GET values are converted to ``bool`` or ``int`` where the parameter
    descriptor declares that type.

    Light validation only — checks that parameter names exist on the component
    and that types can be coerced. Full validation is deferred to the component
    ``__init__``.

    Raises ``ValueError`` with a descriptive message on resolution failure.
    """
    component_name = query_dict.get("component", "").strip()
    if not component_name:
        raise ValueError("Missing required 'component' query parameter.")

    info = _resolve_component(component_name, registry)
    param_specs = info.component_class.get_params()
    positional_arg_names = info.component_class.get_positional_args()

    raw_params = {k: v for k, v in query_dict.items() if k not in ("component", "bg")}

    positional_args, params = _coerce_params(
        raw_params, param_specs, positional_arg_names
    )

    # BlockComponent subclasses require a ``content`` argument that is not a
    # declared param — pass it through directly if provided.

    if issubclass(info.component_class, BlockComponent) and "content" in raw_params:
        params["content"] = raw_params["content"]

    return CanvasSpec(
        component_name=component_name,
        params=params,
        positional_args=positional_args,
    )


def render_component(
    spec: CanvasSpec,
    registry: ComponentRegistry,
) -> str:
    """Instantiate a component from a ``CanvasSpec`` and return rendered HTML.

    On success, returns the component's rendered HTML string. On failure,
    returns a red error ``<p>`` tag with the exception message (matching the
    existing gallery error-display pattern).
    """
    try:
        info = _resolve_component(spec.component_name, registry)
        component_class = info.component_class
        positional_arg_names = component_class.get_positional_args()

        kwargs = dict(spec.params)
        component_class.map_positional_args(
            positional_arg_names, spec.positional_args, kwargs
        )

        # BlockComponent subclasses require a `content` first argument.
        from dj_design_system.components import BlockComponent

        if issubclass(component_class, BlockComponent):
            content = kwargs.pop("content", BLOCK_CONTENT_PLACEHOLDER)
            return str(component_class(content=content, **kwargs))

        return str(component_class(**kwargs))
    except (ValueError, TypeError, KeyError) as exc:
        return format_html('<p style="color:red;">Could not render: {}</p>', str(exc))


def get_component_media(
    spec: CanvasSpec,
    registry: ComponentRegistry,
) -> ComponentMedia:
    """Return the CSS and JS media for a specific component.

    Returns an empty ``ComponentMedia`` if the component cannot be resolved.
    """
    try:
        info = _resolve_component(spec.component_name, registry)
        return info.media
    except ValueError:
        return ComponentMedia()


def build_canvas_url(
    spec: CanvasSpec,
    base_url: str,
    registry: ComponentRegistry | None = None,
) -> str:
    """Build a URL for the canvas iframe view from a ``CanvasSpec``.

    The URL encodes the component name and all parameters as GET query
    parameters suitable for ``resolve_from_get_params`` on the receiving end.

    When *registry* is given, positional arg names are resolved from it.
    Otherwise falls back to the global ``component_registry`` singleton.
    """
    query = {"component": spec.component_name}

    positional_arg_names: list[str] = []
    try:
        if registry is None:
            from dj_design_system.services.registry import component_registry

            registry = component_registry
        info = _resolve_component(spec.component_name, registry)
        positional_arg_names = info.component_class.get_positional_args()
    except (ValueError, ImportError):
        pass  # Graceful fallback — positional args won't be named in URL

    # Positional args → named params for the URL
    for i, value in enumerate(spec.positional_args):
        if i < len(positional_arg_names):
            query[positional_arg_names[i]] = _serialise_value(value)

    for key, value in spec.params.items():
        query[key] = _serialise_value(value)

    return f"{base_url}?{urlencode(query)}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_component(name: str, registry: ComponentRegistry):
    """Look up a component by name, raising ``ValueError`` on failure.

    Supports qualified names in the form ``app_label__name`` or
    ``app_label__relative_path__name`` to disambiguate components that share
    the same short name across multiple apps.
    """
    try:
        if "__" in name:
            parts = name.split("__")
            return registry.get_by_name(parts[-1], app_label=parts[0])
        return registry.get_by_name(name)
    except ComponentDoesNotExist:
        raise ValueError(f"Component '{name}' not found in registry.")
    except MultipleComponentsFound:
        raise ValueError(
            f"Component '{name}' is ambiguous — found in multiple apps. "
            f"Use the fully qualified name."
        )


def _coerce_params(
    raw_params: dict[str, str],
    param_specs: dict,
    positional_arg_names: list[str],
) -> tuple[tuple, dict]:
    """Coerce string GET values to the types declared by param specs.

    Returns a ``(positional_args, keyword_params)`` tuple.
    """
    positional_args: list = []
    keyword_params: dict = {}

    for key, raw_value in raw_params.items():
        if key not in param_specs:
            continue  # Silently ignore unknown params

        spec = param_specs[key]
        coerced = coerce_single(key, raw_value, spec)

        if key in positional_arg_names:
            positional_args.append(coerced)
        else:
            keyword_params[key] = coerced

    return tuple(positional_args), keyword_params


def coerce_single(key: str, raw_value: str, spec) -> object:
    """Coerce a single string value to the type declared by a parameter spec."""
    expected_type = getattr(spec, "type", str)

    if expected_type is bool:
        return raw_value.lower() in ("true", "1", "yes")
    if expected_type is int:
        try:
            return int(raw_value)
        except (ValueError, TypeError):
            raise ValueError(f"Parameter '{key}': expected int, got '{raw_value}'.")

    return raw_value


def _serialise_value(value: object) -> str:
    """Convert a parameter value to a string suitable for URL encoding."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
