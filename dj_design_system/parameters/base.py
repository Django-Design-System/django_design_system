from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helper functions for CSS class generation – reused by both parameter classes
# and ModelParam for consistency and DRY principles.
# ---------------------------------------------------------------------------


def generate_bool_css_class(param_name: str, value: Any) -> list[str]:
    """Generate a kebab-case CSS class from a boolean value when truthy."""
    if value:
        return [param_name.lower().replace("_", "-")]
    return []


def generate_str_css_class(value: Any) -> list[str]:
    """Generate a kebab-case CSS class from a string value when truthy."""
    if value:
        return [str(value).replace("_", "-")]
    return []


class BaseParam:
    """
    Uses the descriptor protocol to define parameters for components, including type validation, default values, and documentation generation.

    See https://docs.python.org/3/howto/descriptor.html for more on the descriptor protocol.
    """

    type: type
    required: bool
    description: Optional[str]
    default: Optional[Any]
    choices: Optional[list[Any]]
    name: str
    private_name: str

    def __init__(
        self,
        description: Optional[str] = None,
        *,
        required: Optional[bool] = True,
        default: Optional[Any] = None,
        choices: Optional[list[Any]] = None,
    ):
        self.description = description
        self.required = bool(required)
        self.default = default
        self.choices = choices

        if default is not None and choices is not None:
            self.validate(default)

    def validate(self, value):
        if not isinstance(value, self.type):
            raise ValueError(f"Expected {self.type} but got {type(value)}.")
        if self.choices is not None and not self.choices:
            raise ValueError("Choices must not be empty")
        if self.choices and value not in self.choices:
            raise ValueError(f"Expected one of {self.choices} but got {value}.")

    def docstring(self) -> str:
        docstr = self.name
        if self.required:
            docstr += f": {self.type.__name__}"
        else:
            docstr += f": Optional[{self.type.__name__}]"
        if self.default is not None:
            docstr += f" (default: {self.default})"
        if self.description:
            docstr += f" - {self.description}"
        return docstr

    def get_extra_context(self, param_name: str, value: Any) -> dict[str, Any]:
        """Return additional context variables to add to the component's template context.

        Override in subclasses (e.g. ModelParam) to inject extra context
        derived from the parameter value.
        """
        return {}

    def get_css_classes(self, param_name: str, value: Any) -> list[str]:
        """Return CSS classes derived from the parameter value.

        Override in subclasses to produce CSS classes from the parameter.
        """
        return []

    def has_been_set(self, obj: Any) -> bool:
        """Return True if the parameter has been explicitly set on the given component instance."""
        return hasattr(obj, self.private_name)

    def __set_name__(self, owner, name) -> None:
        self.name = name
        self.private_name = "_" + name

    def __get__(self, obj, objtype=None) -> Any | None:
        if obj is None:
            return self
        if value := getattr(obj, self.private_name, None):
            return value
        return self.default

    def __set__(self, obj, value) -> None:
        self.validate(value)
        setattr(obj, self.private_name, value)

    def __str__(self):
        return f"<BaseParam {self.name} of type {self.type.__name__}>"


class StrParam(BaseParam):
    type = str


class BoolParam(BaseParam):
    type = bool
    choices = [True, False]


class StrCSSClassParam(StrParam):
    css_class = True

    # this class requires choices to be set, so we enforce that in the constructor
    def __init__(
        self,
        description: Optional[str] = None,
        *,
        required: Optional[bool] = True,
        default: Optional[Any] = None,
        choices: list[Any],
    ):
        return super().__init__(
            description,
            required=required,
            default=default,
            choices=choices,
        )

    def get_css_classes(self, param_name: str, value: Any) -> list[str]:
        """Return the parameter's string value as a CSS class when truthy."""
        return generate_str_css_class(value)


class BoolCSSClassParam(BoolParam):
    css_class = True

    def get_css_classes(self, param_name: str, value: Any) -> list[str]:
        """Return the parameter name as a CSS class when truthy."""
        return generate_bool_css_class(param_name, value)
