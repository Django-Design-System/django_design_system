from typing import Any, Optional

from dj_design_system.parameters.base import (
    BaseParam,
    generate_bool_css_class,
    generate_str_css_class,
)


class ModelParam(BaseParam):
    """A parameter that accepts a Django model instance and exposes its attributes.

    Subclass this and define a ``Meta`` inner class with at least ``model``
    and ``fields``.  ``model`` may be a model class or an ``"app_label.ModelName"``
    string (resolved lazily via Django's app registry).  ``fields`` should be a
    list of attribute names or ``"__all__"`` (all concrete model fields).

    .. warning::

        Prefer explicit field lists over ``"__all__"``.  Using ``"__all__"``
        exposes every concrete model field in the template context, which may
        include sensitive data. It also defers CSS class field validation to
        runtime instead of catching mismatches at class definition time.

    Optional ``Meta`` attributes:

    * ``bool_css_classes`` – list of attribute names (or ``(attr, class_name)``
      tuples) whose truthy values contribute a CSS class.
    * ``str_css_classes`` – list of attribute names (or ``(attr, class_name)``
      tuples) whose string values contribute a CSS class.

    All attributes referenced in ``bool_css_classes`` and ``str_css_classes``
    must be present in ``Meta.fields``.

    CSS classes are namespaced with the parameter's name on the component to
    avoid collisions, e.g. ``user-active``, ``user-name-andrew``.
    """

    def __init_subclass__(cls, **kwargs):
        """Validate that all subclasses define a Meta class.

        Concrete subclasses must have ``Meta.model`` and ``Meta.fields``.
        Abstract intermediates must set ``Meta.abstract = True``.
        """
        super().__init_subclass__(**kwargs)
        own_meta = cls.__dict__.get("Meta", None)
        if own_meta is None:
            raise ValueError(
                f"{cls.__name__} must define a Meta class. "
                "Set Meta.abstract = True for intermediate base classes."
            )
        if getattr(own_meta, "abstract", False):
            return
        if getattr(own_meta, "model", None) is None:
            raise ValueError(f"{cls.__name__}.Meta must define a 'model' attribute.")
        if getattr(own_meta, "fields", None) is None:
            raise ValueError(f"{cls.__name__}.Meta must define a 'fields' attribute.")
        cls._validate_css_class_fields(own_meta)

    def __init__(
        self,
        description: Optional[str] = None,
        *,
        required: Optional[bool] = True,
        default: Optional[Any] = None,
    ):
        # ModelParam does not support ``choices``.
        super().__init__(description=description, required=required, default=default)

    # ------------------------------------------------------------------
    # Model resolution
    # ------------------------------------------------------------------

    def _resolve_model(self):
        """Return the model class, resolving a string reference lazily."""
        if not hasattr(self, "_resolved_model"):
            model = self.__class__.Meta.model  # type: ignore[attr-defined]
            if isinstance(model, str):
                from django.apps import apps

                self._resolved_model = apps.get_model(model)
            else:
                self._resolved_model = model
        return self._resolved_model

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    def _get_fields(self) -> list[str]:
        """Return the list of attribute names to expose in the template context."""
        fields = self.__class__.Meta.fields  # type: ignore[attr-defined]
        if fields == "__all__":
            model = self._resolve_model()
            return [f.name for f in model._meta.get_fields() if f.concrete]
        return list(fields)

    # ------------------------------------------------------------------
    # CSS class config helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_css_entry(item: str | tuple[str, str]) -> tuple[str, str]:
        """Normalise a CSS class config entry to an ``(attr, class_name)`` tuple.

        Accepts either a bare string (attribute name used as class name) or a
        ``(attribute, class_name)`` tuple.
        """
        if isinstance(item, tuple):
            return item
        return (item, item)

    @classmethod
    def _validate_css_class_fields(cls, meta) -> None:
        """Ensure all attributes referenced in CSS class configs are in Meta.fields.

        When ``Meta.fields`` is ``"__all__"``, this check is skipped because
        the full field list depends on the resolved model.
        """
        fields = meta.fields
        if fields == "__all__":
            return

        fields_set = set(fields)
        for config_name in ("bool_css_classes", "str_css_classes"):
            for item in getattr(meta, config_name, []):
                attr, _ = cls._normalise_css_entry(item)
                if attr not in fields_set:
                    raise ValueError(
                        f"{cls.__name__}.Meta.{config_name} references "
                        f"'{attr}', which is not in Meta.fields."
                    )

    # ------------------------------------------------------------------
    # Descriptor overrides
    # ------------------------------------------------------------------

    def validate(self, value):
        """Check that *value* is an instance of the configured model."""
        model_class = self._resolve_model()
        if not isinstance(value, model_class):
            raise TypeError(
                f"Expected {model_class.__name__} instance but got {type(value)}."
            )

    def docstring(self) -> str:
        """Generate a docstring using the resolved model name."""
        model_class = self._resolve_model()
        docstr = self.name
        if self.required:
            docstr += f": {model_class.__name__}"
        else:
            docstr += f": Optional[{model_class.__name__}]"
        if self.default is not None:
            docstr += f" (default: {self.default})"
        if self.description:
            docstr += f" - {self.description}"
        return docstr

    def __str__(self):
        model_class = self._resolve_model()
        return f"<ModelParam {self.name} of type {model_class.__name__}>"

    # ------------------------------------------------------------------
    # Component hooks
    # ------------------------------------------------------------------

    def get_extra_context(self, param_name: str, value: Any) -> dict[str, Any]:
        """Flatten model attributes into the template context.

        Each attribute listed in ``Meta.fields`` is added as
        ``{param_name}_{attribute}``.
        """
        context: dict[str, Any] = super().get_extra_context(param_name, value)
        if value is None:
            return context
        for field_name in self._get_fields():
            context[f"{param_name}_{field_name}"] = getattr(value, field_name, None)
        return context

    def get_css_classes(self, param_name: str, value: Any) -> list[str]:
        """Generate namespaced CSS classes from model attributes configured in Meta.

        Delegates to shared CSS class generation logic for both boolean and string attributes,
        adding a {param_name}- prefix for namespacing.
        """
        classes: list[str] = super().get_css_classes(param_name, value)
        if value is None:
            return classes

        for item in getattr(self.__class__.Meta, "bool_css_classes", []):  # type: ignore[attr-defined]
            attr, class_name = self._normalise_css_entry(item)
            attr_value = getattr(value, attr, False)
            for cls_name in generate_bool_css_class(class_name, attr_value):
                classes.append(f"{param_name}-{cls_name}")

        for item in getattr(self.__class__.Meta, "str_css_classes", []):  # type: ignore[attr-defined]
            attr, class_name = self._normalise_css_entry(item)
            attr_value = getattr(value, attr, None)
            for raw_class in generate_str_css_class(attr_value):
                classes.append(f"{param_name}-{class_name}-{raw_class}")

        return classes
