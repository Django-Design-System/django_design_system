from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class ButtonComponent(TagComponent):
    """A simple button at the root level of the demo_nav app.

    Sits at the top level of the components folder to show how root-level
    components appear directly under the app node in the gallery sidebar.
    """

    template_format_str = "<button class='btn {classes}'>{label}</button>"
    label = StrParam("The button label.")

    class Meta:
        positional_args = ["label"]
        verbose_name = "Action button"
