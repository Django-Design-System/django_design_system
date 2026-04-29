from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class BadgeComponent(TagComponent):
    """A small badge label, useful for status indicators or counts.

    The simplest structural pattern: a single file with an inline template.

    Example usage::

        {% badge "New" %}
    """

    template_format_str = "<span class='badge {classes}'>{text}</span>"
    text = StrParam("The badge text.")

    class Meta:
        positional_args = ["text"]
