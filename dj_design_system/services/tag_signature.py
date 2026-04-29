"""
Generate template tag signature documentation for components.

This module provides utilities to auto-generate usage examples (minimal and maximal)
for template tags, using Meta.positional_args and parameter metadata.

Features:
- Auto-generate minimal and maximal usage examples with proper formatting
- Multi-line formatting for improved readability:
  * Block components: opening tag, content, closing tag on separate lines
  * Parameters: line breaks after each parameter for better readability
- Syntax highlighting using Pygments (graceful fallback to plain text if unavailable)
"""

from typing import Any, NamedTuple

from dj_design_system.components import BaseComponent, BlockComponent
from dj_design_system.data import BLOCK_CONTENT_PLACEHOLDER, CanvasSpec
from dj_design_system.parameters import (
    BoolCSSClassParam,
    BoolParam,
    StrCSSClassParam,
    StrParam,
)
from dj_design_system.services.component import derive_name


# Try to import Pygments for syntax highlighting
try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import DjangoLexer

    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False


class TagSignature(NamedTuple):
    """Container for minimal and maximal tag usage signatures."""

    minimal: str
    """Minimal usage: only required positional args (multi-line formatted)."""

    maximal: str
    """Maximal usage: positional args + optional params (multi-line formatted)."""

    minimal_html: str
    """Minimal usage with optional syntax highlighting (HTML)."""

    maximal_html: str
    """Maximal usage with optional syntax highlighting (HTML)."""

    minimal_spec: CanvasSpec
    """CanvasSpec matching the minimal example — same parameter values."""

    maximal_spec: CanvasSpec
    """CanvasSpec matching the maximal example — same parameter values."""


def _generate_example_value(
    param_spec: Any, param_name: str, str_example_index: int = 0
) -> Any:
    """Generate a representative example value for a parameter.

    Args:
        param_spec: A BaseParam descriptor
        param_name: The parameter name
        str_example_index: Index for cycling through string examples (foo, bar, baz)

    Returns:
        An example value appropriate for the parameter type
    """
    # Use default if available
    if param_spec.default is not None:
        return param_spec.default

    # Use first choice if available
    if hasattr(param_spec, "choices") and param_spec.choices:
        return param_spec.choices[0]

    # Generate type-specific defaults
    if isinstance(param_spec, BoolParam):
        return True
    if isinstance(param_spec, (StrParam, StrCSSClassParam)):
        # Cycle through foo, bar, baz for string examples
        examples = ["foo", "bar", "baz"]
        return examples[str_example_index % len(examples)]
    if isinstance(param_spec, BoolCSSClassParam):
        return True

    # Fallback for custom param types
    return None


def _format_param_for_tag(param_name: str, value: Any) -> str:
    """Format a parameter and value for template tag syntax.

    Args:
        param_name: The parameter name
        value: The parameter value

    Returns:
        String in format 'param_name=value'
    """
    if isinstance(value, bool):
        # Template tag booleans are rendered as 'param_name=True' or 'param_name=False'
        value_str = str(value)
    elif isinstance(value, str):
        # String values in template tags use double quotes
        value_str = f'"{value}"'
    else:
        value_str = str(value)

    return f"{param_name}={value_str}"


def _format_positional_arg(value: Any) -> str:
    """Format a positional argument value (without parameter name).

    Args:
        value: The argument value

    Returns:
        String representation of the value
    """
    if isinstance(value, bool):
        return str(value)
    elif isinstance(value, str):
        return f'"{value}"'
    else:
        return str(value)


def _split_tag_params(params_str: str) -> list[str]:
    """Split a template tag parameter string, respecting quoted values.

    Handles ``key="value with spaces"`` correctly by tracking quote state.

    Args:
        params_str: The raw parameter portion of a tag (after the tag name).

    Returns:
        A list of individual parameter tokens.
    """
    result: list[str] = []
    current = ""
    in_quotes = False
    for char in params_str:
        if char == '"':
            in_quotes = not in_quotes
        if char == " " and not in_quotes:
            if current:
                result.append(current)
            current = ""
        else:
            current += char
    if current:
        result.append(current)
    return result


