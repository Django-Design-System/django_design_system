from dj_design_system.components import BlockComponent
from dj_design_system.parameters import StrCSSClassParam, StrParam
from dj_design_system.slots import Slot


class SlottedCardComponent(BlockComponent):
    """A card with named slots for header, body, and footer areas.

    Demonstrates the named slots feature — a ``BlockComponent`` with
    ``Meta.slots`` declaring multiple content areas that template authors
    fill using ``{% slot "name" %}...{% endslot %}``.

    The ``body`` slot is required; ``header`` and ``footer`` are optional
    and will be omitted from the output when not provided.

    Example usage::

        {% slotted_card title="Welcome" %}
            {% slot "header" %}
                <img src="banner.jpg" alt="Banner">
            {% endslot %}
            {% slot "body" %}
                <p>Main card content goes here.</p>
            {% endslot %}
            {% slot "footer" %}
                <button>Save</button>
            {% endslot %}
        {% endslotted_card %}

    Minimal usage (only required slot)::

        {% slotted_card %}
            {% slot "body" %}
                <p>Just the body.</p>
            {% endslot %}
        {% endslotted_card %}
    """

    title = StrParam("Optional card title displayed above the body.", required=False)
    variant = StrCSSClassParam(
        "Visual variant.",
        required=False,
        default="default",
        choices=["default", "outlined", "elevated"],
    )

    class Meta:
        slots = {
            "body": Slot(required=True, description="Main card content."),
            "header": Slot(required=False, description="Optional header area above the title."),
            "footer": Slot(required=False, description="Optional footer area below the body."),
        }
        positional_args = ["title"]

    def render(self) -> str:
        classes = self.get_classes_string()

        header = (
            f"<div class='slotted-card__header'>{self.slots['header']}</div>"
            if self.slots.get("header")
            else ""
        )
        title = (
            f"<h3 class='slotted-card__title'>{self.title}</h3>"
            if self.title
            else ""
        )
        footer = (
            f"<div class='slotted-card__footer'>{self.slots['footer']}</div>"
            if self.slots.get("footer")
            else ""
        )

        return (
            f"<div class='slotted-card {classes}'>"
            f"{header}"
            f"{title}"
            f"<div class='slotted-card__body'>{self.slots['body']}</div>"
            f"{footer}"
            f"</div>"
        )
