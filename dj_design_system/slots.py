"""Named slot support for BlockComponent.

A slot defines a named content area that template authors fill using
``{% slot "name" %}...{% endslot %}`` tags inside a block component.
"""

from __future__ import annotations

from django.template import TemplateSyntaxError


class Slot:
    """Declaration of a named content slot on a BlockComponent.

    Args:
        required: Whether the slot must be provided. Defaults to False.
        default: Default content when the slot is not provided. Only
            meaningful when ``required=False``.
        description: Human-readable description for documentation/gallery.
    """

    def __init__(
        self,
        required: bool = False,
        default: str = "",
        description: str = "",
    ) -> None:
        self.required = required
        self.default = default
        self.description = description

    def __repr__(self) -> str:
        return (
            f"Slot(required={self.required!r}, "
            f"default={self.default!r}, "
            f"description={self.description!r})"
        )


def validate_slots(
    declared_slots: dict[str, Slot],
    provided_slots: dict[str, str],
    component_name: str,
) -> dict[str, str]:
    """Validate provided slots against a component's declared slots.

    Returns a complete dict of slot values (filling in defaults for
    missing optional slots).

    Raises:
        TemplateSyntaxError: If a required slot is missing, an unknown
            slot name is used, or a slot name appears more than once.
    """
    # Check for unknown slot names
    unknown = set(provided_slots) - set(declared_slots)
    if unknown:
        names = ", ".join(sorted(unknown))
        valid = ", ".join(sorted(declared_slots))
        raise TemplateSyntaxError(
            f"'{component_name}' received unknown slot(s): {names}. "
            f"Valid slots are: {valid}."
        )

    # Build result with defaults for missing optional slots
    result: dict[str, str] = {}
    for name, slot in declared_slots.items():
        if name in provided_slots:
            result[name] = provided_slots[name]
        elif slot.required:
            valid = ", ".join(sorted(declared_slots))
            raise TemplateSyntaxError(
                f"'{component_name}' requires slot '{name}' but it was not provided. "
                f"Declared slots: {valid}."
            )
        else:
            result[name] = slot.default

    return result