def _format_multiline_example(
    example_str: str, is_block: bool, component_name: str
) -> str:
    """Format a tag example string into a multi-line, readable format.

    For tag components: wraps long parameter lists with line breaks
    For block components: puts opening tag, content, closing tag on separate lines

    Args:
        example_str: The single-line tag example (e.g., '{% icon "foo" %}')
        is_block: Whether this is a block component
        component_name: The component name

    Returns:
        A formatted, multi-line string
    """
    if not is_block:
        # For tag components: {% component arg1="val" arg2="val" %}
        # Extract opening/closing and parameters
        if not example_str.startswith("{%"):
            return example_str

        # Remove {% and %}
        inner = example_str[2:-2].strip()
        parts = inner.split(None, 1)  # Split on first whitespace

        if len(parts) == 1:
            # No parameters, keep one line
            return example_str

        component = parts[0]
        params = parts[1]

        param_list = _split_tag_params(params)

        # If only one or two params, keep on one line; otherwise break them up
        if len(param_list) <= 2:
            return example_str

        # Multi-line format with indentation
        formatted = f"{{% {component}\n"
        for i, param in enumerate(param_list):
            formatted += f"  {param}"
            if i < len(param_list) - 1:
                formatted += "\n"
        formatted += "\n%}"
        return formatted

    else:
        # For block components: {% component ... %}...content...{% endcomponent %}
        # Extract opening, content, closing
        opening_match = example_str.split("}")[0] + "}"
        rest = example_str[len(opening_match) :]

        # Find the closing tag
        closing_start = rest.rfind("{%")
        if closing_start == -1:
            return example_str

        content = rest[:closing_start].strip()

        # Extract opening tag content
        inner = opening_match[2:-2].strip()
        parts = inner.split(None, 1)

        if len(parts) == 1:
            # No parameters - keep on single line
            formatted = f"{{% {component_name} %}}{content}{{% end{component_name} %}}"
        else:
            component = parts[0]
            params = parts[1]

            param_list = _split_tag_params(params)

            # Format with line breaks only if multiple parameters (more than 1)
            if len(param_list) <= 1:
                formatted = f"{{% {component} {' '.join(param_list)} %}}\n{content}\n{{% end{component_name} %}}"
            else:
                formatted = f"{{% {component}\n"
                for i, param in enumerate(param_list):
                    formatted += f"  {param}"
                    if i < len(param_list) - 1:
                        formatted += "\n"
                formatted += f"\n%}}\n{content}\n{{% end{component_name} %}}"

        return formatted


def highlight_code(code: str) -> str:
    """Apply syntax highlighting to Django template code using Pygments.

    Args:
        code: The code string to highlight

    Returns:
        HTML with span tags for syntax highlighting (no pre/code wrapper),
        or empty string if Pygments unavailable
    """
    if not HAS_PYGMENTS:
        return ""

    try:
        # Use HtmlFormatter with CSS classes and pre/code wrapper
        fmt = HtmlFormatter(style="monokai", noclasses=False, nowrap=True)
        # nowrap=True returns just inline spans without wrapping div/pre/code
        highlighted = highlight(code, DjangoLexer(), fmt)
        return highlighted
    except (ValueError, TypeError):
        # If highlighting fails, return empty string to fall back to plain text
        return ""


def generate_current_tag_signature(
    component_class: type[BaseComponent],
    kwargs: dict[str, Any],
    canvas_component_name: str | None = None,
) -> TagSignature:
    """Generate a tag usage signature reflecting the currently-active parameter values.

    This is used on the gallery component page to show a copyable usage example
    that matches whatever values the developer has entered into the parameter form.
    Only parameters present in ``kwargs`` are included; parameters with no value
    are omitted. For block components, ``kwargs["content"]`` is rendered as the
    inner block body when present; otherwise ``BLOCK_CONTENT_PLACEHOLDER`` is used.

    Args:
        component_class: A BaseComponent subclass (TagComponent or BlockComponent)
        kwargs: The active parameter values (e.g. from form cleaned_data)

    Returns:
        A TagSignature whose ``minimal`` / ``maximal`` fields both hold the current
        example (plain text) and ``minimal_html`` / ``maximal_html`` hold the
        syntax-highlighted HTML equivalent.
    """
    component_name = derive_name(component_class)
    positional_args = component_class.get_positional_args()
    is_block = issubclass(component_class, BlockComponent)

    # Build positional args from kwargs (in declared order)
    positional = [
        _format_positional_arg(kwargs[name])
        for name in positional_args
        if name in kwargs
    ]

    # Build keyword args for non-positional params that have a value
    keyword = [
        _format_param_for_tag(name, value)
        for name, value in kwargs.items()
        if name not in positional_args and (not is_block or name != "content")
    ]

    all_args = positional + keyword
    args_str = " ".join(all_args)

    if is_block:
        opening = f"{{% {component_name}"
        if args_str:
            opening += f" {args_str}"
        opening += " %}"
        content = kwargs.get("content") or BLOCK_CONTENT_PLACEHOLDER
        raw = f"{opening}{content}{{% end{component_name} %}}"
    else:
        opening = f"{{% {component_name}"
        if args_str:
            opening += f" {args_str}"
        opening += " %}"
        raw = opening

    formatted = _format_multiline_example(raw, is_block, component_name)
    highlighted = highlight_code(formatted)

    # Build a CanvasSpec so the current signature can drive the sandbox iframe.
    positional_values = tuple(
        kwargs[name] for name in positional_args if name in kwargs
    )
    keyword_values = {
        name: value for name, value in kwargs.items() if name not in positional_args
    }
    spec = CanvasSpec(
        component_name=canvas_component_name or component_name,
        params=keyword_values,
        positional_args=positional_values,
    )

    return TagSignature(
        minimal=formatted,
        maximal=formatted,
        minimal_html=highlighted,
        maximal_html=highlighted,
        minimal_spec=spec,
        maximal_spec=spec,
    )


