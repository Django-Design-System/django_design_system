from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class ButtonComponent(TagComponent):
    """A button from the second app — same component name as demo_components.

    This app exists to demonstrate multi-app registration: two apps can both
    define a ``button`` component. The gallery shows them under their
    respective app labels, and the template tag requires the app-qualified
    form ``{% demo_extra:button "Click me" %}`` to resolve ambiguity.

    Example usage::

        {% demo_extra:button "Click me" %}
    """

    template_format_str = "<button class='btn-extra {classes}'>{label}</button>"
    label = StrParam("The button label.")

    class Meta:
        positional_args = ["label"]
