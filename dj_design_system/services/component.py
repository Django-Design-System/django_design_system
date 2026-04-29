import re
from typing import Type


class EmptyMeta:
    """Sentinel returned by ``get_own_meta`` when a class has no own Meta.

    Allows callers to use ``getattr`` unconditionally, without a None check.
    """


def get_own_meta(cls: Type) -> type:
    """Return the Meta inner class defined directly on ``cls``.

    Only looks at the class's own ``__dict__``, not inherited Meta from
    parent classes - matching Django's convention where Meta is not
    inherited. Returns ``EmptyMeta`` if the class has no own Meta.
    """
    return cls.__dict__.get("Meta", EmptyMeta)


def is_abstract(cls: Type) -> bool:
    """Return True if the class's own Meta marks it as abstract."""
    return getattr(get_own_meta(cls), "abstract", False)


def get_meta_name(cls: Type) -> str | None:
    """Return the explicit name from the class's own Meta, if provided."""
    name = getattr(get_own_meta(cls), "name", None)
    return name if isinstance(name, str) else None


def derive_name(cls: Type) -> str:
    """
    Derive a component name from a class name by stripping a trailing
    'Component' suffix and converting to snake_case.

    Examples:
        IconComponent -> "icon"
        MyFancyButton -> "my_fancy_button"
        HeroCardComponent -> "hero_card"
        Component -> "component"  (no stripping when it's the entire name)
    """
    COMPONENT_SUFFIX = "Component"
    class_name = cls.__name__

    # Strip trailing "Component" if it's not the entire name
    if class_name.endswith(COMPONENT_SUFFIX) and class_name != COMPONENT_SUFFIX:
        class_name = class_name[: -len(COMPONENT_SUFFIX)]

    # CamelCase to snake_case
    name = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", class_name)
    name = re.sub(r"(?<=[A-Z])([A-Z][a-z])", r"_\1", name)
    return name.lower()


def derive_relative_path(modname: str, components_module_path: str) -> str:
    """
    Derive the dotted directory path relative to the ``components`` package.

    For example, given:
        modname = "myapp.components.buttons.primary"
        components_module_path = "myapp.components"
    Returns ``"buttons"`` (the directory containing ``primary.py``,
    excluding the module file name itself).
    """
    suffix = modname[len(components_module_path) + 1 :]
    parts = suffix.split(".")
    return ".".join(parts[:-1])  # drop the module filename, keep directories