def generate_tag_signature(
    component_class: type[BaseComponent],
    canvas_component_name: str | None = None,
) -> TagSignature:
    """Generate minimal and maximal usage signatures for a component.

    Args:
        component_class: A BaseComponent subclass (TagComponent or BlockComponent)

    Returns:
        TagSignature with minimal and maximal usage strings (both plain and HTML)

    Example:
        >>> from dw_design_system.components.icon import IconComponent
        >>> sig = generate_tag_signature(IconComponent)
        >>> print(sig.minimal)
        {% icon "foo" %}
    """
    component_name = derive_name(component_class)
    params = component_class.get_params()
    positional_args = component_class.get_positional_args()

    is_block = issubclass(component_class, BlockComponent)

    # ─────────────────────────────────────────────────────────────────────────
    # Build minimal usage (required params only, using positional args)
    # ─────────────────────────────────────────────────────────────────────────

    minimal_positional = []
    minimal_positional_values = []
    minimal_keyword_values: dict[str, object] = {}
    str_index = 0  # Track string example cycling
    for arg_name in positional_args:
        if arg_name in params:
            spec = params[arg_name]
            if spec.required:
                value = _generate_example_value(spec, arg_name, str_index)
                if isinstance(spec, (StrParam, StrCSSClassParam)):
                    str_index += 1
                minimal_positional.append(_format_positional_arg(value))
                minimal_positional_values.append(value)

    if is_block:
        opening = f"{{% {component_name} {' '.join(minimal_positional)}".strip()
        opening += " %}"
        minimal_raw = f"{opening}{BLOCK_CONTENT_PLACEHOLDER}{{% end{component_name} %}}"
    else:
        # Tag: {% component_name positional_args %}
        opening = f"{{% {component_name} {' '.join(minimal_positional)}".strip()
        opening += " %}"
        minimal_raw = opening

    minimal = _format_multiline_example(minimal_raw, is_block, component_name)

    # ─────────────────────────────────────────────────────────────────────────
    # Build maximal usage (all params that work, using positional args where possible)
    # ─────────────────────────────────────────────────────────────────────────

    maximal_positional = []
    maximal_positional_values = []
    maximal_keyword = []
    maximal_keyword_values = {}
    str_index = 0  # Reset counter for maximal signature

    # First, add all positional args in order
    for arg_name in positional_args:
        if arg_name in params:
            spec = params[arg_name]
            value = _generate_example_value(spec, arg_name, str_index)
            if isinstance(spec, (StrParam, StrCSSClassParam)):
                str_index += 1
            if value is not None:
                maximal_positional.append(_format_positional_arg(value))
                maximal_positional_values.append(value)

    # Then, add optional (non-positional) params as keyword args
    for param_name, spec in params.items():
        # Skip positional args (already handled)
        if param_name in positional_args:
            continue

        # Only include optional params or those with defaults
        if not spec.required or spec.default is not None:
            value = _generate_example_value(spec, param_name, str_index)
            if isinstance(spec, (StrParam, StrCSSClassParam)):
                str_index += 1
            if value is not None:
                maximal_keyword.append(_format_param_for_tag(param_name, value))
                maximal_keyword_values[param_name] = value
    # Combine positional and keyword args
    all_args = maximal_positional + maximal_keyword
    args_str = " ".join(all_args)

    if is_block:
        opening = f"{{% {component_name}"
        if args_str:
            opening += f" {args_str}"
        opening += " %}"
        maximal_raw = f"{opening}{BLOCK_CONTENT_PLACEHOLDER}{{% end{component_name} %}}"
    else:
        # Tag: {% component_name args %}
        opening = f"{{% {component_name}"
        if args_str:
            opening += f" {args_str}"
        opening += " %}"
        maximal_raw = opening

    maximal = _format_multiline_example(maximal_raw, is_block, component_name)

    # ─────────────────────────────────────────────────────────────────────────
    # Generate HTML versions with syntax highlighting
    # ─────────────────────────────────────────────────────────────────────────

    minimal_html = highlight_code(minimal)
    maximal_html = highlight_code(maximal)

    # ─────────────────────────────────────────────────────────────────────────
    # Build CanvasSpecs from the exact same values used for code generation
    # ─────────────────────────────────────────────────────────────────────────

    canvas_name = canvas_component_name or component_name
    minimal_spec = CanvasSpec(
        component_name=canvas_name,
        params=minimal_keyword_values,
        positional_args=tuple(minimal_positional_values),
    )
    maximal_spec = CanvasSpec(
        component_name=canvas_name,
        params=maximal_keyword_values,
        positional_args=tuple(maximal_positional_values),
    )

    return TagSignature(
        minimal=minimal,
        maximal=maximal,
        minimal_html=minimal_html,
        maximal_html=maximal_html,
        minimal_spec=minimal_spec,
        maximal_spec=maximal_spec,
    )
