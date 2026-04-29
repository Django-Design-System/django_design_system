from typing import Any

from dj_design_system.parameters.base import BaseParam


class FieldParam(BaseParam):
    """
    Accepts a pre-rendered Django BoundField (or any HTML-renderable object).

    Duck-typed: the value must expose an ``__html__`` method so it can be safely
    embedded in HTML output.  Mutually exclusive with the ``field_*`` attribute
    params and ``autocomplete_url`` — see ``SearchFieldComponent.validate_params``.
    """

    type = object

    def validate(self, value: Any) -> None:
        """Raise ValueError if value is not HTML-renderable."""
        if value is not None and not hasattr(value, "__html__"):
            raise ValueError(
                f"'field' must be an HTML-renderable object (with __html__), "
                f"got {type(value).__name__}."
            )

    def docstring(self) -> str:
        name = self.name
        desc = " - " + self.description if self.description else ""
        return f"{name}: Optional[HTML-renderable]{desc}"
