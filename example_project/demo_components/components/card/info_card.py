from dj_design_system.parameters import BoolParam, StrParam
from example_project.demo_components.components.card.abstract_card import (
    AbstractCardComponent,
)


class InfoCardComponent(AbstractCardComponent):
    """A simple informational card with a title, body text, and optional footer.

    Demonstrates:
    - Inheriting from an abstract component
    - ``BoolParam`` for a toggle flag
    - A nested subfolder layout (``components/card/``)

    Example usage::

        {% info_card "Getting started" "Read the quickstart guide." %}
        {% info_card "Tips" "Use keyword args for clarity." show_footer=True %}
    """

    template_format_str = (
        "<div class='card {classes}'>"
        "<h3 class='card__title'>{title}</h3>"
        "<p class='card__body'>{body}</p>"
        "</div>"
    )
    title = StrParam("The card heading.")
    body = StrParam("The card body text.")
    show_footer = BoolParam("Show a decorative footer rule.", required=False)

    class Meta:
        positional_args = ["title", "body"]
