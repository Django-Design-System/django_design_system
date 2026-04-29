from dj_design_system.components import TagComponent


class AbstractCardComponent(TagComponent):
    """Abstract base for all card components.

    Demonstrates ``Meta.abstract = True`` — this class is excluded from
    autodiscovery and will not appear in the gallery.
    """

    class Meta:
        abstract = True
