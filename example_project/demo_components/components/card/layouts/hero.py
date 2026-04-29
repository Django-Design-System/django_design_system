from dj_design_system.components import TagComponent


class HeroCardComponent(TagComponent):
    """A full-width hero card with a custom registered name.

    Demonstrates ``Meta.name`` — this component is registered as ``hero``
    rather than the auto-derived ``hero_card``. Also demonstrates a
    deeply-nested layout (``components/card/layouts/``).

    Example usage::

        {% hero %}
    """

    template_format_str = "<div class='hero-card {classes}'>Hero</div>"

    class Meta:
        name = "hero"
