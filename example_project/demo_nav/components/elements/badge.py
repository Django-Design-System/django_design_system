from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class BadgeComponent(TagComponent):
    """A badge — lives directly in elements/ with no folder collapsing."""

    template_format_str = "<span class='badge {classes}'>{text}</span>"
    text = StrParam("The badge text.")

    class Meta:
        positional_args = ["text"]
