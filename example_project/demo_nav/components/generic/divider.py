from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class DividerComponent(TagComponent):
    """A horizontal rule, optionally labelled.

    Lives directly in ``generic/`` — demonstrates a flat component inside
    a folder that also contains sub-folders.
    """

    template_format_str = "<hr class='divider {classes}' data-label='{label}' />"
    label = StrParam("Optional divider label.", required=False, default="")
