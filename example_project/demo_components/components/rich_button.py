from dj_design_system.components import TagComponent
from dj_design_system.parameters import BoolParam, StrParam


class RichButtonComponent(TagComponent):
    """A button that declares an explicit ``Media`` class alongside a co-located CSS file.

    Demonstrates that auto-discovered media (the ``rich_button.css`` file next
    to this module) and explicitly declared ``Media.css`` entries are merged
    rather than one suppressing the other.

    Example usage::

        {% rich_button "Submit form" %}
        {% rich_button "Cancel" ghost=True %}
    """

    template_format_str = "<button class='rich-btn {classes}'>{label}</button>"
    label = StrParam("The button label.")
    ghost = BoolParam("Renders as a ghost (outline-only) button.", required=False)

    class Meta:
        positional_args = ["label"]

    class Media:
        css = ["demo_components/components/rich_button_extras.css"]
