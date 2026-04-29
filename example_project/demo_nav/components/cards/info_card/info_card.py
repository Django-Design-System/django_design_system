from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class InfoCardComponent(TagComponent):
    """An info card — lives in ``cards/info_card/`` and collapses to ``cards/info_card``."""

    template_format_str = "<div class='card card--info {classes}'><p>{body}</p></div>"
    body = StrParam("The card body text.")

    class Meta:
        positional_args = ["body"]
