"""Single-file components module — the simplest possible registration pattern.

All components for this app live in this one file rather than a ``components/``
package. This is useful for small apps with only a handful of components.
"""

from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class PillComponent(TagComponent):
    """A pill-shaped label, typically used for tags or categories.

    Demonstrates the single-file ``components.py`` discovery pattern: define
    all components for an app in one file instead of a ``components/`` package.

    Example usage::

        {% pill "Python" %}
        {% pill "Django" %}
    """

    template_format_str = "<span class='pill {classes}'>{text}</span>"
    text = StrParam("The pill text.")

    class Meta:
        positional_args = ["text"]


class ChipComponent(TagComponent):
    """A compact chip label, similar to a pill but smaller.

    Example usage::

        {% chip "v1.0" %}
    """

    template_format_str = "<span class='chip {classes}'>{text}</span>"
    text = StrParam("The chip text.")

    class Meta:
        positional_args = ["text"]
