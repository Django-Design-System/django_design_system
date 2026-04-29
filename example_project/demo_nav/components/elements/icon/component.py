from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam


class IconComponent(TagComponent):
    """An SVG icon referenced by name.

    Lives in ``elements/icon/`` — the folder name matches the component name,
    so the gallery collapses this node (the icon folder doesn't appear as a
    separate folder entry).
    """

    template_format_str = (
        "<span class='icon icon-{name} {classes}' aria-hidden='true'></span>"
    )
    name = StrParam("The icon identifier (e.g. 'arrow-right', 'close').")

    class Meta:
        positional_args = ["name"]
