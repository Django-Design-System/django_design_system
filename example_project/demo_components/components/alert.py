from dj_design_system.components import BlockComponent
from dj_design_system.parameters import StrCSSClassParam


class AlertComponent(BlockComponent):
    """A dismissable alert banner that wraps arbitrary content.

    Demonstrates a ``BlockComponent`` with a ``StrCSSClassParam`` — the
    ``level`` value is injected as a CSS modifier class automatically.

    Example usage::

        {% alert "warning" %}
            Your session will expire in 5 minutes.
        {% endalert %}
    """

    template_format_str = (
        "<div class='alert alert-{level} {classes}' role='alert'>{content}</div>"
    )
    level = StrCSSClassParam(
        "Severity level — controls the colour scheme.",
        default="info",
        choices=["info", "success", "warning", "error"],
    )

    class Meta:
        positional_args = ["level"]
