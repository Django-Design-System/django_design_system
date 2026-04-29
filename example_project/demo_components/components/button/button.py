from dj_design_system.components import TagComponent
from dj_design_system.parameters import (
    BoolCSSClassParam,
    StrCSSClassParam,
    StrParam,
)


class ButtonComponent(TagComponent):
    """A configurable button with size and variant modifiers.

    Demonstrates:
    - ``StrParam`` with positional args
    - ``StrCSSClassParam`` — value injected as a CSS modifier class
    - ``BoolCSSClassParam`` — adds a CSS class when truthy
    - Co-located CSS file (``button.css``) discovered automatically

    Example usage::

        {% button "Save changes" %}
        {% button "Delete" variant="danger" disabled=True %}
    """

    template_format_str = "<button class='btn {classes}'>{label}</button>"
    label = StrParam("The button label.")
    variant = StrCSSClassParam(
        "Visual variant.",
        required=False,
        default="primary",
        choices=["primary", "secondary", "danger"],
    )
    disabled = BoolCSSClassParam("Renders the button as disabled.", required=False)

    class Meta:
        positional_args = ["label"]

    def get_template_context(self, **kwargs):
        ctx = super().get_template_context(**kwargs)
        ctx["disabled_attr"] = "disabled" if self.disabled else ""
        return ctx
