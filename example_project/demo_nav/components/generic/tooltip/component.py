from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class TooltipComponent(TagComponent):
    """A hover tooltip.

    Lives in ``generic/tooltip/`` — the folder name matches the component
    name, so the gallery collapses this node.
    """

    template_format_str = "<span class='tooltip {classes}' title='{text}'>?</span>"
    text = StrParam("The tooltip text shown on hover.")

    class Meta:
        positional_args = ["text"]
